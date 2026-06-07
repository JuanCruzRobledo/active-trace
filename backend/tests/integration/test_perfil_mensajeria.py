"""Tests E2E de Perfil Propio y Mensajería Interna (C-20).

Cubre:
  - MensajeHiloRepository: create, get, list_by_participante, aislamiento
  - MensajeRepository: create, list_by_hilo, marcar_leido, no-leidos
  - PerfilService: obtener, actualizar, CUIL read-only, audit
  - MensajeriaService: crear_hilo, responder, obtener, listar, marcar_leido
  - Routers: GET/PATCH /api/perfil, GET/POST /api/inbox, POST /api/inbox/{id}/mensajes
  - Logout smoke test (reuso C-03)
  - Aislamiento cross-tenant y cross-usuario

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

from datetime import timezone
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from tests.conftest import db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]

_DEV_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
_DEV_TENANT_ID_2 = UUID("00000000-0000-0000-0000-000000000002")
_SECRET_KEY = "a" * 64


# ── Model imports ─────────────────────────────────────────────────────────

from app.models.tenant import Tenant  # noqa: E402
from app.models.usuario import Usuario  # noqa: E402
from app.models.mensaje import MensajeHilo, Mensaje  # noqa: E402


# ── Token helpers ─────────────────────────────────────────────────────────


def _make_token(user_id: UUID, tenant_id: UUID, roles: list[str] | None = None) -> str:
    return create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        secret_key=_SECRET_KEY,
        roles=roles or [],
    )


# ── Seed helpers ──────────────────────────────────────────────────────────


async def _seed_tenant(db: AsyncSession, tenant_id: UUID) -> None:
    exists = await db.get(Tenant, tenant_id)
    if exists is None:
        db.add(Tenant(id=tenant_id, tenant_id=tenant_id, nombre=f"Tenant {tenant_id}"))
        await db.flush()


async def _seed_usuario(
    db: AsyncSession,
    tenant_id: UUID,
    sufijo: str = "",
) -> Usuario:
    uid = uuid4()
    u = Usuario(
        id=uid,
        tenant_id=tenant_id,
        auth_user_id=None,
        nombre=f"Nombre{sufijo}",
        apellidos=f"Apellido{sufijo}",
        email=f"user{sufijo}_{uid}@test.com",
        cuil=f"20-{uid.int % 10**8:08d}-1",
        banco="BancoPrueba",
        regional="Regional Norte",
        estado="Activo",
    )
    db.add(u)
    await db.flush()
    return u


async def _seed_hilo(
    db: AsyncSession,
    tenant_id: UUID,
    usuario_a: Usuario,
    usuario_b: Usuario,
    asunto: str = "Test asunto",
    cuerpo: str = "Primer mensaje",
) -> tuple[MensajeHilo, Mensaje]:
    hilo = MensajeHilo(
        tenant_id=tenant_id,
        asunto=asunto,
        usuario_a_id=usuario_a.id,
        usuario_b_id=usuario_b.id,
    )
    db.add(hilo)
    await db.flush()
    msg = Mensaje(
        tenant_id=tenant_id,
        hilo_id=hilo.id,
        autor_id=usuario_a.id,
        cuerpo=cuerpo,
    )
    db.add(msg)
    await db.flush()
    return hilo, msg


# ══════════════════════════════════════════════════════════════════════════
# Task 3.1 — MensajeHiloRepository
# ══════════════════════════════════════════════════════════════════════════


class TestMensajeHiloRepository:
    """Repository CRUD + inbox filtering + tenant isolation."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession) -> None:
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        await _seed_tenant(db_session, _DEV_TENANT_ID_2)
        self.ua = await _seed_usuario(db_session, _DEV_TENANT_ID, "_a")
        self.ub = await _seed_usuario(db_session, _DEV_TENANT_ID, "_b")
        self.uc = await _seed_usuario(db_session, _DEV_TENANT_ID_2, "_c")
        self.db = db_session

    async def _get_repo(self):
        from app.repositories.mensaje_repository import MensajeHiloRepository
        return MensajeHiloRepository(self.db, _DEV_TENANT_ID)

    @pytest.mark.asyncio
    async def test_create_and_get_by_id(self) -> None:
        repo = await self._get_repo()
        hilo = MensajeHilo(
            tenant_id=_DEV_TENANT_ID,
            asunto="Asunto test",
            usuario_a_id=self.ua.id,
            usuario_b_id=self.ub.id,
        )
        created = await repo.create(hilo)
        assert created.id is not None

        fetched = await repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.asunto == "Asunto test"

    @pytest.mark.asyncio
    async def test_list_by_participante_includes_a_and_b(self) -> None:
        repo = await self._get_repo()
        hilo = MensajeHilo(
            tenant_id=_DEV_TENANT_ID,
            asunto="Hilo para ambos",
            usuario_a_id=self.ua.id,
            usuario_b_id=self.ub.id,
        )
        await repo.create(hilo)

        hilos_a = await repo.list_by_participante(self.ua.id)
        hilos_b = await repo.list_by_participante(self.ub.id)
        assert any(h.id == hilo.id for h in hilos_a)
        assert any(h.id == hilo.id for h in hilos_b)

    @pytest.mark.asyncio
    async def test_list_by_participante_excludes_non_participant(self) -> None:
        repo = await self._get_repo()
        uc_same_tenant = await _seed_usuario(self.db, _DEV_TENANT_ID, "_other")
        hilo = MensajeHilo(
            tenant_id=_DEV_TENANT_ID,
            asunto="Solo A y B",
            usuario_a_id=self.ua.id,
            usuario_b_id=self.ub.id,
        )
        await repo.create(hilo)

        hilos_c = await repo.list_by_participante(uc_same_tenant.id)
        assert not any(h.id == hilo.id for h in hilos_c)

    @pytest.mark.asyncio
    async def test_tenant_isolation(self) -> None:
        # Hilo creado en tenant 1
        repo_t1 = await self._get_repo()
        hilo = MensajeHilo(
            tenant_id=_DEV_TENANT_ID,
            asunto="Hilo tenant 1",
            usuario_a_id=self.ua.id,
            usuario_b_id=self.ub.id,
        )
        await repo_t1.create(hilo)

        # Repo del tenant 2 NO debe verlo
        from app.repositories.mensaje_repository import MensajeHiloRepository
        repo_t2 = MensajeHiloRepository(self.db, _DEV_TENANT_ID_2)
        fetched = await repo_t2.get_by_id(hilo.id)
        assert fetched is None


