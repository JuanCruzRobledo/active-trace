"""Tests unitarios para AuditLogRepository y AuditService (C-05).

Sigue el patrón del proyecto: usa AsyncMock para el session y fixtures
simples. Tests de integración con DB real están en tests/integration/.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.core.config import Settings
from app.repositories.audit_log_repository import AuditLogRepository
from app.services.audit_service import AuditService, VALID_ACCION_CODES
from app.models.audit_log import AuditLog


# ── Helpers ───────────────────────────────────────────────────────────────


def _settings(**kwargs) -> Settings:
    defaults = dict(
        SECRET_KEY="a" * 64,
        ENCRYPTION_KEY="b" * 32,
        DATABASE_URL="placeholder",
        ACCESS_TOKEN_EXPIRE_MINUTES=15,
        REFRESH_TOKEN_EXPIRE_DAYS=7,
        PASSWORD_RESET_EXPIRE_MINUTES=30,
        TWO_FA_CHALLENGE_EXPIRE_MINUTES=5,
        TOTP_ISSUER="activia-trace",
        LOGIN_RATE_LIMIT="5/60s",
        MAILER_MODE="console",
        ENVIRONMENT="development",
        LOG_LEVEL="DEBUG",
    )
    defaults.update(kwargs)
    return Settings(**defaults)


def _audit_log(**kwargs) -> AuditLog:
    """Crea un MagicMock con spec=AuditLog para tests unitarios."""
    log = MagicMock(spec=AuditLog)
    log.id = kwargs.get("id", uuid4())
    log.tenant_id = kwargs.get("tenant_id", uuid4())
    log.fecha_hora = kwargs.get("fecha_hora", datetime.now(UTC))
    log.actor_id = kwargs.get("actor_id", uuid4())
    log.impersonado_id = kwargs.get("impersonado_id", None)
    log.materia_id = kwargs.get("materia_id", None)
    log.accion = kwargs.get("accion", "CALIFICACIONES_IMPORTAR")
    log.detalle = kwargs.get("detalle", None)
    log.filas_afectadas = kwargs.get("filas_afectadas", None)
    log.ip = kwargs.get("ip", None)
    log.user_agent = kwargs.get("user_agent", None)
    return log


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def settings():
    return _settings()


@pytest.fixture
def tenant_id():
    return uuid4()


@pytest.fixture
def mock_session():
    session = AsyncMock()
    # session.add() es síncrono en SQLAlchemy real
    session.add = MagicMock()
    # session.execute() y session.flush() son async
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session, tenant_id):
    return AuditLogRepository(session=mock_session, tenant_id=tenant_id)


@pytest.fixture
def audit_service(repo, settings):
    return AuditService(audit_log_repo=repo, settings=settings)


# ═══════════════════════════════════════════════════════════════════════════
# 5.1 — register() inserts a record correctly
# ═══════════════════════════════════════════════════════════════════════════


class TestRegister:
    """AuditLogRepository.register() inserta un registro."""

    async def test_register_inserts_record(self, repo, tenant_id):
        """WHEN register() with required fields THEN record is added and flushed."""
        actor_id = uuid4()
        result = await repo.register(
            tenant_id=tenant_id,
            actor_id=actor_id,
            accion="CALIFICACIONES_IMPORTAR",
        )

        assert result.tenant_id == tenant_id
        assert result.actor_id == actor_id
        assert result.accion == "CALIFICACIONES_IMPORTAR"
        repo.session.add.assert_called_once()
        repo.session.flush.assert_awaited_once()

    async def test_register_with_all_optional_fields(self, repo, tenant_id):
        """WHEN register() with all optional fields THEN all are set."""
        actor_id = uuid4()
        materia_id = uuid4()
        impersonado_id = uuid4()

        result = await repo.register(
            tenant_id=tenant_id,
            actor_id=actor_id,
            accion="PADRON_CARGAR",
            detalle={"key": "value"},
            filas_afectadas=42,
            materia_id=materia_id,
            impersonado_id=impersonado_id,
            ip="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert result.accion == "PADRON_CARGAR"
        assert result.detalle == {"key": "value"}
        assert result.filas_afectadas == 42
        assert result.materia_id == materia_id
        assert result.impersonado_id == impersonado_id
        assert result.ip == "192.168.1.1"
        assert result.user_agent == "Mozilla/5.0"
        repo.session.add.assert_called_once()
        repo.session.flush.assert_awaited_once()


# ═══════════════════════════════════════════════════════════════════════════
# 5.3 — list() returns paginated results sorted by fecha_hora DESC
# ═══════════════════════════════════════════════════════════════════════════


class TestList:
    """AuditLogRepository.list() consulta registros paginados."""

    async def _setup_scalars(self, mock_session, logs):
        """Helper: configura mock_session.scalars() para retornar logs via .all()."""
        scalars_result = MagicMock()
        scalars_result.all.return_value = logs
        mock_session.scalars = AsyncMock(return_value=scalars_result)

    async def test_list_returns_paginated_desc(self, repo, mock_session, tenant_id):
        """WHEN list() THEN returns records ordered by fecha_hora DESC with limit/offset."""
        now = datetime.now(UTC)
        logs = [_audit_log(tenant_id=tenant_id, fecha_hora=now - timedelta(hours=i)) for i in range(3)]
        await self._setup_scalars(mock_session, logs)

        result = await repo.list(limit=2, offset=0)

        assert len(result) == 3
        # Verify ordering: should be fecha_hora DESC
        assert result[0].fecha_hora >= result[-1].fecha_hora

    async def test_list_filters_by_actor_id(self, repo, mock_session, tenant_id):
        """WHEN list(actor_id=...) THEN filters by that actor."""
        actor = uuid4()
        logs = [_audit_log(tenant_id=tenant_id, actor_id=actor)]
        await self._setup_scalars(mock_session, logs)

        result = await repo.list(actor_id=actor)

        assert all(r.actor_id == actor for r in result)

    async def test_list_filters_by_accion_and_date_range(self, repo, mock_session, tenant_id):
        """WHEN list(accion=..., fecha_hora_desde=..., fecha_hora_hasta=...) THEN filters."""
        logs = [
            _audit_log(tenant_id=tenant_id, accion="CALIFICACIONES_IMPORTAR"),
        ]
        await self._setup_scalars(mock_session, logs)
        since = datetime.now(UTC) - timedelta(days=1)
        until = datetime.now(UTC) + timedelta(days=1)

        result = await repo.list(
            accion="CALIFICACIONES_IMPORTAR",
            fecha_hora_desde=since,
            fecha_hora_hasta=until,
        )

        assert len(result) > 0
        assert all(r.accion == "CALIFICACIONES_IMPORTAR" for r in result)

    async def test_list_with_no_filters_returns_all_tenant_records(self, repo, mock_session, tenant_id):
        """WHEN list() without filters THEN returns all tenant records."""
        logs = [_audit_log(tenant_id=tenant_id) for _ in range(5)]
        await self._setup_scalars(mock_session, logs)

        result = await repo.list()

        assert len(result) == 5

    async def test_list_respects_offset_and_limit(self, repo, mock_session, tenant_id):
        """WHEN list(offset=2, limit=3) THEN offsets and limits."""
        logs = [_audit_log(tenant_id=tenant_id) for _ in range(3)]
        await self._setup_scalars(mock_session, logs)

        result = await repo.list(offset=2, limit=3)

        assert len(result) == 3


# ═══════════════════════════════════════════════════════════════════════════
# 5.6 — count() with and without filters
# ═══════════════════════════════════════════════════════════════════════════


class TestCount:
    """AuditLogRepository.count() cuenta registros."""

    async def _setup_scalar(self, mock_session, value):
        """Helper: configura mock_session.scalar() para retornar un valor."""
        mock_session.scalar = AsyncMock(return_value=value)

    async def test_count_without_filters(self, repo, mock_session):
        """WHEN count() THEN returns total."""
        await self._setup_scalar(mock_session, 10)

        result = await repo.count()

        assert result == 10

    async def test_count_with_filters(self, repo, mock_session):
        """WHEN count(accion=...) THEN returns filtered total."""
        await self._setup_scalar(mock_session, 3)

        result = await repo.count(accion="LOGIN_OK")

        assert result == 3

    async def test_count_returns_zero_when_no_records(self, repo, mock_session):
        """WHEN count() with no matching records THEN returns 0."""
        await self._setup_scalar(mock_session, 0)

        result = await repo.count()

        assert result == 0

    async def test_count_with_actor_id_filter(self, repo, mock_session):
        """WHEN count(actor_id=...) THEN counts by actor."""
        await self._setup_scalar(mock_session, 2)

        result = await repo.count(actor_id=uuid4())

        assert result == 2


# ═══════════════════════════════════════════════════════════════════════════
# 5.7 — AuditService.register() with valid code persists
# ═══════════════════════════════════════════════════════════════════════════


class TestAuditServiceValidCode:
    """AuditService.register() con código válido."""

    async def test_valid_code_calls_repo_register(self, audit_service, repo, tenant_id):
        """WHEN register() with valid code THEN repo.register() is called."""
        actor_id = uuid4()
        repo.register = AsyncMock()

        await audit_service.register(
            accion="CALIFICACIONES_IMPORTAR",
            actor_id=actor_id,
            tenant_id=tenant_id,
        )

        repo.register.assert_awaited_once()
        call_kwargs = repo.register.await_args.kwargs
        assert call_kwargs["accion"] == "CALIFICACIONES_IMPORTAR"
        assert call_kwargs["actor_id"] == actor_id
        assert call_kwargs["tenant_id"] == tenant_id

    async def test_valid_code_impersonation_persists_both_ids(self, audit_service, repo, tenant_id):
        """WHEN register() with impersonado_id THEN both actor and impersonado are passed."""
        actor_id = uuid4()
        impersonado_id = uuid4()
        repo.register = AsyncMock()

        await audit_service.register(
            accion="IMPERSONACION_INICIAR",
            actor_id=actor_id,
            tenant_id=tenant_id,
            impersonado_id=impersonado_id,
        )

        call_kwargs = repo.register.await_args.kwargs
        assert call_kwargs["impersonado_id"] == impersonado_id
        assert call_kwargs["actor_id"] == actor_id

    async def test_valid_code_all_codes_in_whitelist(self, audit_service, repo, tenant_id):
        """WHEN every VALID_CODE is used THEN all persist."""
        repo.register = AsyncMock()

        for code in VALID_ACCION_CODES:
            await audit_service.register(
                accion=code,
                actor_id=uuid4(),
                tenant_id=tenant_id,
            )

        assert repo.register.await_count == len(VALID_ACCION_CODES)


# ═══════════════════════════════════════════════════════════════════════════
# 5.8 — AuditService.register() with invalid code raises error
# ═══════════════════════════════════════════════════════════════════════════


class TestAuditServiceInvalidCode:
    """AuditService.register() con código inválido."""

    async def test_invalid_code_raises_value_error(self, audit_service, repo, tenant_id):
        """WHEN register() with invalid code THEN ValueError and no persist."""
        repo.register = AsyncMock()

        with pytest.raises(ValueError, match="Unknown audit action code"):
            await audit_service.register(
                accion="CODIGO_INEXISTENTE",
                actor_id=uuid4(),
                tenant_id=tenant_id,
            )

        repo.register.assert_not_awaited()

    async def test_empty_code_raises_value_error(self, audit_service, repo, tenant_id):
        """WHEN register() with empty code THEN ValueError."""
        repo.register = AsyncMock()

        with pytest.raises(ValueError, match="Unknown audit action code"):
            await audit_service.register(
                accion="",
                actor_id=uuid4(),
                tenant_id=tenant_id,
            )

        repo.register.assert_not_awaited()


# ═══════════════════════════════════════════════════════════════════════════
# 5.10 — Repository has no update() or delete() methods
# ═══════════════════════════════════════════════════════════════════════════


class TestAppendOnly:
    """AuditLogRepository no expone métodos de modificación."""

    async def test_no_update_method(self, repo):
        """AuditLogRepository NO tiene método update()."""
        assert not hasattr(repo, "update")

    async def test_no_delete_method(self, repo):
        """AuditLogRepository NO tiene método delete()."""
        assert not hasattr(repo, "delete")

    async def test_no_soft_delete_method(self, repo):
        """AuditLogRepository NO tiene método soft_delete()."""
        assert not hasattr(repo, "soft_delete")

    async def test_has_only_read_and_register_methods(self, repo):
        """AuditLogRepository solo tiene register/get_by_id/list/count."""
        expected = {"register", "get_by_id", "list", "count"}
        public_methods = {
            m for m in dir(repo) if not m.startswith("_") and callable(getattr(repo, m, None))
        }
        assert expected.issubset(public_methods), (
            f"Missing methods: {expected - public_methods}"
        )
