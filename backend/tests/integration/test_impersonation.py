"""Integration tests for C-05 Impersonation (POST /api/auth/impersonate + stop).

Requires PostgreSQL real (DATABASE_URL_TEST in env).
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
)
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository
from tests.conftest import db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]

_DEV_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
_OTHER_TENANT_ID = UUID("00000000-0000-0000-0000-000000000002")
_SECRET_KEY = "a" * 64


# ── Seed helpers ──────────────────────────────────────────────────────────


async def _seed_rbac_data(db_session: AsyncSession) -> dict[str, UUID]:
    """Insert minimal RBAC data: permiso, roles, and matrix for dev tenant."""
    # Permiso: impersonacion:usar
    perm_id = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO permiso (id, codigo, descripcion, created_at) "
            "VALUES (:id, :codigo, :descripcion, now()) "
            "ON CONFLICT (codigo) DO NOTHING"
        ),
        {
            "id": perm_id,
            "codigo": "impersonacion:usar",
            "descripcion": "Usar impersonacion",
        },
    )

    # Rol: ADMIN
    rol_id = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO rol (id, tenant_id, codigo, nombre, descripcion, "
            "created_at, updated_at) "
            "VALUES (:id, :tenant_id, :codigo, :nombre, :descripcion, now(), now()) "
            "ON CONFLICT (tenant_id, codigo) DO NOTHING"
        ),
        {
            "id": rol_id,
            "tenant_id": _DEV_TENANT_ID,
            "codigo": "ADMIN",
            "nombre": "Administrador",
            "descripcion": "Admin",
        },
    )

    # Rol: PROFESOR (sin impersonacion:usar)
    prof_rol_id = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO rol (id, tenant_id, codigo, nombre, descripcion, "
            "created_at, updated_at) "
            "VALUES (:id, :tenant_id, :codigo, :nombre, :descripcion, now(), now()) "
            "ON CONFLICT (tenant_id, codigo) DO NOTHING"
        ),
        {
            "id": prof_rol_id,
            "tenant_id": _DEV_TENANT_ID,
            "codigo": "PROFESOR",
            "nombre": "Profesor",
            "descripcion": "Docente",
        },
    )

    # Rol-Permiso: ADMIN → impersonacion:usar
    await db_session.execute(
        text(
            "INSERT INTO rol_permiso (id, tenant_id, rol_id, permiso_id, created_at) "
            "VALUES (:id, :tenant_id, :rol_id, :permiso_id, now()) "
            "ON CONFLICT (tenant_id, rol_id, permiso_id) DO NOTHING"
        ),
        {
            "id": uuid4(),
            "tenant_id": _DEV_TENANT_ID,
            "rol_id": rol_id,
            "permiso_id": perm_id,
        },
    )

    await db_session.commit()

    return {"admin_rol_id": rol_id, "prof_rol_id": prof_rol_id, "perm_id": perm_id}


async def _create_user(
    db_session: AsyncSession,
    email: str = "admin@test.com",
    password: str = "AdminPass123!",
    tenant_id: UUID = _DEV_TENANT_ID,
) -> UUID:
    """Crea un usuario y retorna su UUID."""
    repo = UserRepository(session=db_session, tenant_id=tenant_id)
    user = await repo.create(
        email=email,
        password_hash=hash_password(password),
    )
    await db_session.commit()
    return user.id


async def _assign_role(
    db_session: AsyncSession,
    user_id: UUID,
    tenant_id: UUID = _DEV_TENANT_ID,
    rol_codigo: str = "ADMIN",
) -> None:
    """Asigna un rol a un usuario."""
    rid_result = await db_session.execute(
        text("SELECT id FROM rol WHERE tenant_id = :tid AND codigo = :cod"),
        {"tid": tenant_id, "cod": rol_codigo},
    )
    row = rid_result.fetchone()
    if row is not None:
        await db_session.execute(
            text(
                "INSERT INTO user_rol (id, user_id, rol_id, tenant_id, created_at) "
                "VALUES (:id, :uid, :rid, :tid, now()) "
                "ON CONFLICT (user_id, rol_id) DO NOTHING"
            ),
            {"id": uuid4(), "uid": user_id, "rid": row[0], "tid": tenant_id},
        )
        await db_session.commit()


def _make_token(
    user_id: UUID,
    roles: list[str],
    tenant_id: UUID = _DEV_TENANT_ID,
    impersonated_by: str | None = None,
) -> str:
    """Crea un access token JWT para tests."""
    extra_claims = {}
    if impersonated_by is not None:
        extra_claims["impersonated_by"] = impersonated_by
    return create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        secret_key=_SECRET_KEY,
        roles=roles,
        extra_claims=extra_claims or None,
    )


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _patch_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Override env vars so Settings() reads correct values for tests.

    ``get_current_user`` en ``dependencies.py`` instancia ``Settings()``
    inline — sin este monkeypatch usaría ``.env`` y fallaría porque
    la SECRET_KEY del .env no coincide con _SECRET_KEY del test.
    """
    monkeypatch.setenv("SECRET_KEY", _SECRET_KEY)
    monkeypatch.setenv("ENCRYPTION_KEY", "b" * 32)
    monkeypatch.setenv("DATABASE_URL", "placeholder")