# ══════════════════════════════════════════════════════════════════════════
# Task 3.3 — MensajeRepository
# ══════════════════════════════════════════════════════════════════════════


class TestMensajeRepository:
    """Append-only messages: create, list_by_hilo, marcar_leido, no-leidos."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession) -> None:
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        self.ua = await _seed_usuario(db_session, _DEV_TENANT_ID, "_ma")
        self.ub = await _seed_usuario(db_session, _DEV_TENANT_ID, "_mb")
        self.hilo, self.msg1 = await _seed_hilo(
            db_session, _DEV_TENANT_ID, self.ua, self.ub
        )
        self.db = db_session

    async def _get_repo(self):
        from app.repositories.mensaje_repository import MensajeRepository
        return MensajeRepository(self.db, _DEV_TENANT_ID)

    @pytest.mark.asyncio
    async def test_create_append_only(self) -> None:
        repo = await self._get_repo()
        msg = Mensaje(
            tenant_id=_DEV_TENANT_ID,
            hilo_id=self.hilo.id,
            autor_id=self.ub.id,
            cuerpo="Respuesta de B",
        )
        created = await repo.create(msg)
        assert created.id is not None
        assert created.leido_at is None

    @pytest.mark.asyncio
    async def test_list_by_hilo_asc_order(self) -> None:
        repo = await self._get_repo()
        msg2 = Mensaje(
            tenant_id=_DEV_TENANT_ID,
            hilo_id=self.hilo.id,
            autor_id=self.ub.id,
            cuerpo="Segundo mensaje",
        )
        await repo.create(msg2)

        mensajes = await repo.list_by_hilo(self.hilo.id)
        assert len(mensajes) == 2
        assert mensajes[0].creado_at <= mensajes[1].creado_at

    @pytest.mark.asyncio
    async def test_marcar_leido(self) -> None:
        repo = await self._get_repo()
        assert self.msg1.leido_at is None

        updated = await repo.marcar_leido(self.msg1.id)
        assert updated is not None
        assert updated.leido_at is not None

    @pytest.mark.asyncio
    async def test_count_no_leidos_para_usuario(self) -> None:
        repo = await self._get_repo()
        # msg1 fue enviado por ua a ub — para ub es no leído
        count = await repo.count_no_leidos_para(self.hilo.id, destinatario_id=self.ub.id)
        assert count > 0

    @pytest.mark.asyncio
    async def test_propios_no_cuentan_como_no_leidos(self) -> None:
        repo = await self._get_repo()
        # msg1 fue enviado por ua — para ua mismo no es no leído
        count = await repo.count_no_leidos_para(self.hilo.id, destinatario_id=self.ua.id)
        assert count == 0


# ══════════════════════════════════════════════════════════════════════════
# Task 4.1 — PerfilService
# ══════════════════════════════════════════════════════════════════════════


class TestPerfilService:
    """obtener_mio, actualizar_mio, audit PERFIL_EDITAR, tenant scope."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession) -> None:
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        self.usuario = await _seed_usuario(db_session, _DEV_TENANT_ID, "_perfil")
        self.db = db_session

    def _get_svc(self):
        from app.services.perfil_service import PerfilService
        return PerfilService(
            session=self.db,
            tenant_id=_DEV_TENANT_ID,
            actor_id=self.usuario.id,
        )

    @pytest.mark.asyncio
    async def test_obtener_mio(self) -> None:
        svc = self._get_svc()
        perfil = await svc.obtener_mio(self.usuario.id)
        assert perfil is not None
        assert perfil.id == self.usuario.id

    @pytest.mark.asyncio
    async def test_actualizar_mio_campos_editables(self) -> None:
        svc = self._get_svc()
        from app.schemas.perfil import PerfilUpdate
        datos = PerfilUpdate(banco="Nuevo Banco", regional="Sur")
        perfil = await svc.actualizar_mio(self.usuario.id, datos)
        assert perfil.banco == "Nuevo Banco"
        assert perfil.regional == "Sur"

    @pytest.mark.asyncio
    async def test_actualizar_mio_no_modifica_otros_campos(self) -> None:
        svc = self._get_svc()
        from app.schemas.perfil import PerfilUpdate
        nombre_original = self.usuario.nombre
        datos = PerfilUpdate(regional="Este")
        perfil = await svc.actualizar_mio(self.usuario.id, datos)
        assert perfil.nombre == nombre_original

    @pytest.mark.asyncio
    async def test_actualizar_mio_genera_audit(self, db_session: AsyncSession) -> None:
        from app.models.audit_log import AuditLog
        from sqlalchemy import select
        svc = self._get_svc()
        from app.schemas.perfil import PerfilUpdate
        await svc.actualizar_mio(self.usuario.id, PerfilUpdate(banco="AuditBanco"))
        await db_session.flush()
        result = await db_session.execute(
            select(AuditLog).where(AuditLog.accion == "PERFIL_EDITAR")
        )
        logs = result.scalars().all()
        assert len(logs) >= 1

    @pytest.mark.asyncio
    async def test_actualizar_mio_no_expone_pii_en_audit(self, db_session: AsyncSession) -> None:
        from app.models.audit_log import AuditLog
        from sqlalchemy import select
        svc = self._get_svc()
        from app.schemas.perfil import PerfilUpdate
        nuevo_cbu = "0000-cbu-secreto"
        await svc.actualizar_mio(self.usuario.id, PerfilUpdate(cbu=nuevo_cbu))
        await db_session.flush()
        result = await db_session.execute(
            select(AuditLog).where(AuditLog.accion == "PERFIL_EDITAR")
        )
        for log in result.scalars().all():
            if log.detalle:
                import json
                d = log.detalle if isinstance(log.detalle, dict) else json.loads(log.detalle)
                assert nuevo_cbu not in str(d)


