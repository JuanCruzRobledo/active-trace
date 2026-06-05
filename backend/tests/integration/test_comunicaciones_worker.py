"""Tests de integración para el worker asíncrono de comunicaciones (C-12).

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comunicacion import Comunicacion, EstadoComunicacion
from app.models.tenant import Tenant
from tests.conftest import db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]


# ── Seeds ────────────────────────────────────────────────────────────


async def _seed_tenant(
    db_session: AsyncSession,
    config: dict | None = None,
) -> Tenant:
    tid = uuid.uuid4()
    t = Tenant(id=tid, tenant_id=tid, nombre="WorkerTest", config=config or {})
    db_session.add(t)
    await db_session.flush()
    return t


async def _seed_materia(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    from app.models.materia import Materia

    m = Materia(tenant_id=tenant_id, codigo="MAT-WRK", nombre="Worker Test")
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
        nombre="Worker",
        apellidos="Test",
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
    necesita_aprobacion: uuid.UUID | None = None,
) -> Comunicacion:
    c = Comunicacion(
        tenant_id=tenant_id,
        enviado_por_id=enviado_por_id,
        materia_id=materia_id,
        destinatario=f"alumno{uuid.uuid4().hex[:4]}@test.com",
        asunto="Worker test",
        cuerpo="Cuerpo de prueba",
        estado=estado,
        lote_id=lote_id,
        necesita_aprobacion=necesita_aprobacion,
    )
    db_session.add(c)
    await db_session.flush()
    return c


# ── Provider de prueba ────────────────────────────────────────────────


class _TestProvider:
    """Provider controlable para tests — permite simular fallos."""

    def __init__(self, debe_fallar: bool = False) -> None:
        self.debe_fallar = debe_fallar
        self.llamadas: list[dict] = []

    async def enviar(self, destinatario: str, asunto: str, cuerpo: str) -> bool:
        self.llamadas.append(
            {"destinatario": destinatario, "asunto": asunto, "cuerpo": cuerpo}
        )
        if self.debe_fallar:
            return False
        return True


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def tenant(db_session: AsyncSession) -> Tenant:
    return await _seed_tenant(db_session, config={"aprobacion_comunicaciones_requerida": True})


@pytest_asyncio.fixture
async def tenant_sin_aprobacion(db_session: AsyncSession) -> Tenant:
    return await _seed_tenant(
        db_session, config={"aprobacion_comunicaciones_requerida": False}
    )


@pytest_asyncio.fixture
async def usuario(db_session: AsyncSession, tenant: Tenant) -> uuid.UUID:
    return await _seed_usuario(db_session, tenant.id)


@pytest_asyncio.fixture
async def materia(db_session: AsyncSession, tenant: Tenant) -> uuid.UUID:
    return await _seed_materia(db_session, tenant.id)


# ── Tests: procesar_comunicacion ─────────────────────────────────────


class TestProcesarComunicacion:
    async def test_envio_exitoso(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        db_session: AsyncSession,
    ) -> None:
        """Procesar una comunicación con provider que retorna True → Enviado."""
        from workers.comunicaciones_worker import procesar_comunicacion

        c = await _seed_comunicacion(
            db_session, tenant.id, usuario, uuid.uuid4(), materia
        )
        await db_session.commit()

        provider = _TestProvider(debe_fallar=False)
        estado = await procesar_comunicacion(c, provider)

        assert estado == EstadoComunicacion.Enviado
        assert len(provider.llamadas) == 1
        assert provider.llamadas[0]["destinatario"] == c.destinatario

    async def test_envio_fallido(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        db_session: AsyncSession,
    ) -> None:
        """Procesar una comunicación con provider que retorna False → Error."""
        from workers.comunicaciones_worker import procesar_comunicacion

        c = await _seed_comunicacion(
            db_session, tenant.id, usuario, uuid.uuid4(), materia
        )
        await db_session.commit()

        provider = _TestProvider(debe_fallar=True)
        estado = await procesar_comunicacion(c, provider)

        assert estado == EstadoComunicacion.Error
        assert len(provider.llamadas) == 1


# ── Tests: procesar_lote ──────────────────────────────────────────────


class TestProcesarLote:
    async def test_procesa_pendiente_a_enviado(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        db_session: AsyncSession,
    ) -> None:
        """Worker procesa Pendiente → estado Enviado."""
        from workers.comunicaciones_worker import procesar_lote

        lote_id = uuid.uuid4()
        await _seed_comunicacion(
            db_session, tenant.id, usuario, lote_id, materia,
            estado=EstadoComunicacion.Pendiente,
        )
        await db_session.commit()

        provider = _TestProvider(debe_fallar=False)
        n = await procesar_lote(db_session, provider, batch_size=10)

        assert n == 1

        # Verificar que la comunicación se actualizó
        stmt = select(Comunicacion).where(Comunicacion.lote_id == lote_id)
        result = await db_session.execute(stmt)
        actualizada = result.scalar_one()
        assert actualizada.estado == EstadoComunicacion.Enviado
        assert actualizada.enviado_at is not None

    async def test_procesa_pendiente_y_falla_a_error(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        db_session: AsyncSession,
    ) -> None:
        """Worker procesa Pendiente y el provider falla → estado Error."""
        from workers.comunicaciones_worker import procesar_lote

        lote_id = uuid.uuid4()
        await _seed_comunicacion(
            db_session, tenant.id, usuario, lote_id, materia,
            estado=EstadoComunicacion.Pendiente,
        )
        await db_session.commit()

        provider = _TestProvider(debe_fallar=True)
        n = await procesar_lote(db_session, provider, batch_size=10)

        assert n == 1

        stmt = select(Comunicacion).where(Comunicacion.lote_id == lote_id)
        result = await db_session.execute(stmt)
        actualizada = result.scalar_one()
        assert actualizada.estado == EstadoComunicacion.Error
        assert actualizada.enviado_at is not None

    async def test_salta_que_requieren_aprobacion(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        db_session: AsyncSession,
    ) -> None:
        """Worker salta comunicaciones Pendiente con necesita_aprobacion set."""
        from workers.comunicaciones_worker import procesar_lote

        lote_sin_aprobar = uuid.uuid4()
        lote_normal = uuid.uuid4()

        # Esta comunicación requiere aprobación → debe ser saltada
        await _seed_comunicacion(
            db_session, tenant.id, usuario, lote_sin_aprobar, materia,
            estado=EstadoComunicacion.Pendiente,
            necesita_aprobacion=uuid.uuid4(),
        )
        # Esta no requiere aprobación → debe ser procesada
        await _seed_comunicacion(
            db_session, tenant.id, usuario, lote_normal, materia,
            estado=EstadoComunicacion.Pendiente,
            necesita_aprobacion=None,
        )
        await db_session.commit()

        provider = _TestProvider(debe_fallar=False)
        n = await procesar_lote(db_session, provider, batch_size=10)

        # Solo 1 debe procesarse (la sin aprobación)
        assert n == 1

        # La comunicación con necesita_aprobacion sigue Pendiente
        stmt = select(Comunicacion).where(Comunicacion.lote_id == lote_sin_aprobar)
        result = await db_session.execute(stmt)
        sin_aprobar = result.scalar_one()
        assert sin_aprobar.estado == EstadoComunicacion.Pendiente

    async def test_procesa_lote_aprobado_cuando_tenant_no_requiere_aprobacion(
        self,
        tenant_sin_aprobacion: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        db_session: AsyncSession,
    ) -> None:
        """Worker procesa todas las Pendientes si tenant no requiere aprobación."""
        from workers.comunicaciones_worker import procesar_lote

        lote_con_aprobacion = uuid.uuid4()
        lote_normal = uuid.uuid4()

        # Esta comunicación requiere aprobación pero el tenant no la requiere
        # → debe procesarse igual
        await _seed_comunicacion(
            db_session, tenant_sin_aprobacion.id, usuario, lote_con_aprobacion, materia,
            estado=EstadoComunicacion.Pendiente,
            necesita_aprobacion=uuid.uuid4(),
        )
        # Esta no requiere aprobación → debe procesarse
        await _seed_comunicacion(
            db_session, tenant_sin_aprobacion.id, usuario, lote_normal, materia,
            estado=EstadoComunicacion.Pendiente,
            necesita_aprobacion=None,
        )
        await db_session.commit()

        provider = _TestProvider(debe_fallar=False)
        n = await procesar_lote(db_session, provider, batch_size=10)

        # Ambas deben procesarse (tenant no requiere aprobación)
        assert n == 2

        stmt = select(Comunicacion).where(
            Comunicacion.tenant_id == tenant_sin_aprobacion.id
        )
        result = await db_session.execute(stmt)
        comunicaciones = result.scalars().all()
        for c in comunicaciones:
            assert c.estado == EstadoComunicacion.Enviado

    async def test_sin_pendientes_no_procesa_nada(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        db_session: AsyncSession,
    ) -> None:
        """Worker retorna 0 si no hay comunicaciones Pendiente."""
        from workers.comunicaciones_worker import procesar_lote

        # Solo comunicaciones Enviado
        await _seed_comunicacion(
            db_session, tenant.id, usuario, uuid.uuid4(), materia,
            estado=EstadoComunicacion.Enviado,
        )
        await db_session.commit()

        provider = _TestProvider(debe_fallar=False)
        n = await procesar_lote(db_session, provider, batch_size=10)
        assert n == 0
