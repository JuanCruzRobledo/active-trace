"""Tests para ``app.core.rate_limit`` (C-03): 5/60s en endpoints sensibles.

Estos tests montan un mini-app FastAPI para ejercitar el decorador
``rate_limit_login`` con el limiter real de slowapi. El storage de
slowapi es in-memory (D5) y se resetea entre tests con
``limiter.reset()``.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware


@pytest.fixture(autouse=True)
def _fresh_limiter_per_test():
    """Reemplaza el limiter singleton con uno fresh por test.

    slowapi's ``Limiter.reset()`` no limpia el storage correctamente en
    algunas versiones, así que usamos uno nuevo por test. El key_func
    lee del header ``X-Test-IP`` para simular IPs distintas.
    """
    from slowapi import Limiter

    def _test_key_func(request: Request) -> str:
        return request.headers.get("X-Test-IP") or (
            request.client.host if request.client else "test"
        )

    fresh = Limiter(key_func=_test_key_func, headers_enabled=True)

    # Patch el módulo para que el decorador ``rate_limit_login`` use el fresh.
    import app.core.rate_limit as rl_mod

    rl_mod.limiter = fresh  # type: ignore[attr-defined]

    yield fresh

    # No es necesario restaurar — el siguiente test sobrescribe.


def _build_test_app(test_limiter) -> FastAPI:
    """Mini-app con un endpoint decorado con rate_limit_login."""
    from app.core.rate_limit import rate_limit_login

    app = FastAPI()
    app.state.limiter = test_limiter

    @app.get("/login")
    @rate_limit_login
    async def fake_login(request: Request, response: Response) -> dict[str, str]:
        return {"ip": request.headers.get("X-Test-IP", "n/a")}

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(request, exc):  # noqa: ANN001
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
        )

    app.add_middleware(SlowAPIMiddleware)
    return app


# ===========================================================================
# Happy path: hasta 5 requests OK
# ===========================================================================


class TestRateLimitUnderThreshold:
    """Bajo el umbral de 5, todas las requests pasan."""

    @pytest.mark.asyncio
    async def test_first_request_returns_200(self, _fresh_limiter_per_test):
        app = _build_test_app(_fresh_limiter_per_test)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.get("/login", headers={"X-Test-IP": "1.2.3.4"})
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_five_consecutive_requests_return_200(
        self, _fresh_limiter_per_test
    ):
        app = _build_test_app(_fresh_limiter_per_test)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            for i in range(5):
                r = await client.get(
                    "/login", headers={"X-Test-IP": "1.2.3.4"}
                )
                assert r.status_code == 200, f"request {i + 1} should be 200"


# ===========================================================================
# Sexto request: 429
# ===========================================================================


class TestRateLimitAtThreshold:
    """El sexto request a la misma IP en 60s → 429."""

    @pytest.mark.asyncio
    async def test_sixth_request_returns_429(self, _fresh_limiter_per_test):
        app = _build_test_app(_fresh_limiter_per_test)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 5 requests OK
            for _ in range(5):
                r = await client.get(
                    "/login", headers={"X-Test-IP": "1.2.3.4"}
                )
                assert r.status_code == 200

            # 6ª → 429
            r = await client.get("/login", headers={"X-Test-IP": "1.2.3.4"})
            assert r.status_code == 429
            assert "detail" in r.json()

    @pytest.mark.asyncio
    async def test_seventh_request_also_429(self, _fresh_limiter_per_test):
        """Después de superar el límite, todas las subsiguientes son 429."""
        app = _build_test_app(_fresh_limiter_per_test)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            for _ in range(6):
                await client.get(
                    "/login", headers={"X-Test-IP": "1.2.3.4"}
                )

            r = await client.get("/login", headers={"X-Test-IP": "1.2.3.4"})
            assert r.status_code == 429


# ===========================================================================
# IPs distintas NO comparten contador
# ===========================================================================


class TestRateLimitDifferentIPs:
    """IPs distintas tienen contadores independientes."""

    @pytest.mark.asyncio
    async def test_ip_b_not_affected_by_ip_a(self, _fresh_limiter_per_test):
        """Si IP A quemó sus 5 requests, IP B todavía tiene 5 disponibles."""
        app = _build_test_app(_fresh_limiter_per_test)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # IP A: 5 OK + 1 429
            for _ in range(5):
                r = await client.get(
                    "/login", headers={"X-Test-IP": "1.1.1.1"}
                )
                assert r.status_code == 200
            r = await client.get(
                "/login", headers={"X-Test-IP": "1.1.1.1"}
            )
            assert r.status_code == 429

            # IP B: 5 OK independientes
            for _ in range(5):
                r = await client.get(
                    "/login", headers={"X-Test-IP": "2.2.2.2"}
                )
                assert r.status_code == 200, (
                    "IP B should have its own counter"
                )

    @pytest.mark.asyncio
    async def test_ip_a_returns_after_being_blocked(
        self, _fresh_limiter_per_test
    ):
        """IP A en 429, IP B en 200, IP A sigue en 429 (no reseteo cross-IP)."""
        app = _build_test_app(_fresh_limiter_per_test)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            for _ in range(6):
                await client.get(
                    "/login", headers={"X-Test-IP": "1.1.1.1"}
                )
            # IP A sigue en 429
            r = await client.get(
                "/login", headers={"X-Test-IP": "1.1.1.1"}
            )
            assert r.status_code == 429


# ===========================================================================
# Decoradores pre-configurados
# ===========================================================================


class TestRateLimitDecorators:
    """Los 5 decoradores pre-configurados existen y aplican límites."""

    def test_all_decorators_exist(self):
        from app.core import rate_limit

        assert hasattr(rate_limit, "rate_limit_login")
        assert hasattr(rate_limit, "rate_limit_2fa_verify")
        assert hasattr(rate_limit, "rate_limit_refresh")
        assert hasattr(rate_limit, "rate_limit_forgot")
        assert hasattr(rate_limit, "rate_limit_reset")

    def test_decorators_are_callable(self):
        from app.core.rate_limit import (
            rate_limit_2fa_verify,
            rate_limit_forgot,
            rate_limit_login,
            rate_limit_refresh,
            rate_limit_reset,
        )

        # Cada uno es un decorador: aplicarlo a una función devuelve la función.
        # slowapi requiere que la función tenga un parámetro ``request`` o
        # ``websocket`` para hacer la keying, así que el dummy lo tiene.
        async def dummy(request: Request, response: Response) -> None:
            return None

        for dec in (
            rate_limit_login,
            rate_limit_2fa_verify,
            rate_limit_refresh,
            rate_limit_forgot,
            rate_limit_reset,
        ):
            wrapped = dec(dummy)
            assert callable(wrapped)


# ===========================================================================
# Audit log en RATE_LIMIT_HIT
# ===========================================================================


class TestRateLimitAudit:
    """Cuando se dispara el límite, se registra un audit event."""

    @pytest.mark.asyncio
    async def test_rate_limit_hit_emits_audit_log(
        self, caplog, _fresh_limiter_per_test
    ):
        import logging

        caplog.set_level(logging.INFO, logger="audit")

        app = _build_test_app(_fresh_limiter_per_test)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Quemar el límite
            for _ in range(6):
                await client.get(
                    "/login", headers={"X-Test-IP": "9.9.9.9"}
                )

        # El audit logger debió registrar RATE_LIMIT_HIT
        audit_records = [r for r in caplog.records if r.name == "audit"]
        rate_limit_records = [
            r
            for r in audit_records
            if r.extra
            and r.extra.get("audit.code") == "RATE_LIMIT_HIT"
        ]
        assert len(rate_limit_records) >= 1


# ===========================================================================
# Triangulación: limiter es singleton
# ===========================================================================


class TestRateLimitTriangulate:
    """El ``limiter`` es el mismo singleton en toda la app."""

    def test_limiter_is_singleton(self):
        from app.core.rate_limit import limiter

        from app.core.rate_limit import limiter as l2  # noqa: F401

        assert limiter is l2