# ══════════════════════════════════════════════════════════════════════════
# Task 4.3 — MensajeriaService
# ══════════════════════════════════════════════════════════════════════════


class TestMensajeriaService:
    """crear_hilo, responder, obtener, listar, marcar_leido, participación."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession) -> None:
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        self.ua = await _seed_usuario(db_session, _DEV_TENANT_ID, "_ms_a")
        self.ub = await _seed_usuario(db_session, _DEV_TENANT_ID, "_ms_b")
        self.uc = await _seed_usuario(db_session, _DEV_TENANT_ID, "_ms_c")
        self.db = db_session

    def _get_svc(self, actor: Usuario):
        from app.services.mensajeria_service import MensajeriaService
        return MensajeriaService(
            session=self.db,
            tenant_id=_DEV_TENANT_ID,
            actor_id=actor.id,
        )

    @pytest.mark.asyncio
    async def test_crear_hilo(self) -> None:
        svc = self._get_svc(self.ua)
        from app.schemas.mensajeria import HiloCreate
        body = HiloCreate(destinatario_id=self.ub.id, asunto="Hola", cuerpo="Primer msg")
        hilo = await svc.crear_hilo(body)
        assert hilo.id is not None
        assert hilo.asunto == "Hola"
        assert len(hilo.mensajes) == 1

    @pytest.mark.asyncio
    async def test_responder_en_hilo(self) -> None:
        svc_a = self._get_svc(self.ua)
        svc_b = self._get_svc(self.ub)
        from app.schemas.mensajeria import HiloCreate, MensajeCreate
        hilo = await svc_a.crear_hilo(
            HiloCreate(destinatario_id=self.ub.id, asunto="Test", cuerpo="Inicio")
        )
        msg = await svc_b.responder(hilo.id, MensajeCreate(cuerpo="Respuesta de B"))
        assert msg.autor_id == self.ub.id

    @pytest.mark.asyncio
    async def test_obtener_hilo_participante_ok(self) -> None:
        svc = self._get_svc(self.ua)
        from app.schemas.mensajeria import HiloCreate
        hilo = await svc.crear_hilo(
            HiloCreate(destinatario_id=self.ub.id, asunto="Ver", cuerpo="Mensaje")
        )
        svc_b = self._get_svc(self.ub)
        result = await svc_b.obtener_hilo(hilo.id)
        assert result.id == hilo.id
        assert len(result.mensajes) >= 1

    @pytest.mark.asyncio
    async def test_obtener_hilo_no_participante_raises(self) -> None:
        from app.core.exceptions import BusinessError
        svc_a = self._get_svc(self.ua)
        from app.schemas.mensajeria import HiloCreate
        hilo = await svc_a.crear_hilo(
            HiloCreate(destinatario_id=self.ub.id, asunto="Privado", cuerpo="Mensaje")
        )
        svc_c = self._get_svc(self.uc)
        with pytest.raises(BusinessError):
            await svc_c.obtener_hilo(hilo.id)

    @pytest.mark.asyncio
    async def test_listar_inbox_solo_propios(self) -> None:
        svc_a = self._get_svc(self.ua)
        svc_c = self._get_svc(self.uc)
        from app.schemas.mensajeria import HiloCreate
        hilo_a = await svc_a.crear_hilo(
            HiloCreate(destinatario_id=self.ub.id, asunto="Solo A y B", cuerpo="msg")
        )
        inbox_c = await svc_c.listar_inbox()
        ids = [h.id for h in inbox_c.items]
        assert hilo_a.id not in ids

    @pytest.mark.asyncio
    async def test_responder_no_participante_raises(self) -> None:
        from app.core.exceptions import BusinessError
        svc_a = self._get_svc(self.ua)
        svc_c = self._get_svc(self.uc)
        from app.schemas.mensajeria import HiloCreate, MensajeCreate
        hilo = await svc_a.crear_hilo(
            HiloCreate(destinatario_id=self.ub.id, asunto="Ajeno", cuerpo="msg")
        )
        with pytest.raises(BusinessError):
            await svc_c.responder(hilo.id, MensajeCreate(cuerpo="Intruso"))

    @pytest.mark.asyncio
    async def test_crear_hilo_genera_audit(self, db_session: AsyncSession) -> None:
        from app.models.audit_log import AuditLog
        from sqlalchemy import select
        svc = self._get_svc(self.ua)
        from app.schemas.mensajeria import HiloCreate
        await svc.crear_hilo(HiloCreate(destinatario_id=self.ub.id, asunto="Audit", cuerpo="msg"))
        await db_session.flush()
        result = await db_session.execute(
            select(AuditLog).where(AuditLog.accion == "MENSAJE_ENVIAR")
        )
        assert len(result.scalars().all()) >= 1


# ══════════════════════════════════════════════════════════════════════════
# Task 6.1 — Router /api/perfil
# ══════════════════════════════════════════════════════════════════════════


class TestRouterPerfil:
    """GET /api/perfil, PATCH /api/perfil, 422 en cuil, PII enmascarada."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, client: AsyncClient, db_session: AsyncSession) -> None:
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        self.usuario = await _seed_usuario(db_session, _DEV_TENANT_ID, "_router_perfil")
        await db_session.commit()
        self.token = _make_token(self.usuario.id, _DEV_TENANT_ID)
        self.client = client

    @pytest.mark.asyncio
    async def test_get_perfil_returns_own_data(self) -> None:
        r = await self.client.get(
            "/api/perfil",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == str(self.usuario.id)

    @pytest.mark.asyncio
    async def test_get_perfil_ignores_usuario_id_param(self) -> None:
        otro = uuid4()
        r = await self.client.get(
            f"/api/perfil?usuario_id={otro}",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        assert r.status_code == 200
        assert r.json()["id"] == str(self.usuario.id)

    @pytest.mark.asyncio
    async def test_patch_perfil_editable_fields(self) -> None:
        r = await self.client.patch(
            "/api/perfil",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"banco": "BancoNuevo", "regional": "Oeste"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["banco"] == "BancoNuevo"
        assert data["regional"] == "Oeste"

    @pytest.mark.asyncio
    async def test_patch_perfil_cuil_returns_422(self) -> None:
        r = await self.client.patch(
            "/api/perfil",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"cuil": "20-99999999-9"},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_get_perfil_requires_auth(self) -> None:
        r = await self.client.get("/api/perfil")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_get_perfil_pii_masked(self) -> None:
        r = await self.client.get(
            "/api/perfil",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        assert r.status_code == 200
        data = r.json()
        if data.get("cuil"):
            assert "*" in data["cuil"]


# ══════════════════════════════════════════════════════════════════════════
# Task 6.3 — Router /api/inbox
# ══════════════════════════════════════════════════════════════════════════


class TestRouterInbox:
    """GET /api/inbox, GET /api/inbox/{id}, POST /api/inbox, POST /api/inbox/{id}/mensajes."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, client: AsyncClient, db_session: AsyncSession) -> None:
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        self.ua = await _seed_usuario(db_session, _DEV_TENANT_ID, "_inbox_a")
        self.ub = await _seed_usuario(db_session, _DEV_TENANT_ID, "_inbox_b")
        self.uc = await _seed_usuario(db_session, _DEV_TENANT_ID, "_inbox_c")
        await db_session.commit()
        self.token_a = _make_token(self.ua.id, _DEV_TENANT_ID)
        self.token_b = _make_token(self.ub.id, _DEV_TENANT_ID)
        self.token_c = _make_token(self.uc.id, _DEV_TENANT_ID)
        self.client = client

    @pytest.mark.asyncio
    async def test_get_inbox_empty(self) -> None:
        r = await self.client.get(
            "/api/inbox",
            headers={"Authorization": f"Bearer {self.token_a}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_post_inbox_crea_hilo(self) -> None:
        r = await self.client.post(
            "/api/inbox",
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"destinatario_id": str(self.ub.id), "asunto": "Hola B", "cuerpo": "Primer msg"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["asunto"] == "Hola B"
        assert len(data["mensajes"]) == 1

    @pytest.mark.asyncio
    async def test_get_inbox_solo_propios(self) -> None:
        # A crea hilo con B
        await self.client.post(
            "/api/inbox",
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"destinatario_id": str(self.ub.id), "asunto": "Solo AB", "cuerpo": "msg"},
        )
        # C no ve ese hilo
        r = await self.client.get(
            "/api/inbox",
            headers={"Authorization": f"Bearer {self.token_c}"},
        )
        assert r.status_code == 200
        assert r.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_get_inbox_hilo_detalle_participante(self) -> None:
        cr = await self.client.post(
            "/api/inbox",
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"destinatario_id": str(self.ub.id), "asunto": "Detalle", "cuerpo": "ver"},
        )
        hilo_id = cr.json()["id"]

        r = await self.client.get(
            f"/api/inbox/{hilo_id}",
            headers={"Authorization": f"Bearer {self.token_b}"},
        )
        assert r.status_code == 200
        assert r.json()["id"] == hilo_id

    @pytest.mark.asyncio
    async def test_get_inbox_hilo_no_participante_404(self) -> None:
        cr = await self.client.post(
            "/api/inbox",
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"destinatario_id": str(self.ub.id), "asunto": "Privado", "cuerpo": "msg"},
        )
        hilo_id = cr.json()["id"]

        r = await self.client.get(
            f"/api/inbox/{hilo_id}",
            headers={"Authorization": f"Bearer {self.token_c}"},
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_get_inbox_hilo_inexistente_404(self) -> None:
        r = await self.client.get(
            f"/api/inbox/{uuid4()}",
            headers={"Authorization": f"Bearer {self.token_a}"},
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_post_responder_participante(self) -> None:
        cr = await self.client.post(
            "/api/inbox",
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"destinatario_id": str(self.ub.id), "asunto": "Responder", "cuerpo": "Inicio"},
        )
        hilo_id = cr.json()["id"]

        r = await self.client.post(
            f"/api/inbox/{hilo_id}/mensajes",
            headers={"Authorization": f"Bearer {self.token_b}"},
            json={"cuerpo": "Respuesta B"},
        )
        assert r.status_code == 201
        assert r.json()["autor_id"] == str(self.ub.id)

    @pytest.mark.asyncio
    async def test_post_responder_no_participante_404(self) -> None:
        cr = await self.client.post(
            "/api/inbox",
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"destinatario_id": str(self.ub.id), "asunto": "Ajeno", "cuerpo": "msg"},
        )
        hilo_id = cr.json()["id"]

        r = await self.client.post(
            f"/api/inbox/{hilo_id}/mensajes",
            headers={"Authorization": f"Bearer {self.token_c}"},
            json={"cuerpo": "Intruso"},
        )
        assert r.status_code == 404


# ══════════════════════════════════════════════════════════════════════════
# Task 7.1 — Logout smoke test (reuso C-03)
# ══════════════════════════════════════════════════════════════════════════


class TestLogoutSmoke:
    """POST /api/auth/logout sigue revocando el refresh token."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, client: AsyncClient, db_session: AsyncSession) -> None:
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        self.usuario = await _seed_usuario(db_session, _DEV_TENANT_ID, "_logout")
        await db_session.commit()
        self.client = client
        self.access_token = _make_token(self.usuario.id, _DEV_TENANT_ID)

    @pytest.mark.asyncio
    async def test_logout_con_token_invalido_devuelve_error(self) -> None:
        r = await self.client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json={"refresh_token": "token-invalido-fake"},
        )
        # 400 o 401 — el logout rechaza tokens inválidos
        assert r.status_code in (400, 401, 422)


# ══════════════════════════════════════════════════════════════════════════
# Task 8.1 — E2E perfil
# ══════════════════════════════════════════════════════════════════════════


class TestE2EPerfil:
    """Usuario edita banco/regional → relee → cambios persisten. CUIL → 422."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, client: AsyncClient, db_session: AsyncSession) -> None:
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        self.usuario = await _seed_usuario(db_session, _DEV_TENANT_ID, "_e2e_perfil")
        await db_session.commit()
        self.token = _make_token(self.usuario.id, _DEV_TENANT_ID)
        self.client = client

    @pytest.mark.asyncio
    async def test_editar_y_releer(self) -> None:
        await self.client.patch(
            "/api/perfil",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"banco": "BancoFinal", "regional": "Sur"},
        )
        r = await self.client.get(
            "/api/perfil",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["banco"] == "BancoFinal"
        assert data["regional"] == "Sur"

    @pytest.mark.asyncio
    async def test_editar_cuil_422(self) -> None:
        r = await self.client.patch(
            "/api/perfil",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"cuil": "27-12345678-3"},
        )
        assert r.status_code == 422


# ══════════════════════════════════════════════════════════════════════════
# Task 8.2 — E2E mensajería
# ══════════════════════════════════════════════════════════════════════════


class TestE2EMensajeria:
    """A crea hilo a B → B ve inbox → B responde → A ve respuesta."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, client: AsyncClient, db_session: AsyncSession) -> None:
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        self.ua = await _seed_usuario(db_session, _DEV_TENANT_ID, "_e2e_ma")
        self.ub = await _seed_usuario(db_session, _DEV_TENANT_ID, "_e2e_mb")
        await db_session.commit()
        self.token_a = _make_token(self.ua.id, _DEV_TENANT_ID)
        self.token_b = _make_token(self.ub.id, _DEV_TENANT_ID)
        self.client = client

    @pytest.mark.asyncio
    async def test_flujo_completo(self) -> None:
        # A crea hilo
        cr = await self.client.post(
            "/api/inbox",
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"destinatario_id": str(self.ub.id), "asunto": "E2E hilo", "cuerpo": "Mensaje A"},
        )
        assert cr.status_code == 201
        hilo_id = cr.json()["id"]

        # B ve el hilo en su inbox
        inbox_b = await self.client.get(
            "/api/inbox",
            headers={"Authorization": f"Bearer {self.token_b}"},
        )
        assert inbox_b.status_code == 200
        assert any(h["id"] == hilo_id for h in inbox_b.json()["items"])

        # B responde
        resp = await self.client.post(
            f"/api/inbox/{hilo_id}/mensajes",
            headers={"Authorization": f"Bearer {self.token_b}"},
            json={"cuerpo": "Respuesta de B"},
        )
        assert resp.status_code == 201

        # A ve la respuesta
        hilo_a = await self.client.get(
            f"/api/inbox/{hilo_id}",
            headers={"Authorization": f"Bearer {self.token_a}"},
        )
        assert hilo_a.status_code == 200
        mensajes = hilo_a.json()["mensajes"]
        cuerpos = [m["cuerpo"] for m in mensajes]
        assert "Respuesta de B" in cuerpos


# ══════════════════════════════════════════════════════════════════════════
# Task 8.3 — Aislamiento cross-tenant
# ══════════════════════════════════════════════════════════════════════════


class TestAislamientoCrossTenant:
    """Perfil e inbox de tenant A nunca exponen datos de tenant B."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, client: AsyncClient, db_session: AsyncSession) -> None:
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        await _seed_tenant(db_session, _DEV_TENANT_ID_2)
        self.ua_t1 = await _seed_usuario(db_session, _DEV_TENANT_ID, "_ct_a")
        self.ub_t1 = await _seed_usuario(db_session, _DEV_TENANT_ID, "_ct_b")
        self.ua_t2 = await _seed_usuario(db_session, _DEV_TENANT_ID_2, "_ct_c")
        self.ub_t2 = await _seed_usuario(db_session, _DEV_TENANT_ID_2, "_ct_d")
        await db_session.commit()
        self.token_t1 = _make_token(self.ua_t1.id, _DEV_TENANT_ID)
        self.token_t2 = _make_token(self.ua_t2.id, _DEV_TENANT_ID_2)
        self.client = client

    @pytest.mark.asyncio
    async def test_inbox_aislado_por_tenant(self) -> None:
        # Crear hilo en tenant 1
        cr = await self.client.post(
            "/api/inbox",
            headers={"Authorization": f"Bearer {self.token_t1}"},
            json={
                "destinatario_id": str(self.ub_t1.id),
                "asunto": "Hilo T1",
                "cuerpo": "msg T1",
            },
        )
        assert cr.status_code == 201
        hilo_id_t1 = cr.json()["id"]

        # Usuario de tenant 2 no lo ve
        inbox_t2 = await self.client.get(
            "/api/inbox",
            headers={"Authorization": f"Bearer {self.token_t2}"},
        )
        assert inbox_t2.status_code == 200
        ids = [h["id"] for h in inbox_t2.json()["items"]]
        assert hilo_id_t1 not in ids

    @pytest.mark.asyncio
    async def test_hilo_t1_inaccesible_desde_t2(self) -> None:
        cr = await self.client.post(
            "/api/inbox",
            headers={"Authorization": f"Bearer {self.token_t1}"},
            json={
                "destinatario_id": str(self.ub_t1.id),
                "asunto": "Secreto T1",
                "cuerpo": "msg",
            },
        )
        hilo_id_t1 = cr.json()["id"]

        r = await self.client.get(
            f"/api/inbox/{hilo_id_t1}",
            headers={"Authorization": f"Bearer {self.token_t2}"},
        )
        assert r.status_code == 404


# ══════════════════════════════════════════════════════════════════════════
# Task 8.4 — Aislamiento cross-usuario
# ══════════════════════════════════════════════════════════════════════════


class TestAislamientoCrossUsuario:
    """No-participante recibe 404 al leer o responder hilo ajeno."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, client: AsyncClient, db_session: AsyncSession) -> None:
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        self.ua = await _seed_usuario(db_session, _DEV_TENANT_ID, "_cu_a")
        self.ub = await _seed_usuario(db_session, _DEV_TENANT_ID, "_cu_b")
        self.uc = await _seed_usuario(db_session, _DEV_TENANT_ID, "_cu_c")
        await db_session.commit()
        self.token_a = _make_token(self.ua.id, _DEV_TENANT_ID)
        self.token_c = _make_token(self.uc.id, _DEV_TENANT_ID)
        self.client = client

    @pytest.mark.asyncio
    async def test_leer_hilo_ajeno_404(self) -> None:
        cr = await self.client.post(
            "/api/inbox",
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"destinatario_id": str(self.ub.id), "asunto": "Privado", "cuerpo": "msg"},
        )
        hilo_id = cr.json()["id"]

        r = await self.client.get(
            f"/api/inbox/{hilo_id}",
            headers={"Authorization": f"Bearer {self.token_c}"},
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_responder_hilo_ajeno_404(self) -> None:
        cr = await self.client.post(
            "/api/inbox",
            headers={"Authorization": f"Bearer {self.token_a}"},
            json={"destinatario_id": str(self.ub.id), "asunto": "Privado", "cuerpo": "msg"},
        )
        hilo_id = cr.json()["id"]

        r = await self.client.post(
            f"/api/inbox/{hilo_id}/mensajes",
            headers={"Authorization": f"Bearer {self.token_c}"},
            json={"cuerpo": "Intruso"},
        )
        assert r.status_code == 404