@pytest_asyncio.fixture(autouse=True)
async def _seed_permissions(db_session: AsyncSession) -> None:
    """Seed RBAC data before each test."""
    await _seed_rbac_data(db_session)


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> UUID:
    """Admin user with impersonacion:usar permission."""
    uid = await _create_user(db_session, email="admin@test.com")
    await _assign_role(db_session, uid, rol_codigo="ADMIN")
    return uid


@pytest_asyncio.fixture
async def target_user(db_session: AsyncSession) -> UUID:
    """Target user for impersonation."""
    return await _create_user(
        db_session, email="target@test.com", password="TargetPass123!"
    )


@pytest_asyncio.fixture
async def other_tenant_user(db_session: AsyncSession) -> UUID:
    """User in another tenant."""
    uid = await _create_user(
        db_session,
        email="other@tenant.com",
        password="OtherPass123!",
        tenant_id=_OTHER_TENANT_ID,
    )
    await _assign_role(db_session, uid, tenant_id=_OTHER_TENANT_ID, rol_codigo="ADMIN")
    return uid


@pytest_asyncio.fixture
async def professor_user(db_session: AsyncSession) -> UUID:
    """Professor user WITHOUT impersonacion:usar permission."""
    uid = await _create_user(db_session, email="prof@test.com")
    await _assign_role(db_session, uid, rol_codigo="PROFESOR")
    return uid


# ═══════════════════════════════════════════════════════════════════════════
# 6.1 — Iniciar impersonación con ADMIN con permiso → 200 + token con impersonated_by
# ═══════════════════════════════════════════════════════════════════════════


