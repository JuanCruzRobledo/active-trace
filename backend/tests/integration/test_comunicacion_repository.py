"""Tests de integración para ComunicacionRepository (C-12).

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comunicacion import Comunicacion, EstadoComunicacion
from app.models.tenant import Tenant
from app.repositories.comunicacion_repository import ComunicacionRepository
from tests.conftest import db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]


# ── Seeds ────────────────────────────────────────────────────────────


async def _seed_tenant(db_session: AsyncSession) -> Tenant:
    tid = uuid.uuid4()
    t = Tenant(id=tid, tenant_id=tid, nombre="ComRepoTest")
    db_session.add(t)
    await db_session.flush()
    return t


async def _seed_materia(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    from app.models.materia import Materia

    m = Materia(tenant_id=tenant_id, codigo="MAT-COM", nombre="Comunicaciones Test")
    db_session.add(m)
    await db_session.flush()
    return m.id


async def _seed_usuario(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    from app.models.usuario import Usuario

    uid = uuid.uuid4()
    u = Usuario(
        id=uid,
        tenant_id=tenant_id,
        email=f"user{uuid.uuid4().hex[:4]}@test.com",
        nombre="Test",
        apellidos="User",
        estado="Activo",
    )
    db_session.add(u)
    await db_session.flush()
    return uid


async def _seed_comunicacion(
    db_session: AsyncSession,
    tenant_id: uuid.UUID,
    enviado_por_id: uuid.UUID,
    lote_id: uuid.UUID,
    materia_id: uuid.UUID | None = None,
    estado: EstadoComunicacion = EstadoComunicacion.Pendiente,
    necesita_aprobacion: bool = False,
) -> Comunicacion:
    c = Comunicacion(
        tenant_id=tenant_id,
        enviado_por_id=enviado_por_id,
        materia_id=materia_id,
        destinatario=f"alumno{uuid.uuid4().hex[:4]}@test.com",
        asunto="Test asunto",
        cuerpo="Test cuerpo",
        estado=estado,
        lote_id=lote_id,
        necesita_aprobacion=uuid.uuid4() if necesita_aprobacion else None,
    )
    db_session.add(c)
    await db_session.flush()
    return c


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def tenant(db_session: AsyncSession) -> Tenant:
    return await _seed_tenant(db_session)


@pytest_asyncio.fixture
async def usuario(db_session: AsyncSession, tenant: Tenant) -> uuid.UUID:
    return await _seed_usuario(db_session, tenant.id)


@pytest_asyncio.fixture
async def materia(db_session: AsyncSession, tenant: Tenant) -> uuid.UUID:
    return await _seed_materia(db_session, tenant.id)


@pytest_asyncio.fixture
async def repo(
    tenant: Tenant, db_session: AsyncSession
) -> ComunicacionRepository:
    return ComunicacionRepository(db_session, tenant.id)


# ── Tests: crear_muchos ─────────────────────────────────────────────


class TestCrearMuchos:
    async def test_crea_n_comunicaciones_con_mismo_lote(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        repo: ComunicacionRepository,
        db_session: AsyncSession,
    ) -> None:
        lote_id = uuid.uuid4()
        destinatarios = [
            {"tipo": "email", "valor": f"alumno{i}@test.com"}
            for i in range(3)
        ]

        creadas = await repo.crear_muchos(
            tenant_id=tenant.id,
            enviado_por_id=usuario,
            materia_id=materia,
            lote_id=lote_id,
            asunto="Test",
            cuerpo="Cuerpo",
            destinatarios=destinatarios,
        )
        await db_session.commit()

        assert len(creadas) == 3
        for c in creadas:
            assert c.lote_id == lote_id
            assert c.estado == EstadoComunicacion.Pendiente
            assert c.tenant_id == tenant.id

    async def test_crea_sin_materia(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        repo: ComunicacionRepository,
        db_session: AsyncSession,
    ) -> None:
        lote_id = uuid.uuid4()
        destinatarios = [{"tipo": "email", "valor": "alumno@test.com"}]

        creadas = await repo.crear_muchos(
            tenant_id=tenant.id,
            enviado_por_id=usuario,
            materia_id=None,
            lote_id=lote_id,
            asunto="Test",
            cuerpo="Cuerpo",
            destinatarios=destinatarios,
        )
        await db_session.commit()

        assert len(creadas) == 1
        assert creadas[0].materia_id is None


# ── Tests: listar_por_lote ──────────────────────────────────────────


class TestListarPorLote:
    async def test_devuelve_conteos_correctos(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        repo: ComunicacionRepository,
        db_session: AsyncSession,
    ) -> None:
        lote_id = uuid.uuid4()
        await _seed_comunicacion(db_session, tenant.id, usuario, lote_id, materia, EstadoComunicacion.Enviado)
        await _seed_comunicacion(db_session, tenant.id, usuario, lote_id, materia, EstadoComunicacion.Error)
        await _seed_comunicacion(db_session, tenant.id, usuario, lote_id, materia, EstadoComunicacion.Pendiente)
        await db_session.commit()

        resultado = await repo.listar_por_lote(tenant.id, lote_id)
        assert resultado["total"] == 3
        assert resultado["enviados"] == 1
        assert resultado["fallidos"] == 1
        assert resultado["pendientes"] == 1
        assert resultado["cancelados"] == 0

    async def test_aislamiento_tenant(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        repo: ComunicacionRepository,
        db_session: AsyncSession,
    ) -> None:
        lote_id = uuid.uuid4()
        otro_tenant_id = uuid.uuid4()
        otro_tenant = Tenant(id=otro_tenant_id, tenant_id=otro_tenant_id, nombre="Otro")
        db_session.add(otro_tenant)
        await db_session.flush()

        otro_user = await _seed_usuario(db_session, otro_tenant_id)
        await _seed_comunicacion(db_session, otro_tenant_id, otro_user, lote_id, materia, EstadoComunicacion.Enviado)
        await db_session.commit()

        resultado = await repo.listar_por_lote(tenant.id, lote_id)
        assert resultado["total"] == 0


# ── Tests: listar_pendientes_worker ─────────────────────────────────


class TestListarPendientesWorker:
    async def test_devuelve_solo_pendientes(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        repo: ComunicacionRepository,
        db_session: AsyncSession,
    ) -> None:
        lote_id = uuid.uuid4()
        await _seed_comunicacion(db_session, tenant.id, usuario, lote_id, materia, EstadoComunicacion.Pendiente)
        await _seed_comunicacion(db_session, tenant.id, usuario, lote_id, materia, EstadoComunicacion.Enviado)
        await _seed_comunicacion(db_session, tenant.id, usuario, lote_id, materia, EstadoComunicacion.Error)
        await db_session.commit()

        pendientes = await repo.listar_pendientes_worker(tenant.id, limit=10)
        assert len(pendientes) == 1
        assert pendientes[0].estado == EstadoComunicacion.Pendiente

    async def test_excluye_que_requieren_aprobacion(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        repo: ComunicacionRepository,
        db_session: AsyncSession,
    ) -> None:
        lote_id = uuid.uuid4()
        await _seed_comunicacion(db_session, tenant.id, usuario, lote_id, materia, EstadoComunicacion.Pendiente, necesita_aprobacion=True)
        await _seed_comunicacion(db_session, tenant.id, usuario, lote_id, materia, EstadoComunicacion.Pendiente)
        await db_session.commit()

        pendientes = await repo.listar_pendientes_worker(tenant.id, limit=10)
        assert len(pendientes) == 1

    async def test_aislamiento_tenant(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        repo: ComunicacionRepository,
        db_session: AsyncSession,
    ) -> None:
        otro_tenant_id = uuid.uuid4()
        otro_tenant = Tenant(id=otro_tenant_id, tenant_id=otro_tenant_id, nombre="Otro")
        db_session.add(otro_tenant)
        await db_session.flush()

        otro_user = await _seed_usuario(db_session, otro_tenant_id)
        await _seed_comunicacion(db_session, otro_tenant_id, otro_user, uuid.uuid4(), materia, EstadoComunicacion.Pendiente)
        await db_session.commit()

        pendientes = await repo.listar_pendientes_worker(tenant.id, limit=10)
        assert len(pendientes) == 0


# ── Tests: actualizar_estado ────────────────────────────────────────


class TestActualizarEstado:
    async def test_cambia_estado_y_registra_enviado_at(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        repo: ComunicacionRepository,
        db_session: AsyncSession,
    ) -> None:
        c = await _seed_comunicacion(db_session, tenant.id, usuario, uuid.uuid4(), materia)
        await db_session.commit()

        now = datetime.now(timezone.utc)
        await repo.actualizar_estado(c.id, EstadoComunicacion.Enviado, now)
        await db_session.commit()

        actualizada = await repo.get_by_id(c.id)
        assert actualizada is not None
        assert actualizada.estado == EstadoComunicacion.Enviado
        assert actualizada.enviado_at is not None

    async def test_cambia_a_error(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        repo: ComunicacionRepository,
        db_session: AsyncSession,
    ) -> None:
        c = await _seed_comunicacion(db_session, tenant.id, usuario, uuid.uuid4(), materia)
        await db_session.commit()

        await repo.actualizar_estado(c.id, EstadoComunicacion.Error, None)
        await db_session.commit()

        actualizada = await repo.get_by_id(c.id)
        assert actualizada is not None
        assert actualizada.estado == EstadoComunicacion.Error


# ── Tests: cancelar ─────────────────────────────────────────────────


class TestCancelar:
    async def test_cancela_pendiente_propia(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        repo: ComunicacionRepository,
        db_session: AsyncSession,
    ) -> None:
        c = await _seed_comunicacion(db_session, tenant.id, usuario, uuid.uuid4(), materia)
        await db_session.commit()

        resultado = await repo.cancelar(c.id, usuario)
        await db_session.commit()

        assert resultado is True
        actualizada = await repo.get_by_id(c.id)
        assert actualizada is not None
        assert actualizada.estado == EstadoComunicacion.Cancelado

    async def test_rechaza_cancelar_de_otro_usuario(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        repo: ComunicacionRepository,
        db_session: AsyncSession,
    ) -> None:
        otro_user = await _seed_usuario(db_session, tenant.id)
        c = await _seed_comunicacion(db_session, tenant.id, otro_user, uuid.uuid4(), materia)
        await db_session.commit()

        resultado = await repo.cancelar(c.id, usuario)
        await db_session.commit()

        assert resultado is False
        actualizada = await repo.get_by_id(c.id)
        assert actualizada.estado == EstadoComunicacion.Pendiente

    async def test_rechaza_cancelar_enviado(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        repo: ComunicacionRepository,
        db_session: AsyncSession,
    ) -> None:
        c = await _seed_comunicacion(db_session, tenant.id, usuario, uuid.uuid4(), materia, EstadoComunicacion.Enviado)
        await db_session.commit()

        resultado = await repo.cancelar(c.id, usuario)
        assert resultado is False


# ── Tests: listar_por_usuario ───────────────────────────────────────


class TestListarPorUsuario:
    async def test_devuelve_envios_del_usuario_paginados(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        repo: ComunicacionRepository,
        db_session: AsyncSession,
    ) -> None:
        lote = uuid.uuid4()
        for _ in range(3):
            await _seed_comunicacion(db_session, tenant.id, usuario, lote, materia)
        await db_session.commit()

        items, total = await repo.listar_por_usuario(tenant.id, usuario, pagina=1, tamano=10)
        assert len(items) >= 1
        assert total >= 1


# ── Tests: lotes pendientes aprobación ──────────────────────────────


class TestLotesPendientesAprobacion:
    async def test_devuelve_lotes_que_requieren_aprobacion(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        repo: ComunicacionRepository,
        db_session: AsyncSession,
    ) -> None:
        lote1 = uuid.uuid4()
        lote2 = uuid.uuid4()
        await _seed_comunicacion(db_session, tenant.id, usuario, lote1, materia, necesita_aprobacion=True)
        await _seed_comunicacion(db_session, tenant.id, usuario, lote2, materia)
        await db_session.commit()

        lotes = await repo.listar_lotes_pendientes_aprobacion(tenant.id)
        assert lote1 in lotes
        assert lote2 not in lotes


class TestAprobarLote:
    async def test_aprueba_lote_completo(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        repo: ComunicacionRepository,
        db_session: AsyncSession,
    ) -> None:
        lote_id = uuid.uuid4()
        c1 = await _seed_comunicacion(db_session, tenant.id, usuario, lote_id, materia, necesita_aprobacion=True)
        c2 = await _seed_comunicacion(db_session, tenant.id, usuario, lote_id, materia, necesita_aprobacion=True)
        await db_session.commit()

        await repo.aprobar_lote(lote_id, usuario)
        await db_session.commit()

        for c_id in [c1.id, c2.id]:
            actualizada = await repo.get_by_id(c_id)
            assert actualizada is not None
            assert actualizada.necesita_aprobacion is None
            assert actualizada.aprobado_por_id == usuario

    async def test_rechaza_lote(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        repo: ComunicacionRepository,
        db_session: AsyncSession,
    ) -> None:
        lote_id = uuid.uuid4()
        c = await _seed_comunicacion(db_session, tenant.id, usuario, lote_id, materia, necesita_aprobacion=True)
        await db_session.commit()

        await repo.rechazar_lote(lote_id, usuario)
        await db_session.commit()

        actualizada = await repo.get_by_id(c.id)
        assert actualizada is not None
        assert actualizada.estado == EstadoComunicacion.Cancelado