class TestImpersonateSuccess:
    """Iniciar impersonación exitosa."""

    async def test_impersonate_returns_200_with_impersonated_by_claim(
        self,
        client: AsyncClient,
        admin_user: UUID,
        target_user: UUID,
    ) -> None:
        """GIVEN admin con permiso WHEN impersonate target THEN 200 + token con impersonated_by."""
        token = _make_token(admin_user, roles=["ADMIN"])
        resp = await client.post(
            "/api/auth/impersonate",
            json={"target_user_id": str(target_user)},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

        # Verificar claim impersonated_by en el access token
        payload = decode_access_token(body["access_token"], _SECRET_KEY)
        assert payload["sub"] == str(target_user)
        assert payload["impersonated_by"] == str(admin_user)

    async def test_impersonate_creates_audit_log(
        self,
        client: AsyncClient,
        admin_user: UUID,
        target_user: UUID,
        db_session: AsyncSession,
    ) -> None:
        """GIVEN impersonación exitosa THEN registra IMPERSONACION_INICIAR en audit_log."""
        token = _make_token(admin_user, roles=["ADMIN"])
        await client.post(
            "/api/auth/impersonate",
            json={"target_user_id": str(target_user)},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verificar audit log
        repo = AuditLogRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        logs = await repo.list(accion="IMPERSONACION_INICIAR")
        assert len(logs) >= 1
        log = logs[0]
        assert log.actor_id == admin_user
        assert log.impersonado_id == target_user


# ═══════════════════════════════════════════════════════════════════════════
# 6.2 — Iniciar impersonación sin permiso → 403
# ═══════════════════════════════════════════════════════════════════════════


class TestImpersonateForbidden:
    """Iniciar impersonación sin permiso."""

    async def test_impersonate_without_permission_returns_403(
        self,
        client: AsyncClient,
        professor_user: UUID,
        target_user: UUID,
    ) -> None:
        """GIVEN profesor SIN permiso WHEN impersonate THEN 403."""
        token = _make_token(professor_user, roles=["PROFESOR"])
        resp = await client.post(
            "/api/auth/impersonate",
            json={"target_user_id": str(target_user)},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 403

    async def test_impersonate_without_auth_returns_401(
        self,
        client: AsyncClient,
        target_user: UUID,
    ) -> None:
        """GIVEN no autenticado WHEN impersonate THEN 401."""
        resp = await client.post(
            "/api/auth/impersonate",
            json={"target_user_id": str(target_user)},
        )

        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# 6.3 — Iniciar impersonación a usuario inexistente → 404
# ═══════════════════════════════════════════════════════════════════════════


class TestImpersonateTargetNotFound:
    """Iniciar impersonación a usuario inexistente."""

    async def test_impersonate_nonexistent_user_returns_404(
        self,
        client: AsyncClient,
        admin_user: UUID,
    ) -> None:
        """GIVEN target inexistente WHEN impersonate THEN 404."""
        fake_id = uuid4()
        token = _make_token(admin_user, roles=["ADMIN"])
        resp = await client.post(
            "/api/auth/impersonate",
            json={"target_user_id": str(fake_id)},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# 6.4 — Iniciar impersonación a usuario de otro tenant → 404
# ═══════════════════════════════════════════════════════════════════════════


class TestImpersonateOtherTenant:
    """Iniciar impersonación a usuario de otro tenant."""

    async def test_impersonate_other_tenant_user_returns_404(
        self,
        client: AsyncClient,
        admin_user: UUID,
        other_tenant_user: UUID,
    ) -> None:
        """GIVEN target de otro tenant WHEN impersonate THEN 404 (no revela existencia)."""
        token = _make_token(admin_user, roles=["ADMIN"])
        resp = await client.post(
            "/api/auth/impersonate",
            json={"target_user_id": str(other_tenant_user)},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# 6.5 — Detener impersonación → 200 + registra IMPERSONACION_FINALIZAR
# ═══════════════════════════════════════════════════════════════════════════


class TestImpersonateStop:
    """Detener impersonación."""

    async def test_impersonate_stop_returns_200(
        self,
        client: AsyncClient,
        admin_user: UUID,
        target_user: UUID,
        db_session: AsyncSession,
    ) -> None:
        """GIVEN impersonando WHEN stop THEN 200 + token para admin."""
        # Primero iniciar impersonación
        admin_token = _make_token(admin_user, roles=["ADMIN"])
        imp_resp = await client.post(
            "/api/auth/impersonate",
            json={"target_user_id": str(target_user)},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert imp_resp.status_code == 200
        imp_token = imp_resp.json()["access_token"]

        # Detener impersonación
        stop_resp = await client.post(
            "/api/auth/impersonate/stop",
            headers={"Authorization": f"Bearer {imp_token}"},
        )

        assert stop_resp.status_code == 200
        stop_body = stop_resp.json()
        assert "access_token" in stop_body
        assert "refresh_token" in stop_body

        # El nuevo access token es para el admin (sin impersonated_by)
        payload = decode_access_token(stop_body["access_token"], _SECRET_KEY)
        assert payload["sub"] == str(admin_user)
        assert "impersonated_by" not in payload

    async def test_impersonate_stop_creates_audit_log(
        self,
        client: AsyncClient,
        admin_user: UUID,
        target_user: UUID,
        db_session: AsyncSession,
    ) -> None:
        """GIVEN impersonación detenida THEN registra IMPERSONACION_FINALIZAR."""
        admin_token = _make_token(admin_user, roles=["ADMIN"])
        imp_resp = await client.post(
            "/api/auth/impersonate",
            json={"target_user_id": str(target_user)},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert imp_resp.status_code == 200
        imp_token = imp_resp.json()["access_token"]

        await client.post(
            "/api/auth/impersonate/stop",
            headers={"Authorization": f"Bearer {imp_token}"},
        )

        repo = AuditLogRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        logs = await repo.list(accion="IMPERSONACION_FINALIZAR")
        assert len(logs) >= 1
        log = logs[0]
        assert log.actor_id == admin_user
        assert log.impersonado_id == target_user


# ═══════════════════════════════════════════════════════════════════════════
# 6.6 — Detener impersonación sin estar impersonando → 400
# ═══════════════════════════════════════════════════════════════════════════


class TestImpersonateStopWithoutImpersonation:
    """Detener impersonación sin estar impersonando."""

    async def test_stop_without_impersonation_returns_400(
        self,
        client: AsyncClient,
        admin_user: UUID,
    ) -> None:
        """GIVEN no impersonando WHEN stop THEN 400."""
        token = _make_token(admin_user, roles=["ADMIN"])
        resp = await client.post(
            "/api/auth/impersonate/stop",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
# 6.7 — Refresh conserva impersonated_by
# ═══════════════════════════════════════════════════════════════════════════


class TestImpersonationRefresh:
    """Refresh conserva impersonated_by durante rotación."""

    async def test_refresh_preserves_impersonated_by(
        self,
        client: AsyncClient,
        admin_user: UUID,
        target_user: UUID,
    ) -> None:
        """GIVEN token bajo impersonación WHEN refresh THEN nuevo token conserva impersonated_by."""
        admin_token = _make_token(admin_user, roles=["ADMIN"])
        imp_resp = await client.post(
            "/api/auth/impersonate",
            json={"target_user_id": str(target_user)},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert imp_resp.status_code == 200
        imp_body = imp_resp.json()
        refresh_token = imp_body["refresh_token"]

        # Hacer refresh con el token de impersonación
        refresh_resp = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert refresh_resp.status_code == 200
        refresh_body = refresh_resp.json()

        # Verificar que el nuevo access token conserva impersonated_by
        payload = decode_access_token(refresh_body["access_token"], _SECRET_KEY)
        assert payload["sub"] == str(target_user)
        assert payload["impersonated_by"] == str(admin_user)


# ═══════════════════════════════════════════════════════════════════════════
# 6.8 — Acción bajo impersonación registra actor_id real en audit log
# ═══════════════════════════════════════════════════════════════════════════


class TestAuditDuringImpersonation:
    """Auditoría bajo impersonación."""

    async def test_audit_logs_actor_id_under_impersonation(
        self,
        client: AsyncClient,
        admin_user: UUID,
        target_user: UUID,
        db_session: AsyncSession,
    ) -> None:
        """GIVEN acción bajo impersonación THEN audit_log tiene actor_id real."""
        admin_token = _make_token(admin_user, roles=["ADMIN"])
        imp_resp = await client.post(
            "/api/auth/impersonate",
            json={"target_user_id": str(target_user)},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert imp_resp.status_code == 200

        # Verificar que IMPERSONACION_INICIAR tiene actor_id = admin (real)
        repo = AuditLogRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        iniciar_logs = await repo.list(accion="IMPERSONACION_INICIAR")
        assert len(iniciar_logs) >= 1
        # actor_id es el admin (quien realmente hace la acción)
        assert iniciar_logs[0].actor_id == admin_user
        # impersonado_id es el target
        assert iniciar_logs[0].impersonado_id == target_user


# ═══════════════════════════════════════════════════════════════════════════
# 6.9 — Acción sin impersonación registra impersonado_id = NULL
# ═══════════════════════════════════════════════════════════════════════════


class TestAuditWithoutImpersonation:
    """Auditoría sin impersonación."""

    async def test_audit_logs_no_impersonation(
        self,
        client: AsyncClient,
        admin_user: UUID,
        db_session: AsyncSession,
    ) -> None:
        """GIVEN acción sin impersonación THEN audit_log tiene impersonado_id = NULL."""
        # Usar AuditService directamente para LOGIN_OK (acción sin impersonación)
        from app.services.audit_service import AuditService
        from app.core.config import Settings
        from app.repositories.audit_log_repository import AuditLogRepository

        repo = AuditLogRepository(session=db_session, tenant_id=_DEV_TENANT_ID)
        settings = Settings(SECRET_KEY="a"*64, ENCRYPTION_KEY="b"*32, DATABASE_URL="placeholder")
        svc = AuditService(audit_log_repo=repo, settings=settings)

        await svc.register(
            accion="LOGIN_OK",
            actor_id=admin_user,
            tenant_id=_DEV_TENANT_ID,
        )
        await db_session.commit()

        logs = await repo.list(accion="LOGIN_OK")
        assert len(logs) >= 1
        log = logs[0]
        assert log.actor_id == admin_user
        assert log.impersonado_id is None
