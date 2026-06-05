"""Tests de integración para ComunicacionService (C-12).

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comunicacion import Comunicacion, EstadoComunicacion
from app.models.tenant import Tenant
from app.repositories.comunicacion_repository import ComunicacionRepository
from app.services.comunicacion_service import ComunicacionService
from app.core.config import Settings
from tests.conftest import _DEV_TENANT_ID, db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]


# ── Seeds ────────────────────────────────────────────────────────────


async def _seed_tenant(db_session: AsyncSession) -> Tenant:
    tid = uuid.uuid4()
    t = Tenant(id=tid, tenant_id=tid, nombre="ComServiceTest")
    db_session.add(t)
    await db_session.flush()
    return t


async def _seed_materia(db_session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    from app.models.materia import Materia

    m = Materia(tenant_id=tenant_id, codigo="MAT-COMSRV", nombre="Com Service Test")
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


async def _seed_alumno_en_padron(
    db_session: AsyncSession, tenant_id: uuid.UUID, materia_id: uuid.UUID
) -> uuid.UUID:
    """Crea un alumno en el padrón para una materia. Retorna entrada_padron_id."""
    from app.models.usuario import Usuario
    from app.models.version_padron import VersionPadron
    from app.models.entrada_padron import EntradaPadron
    from app.models.cohorte import Cohorte
    from app.models.carrera import Carrera

    carrera = Carrera(tenant_id=tenant_id, codigo="C-CSRV", nombre="Carrera Service")
    db_session.add(carrera)
    await db_session.flush()

    cohorte = Cohorte(
        tenant_id=tenant_id,
        carrera_id=carrera.id,
        nombre="2026-A",
        anio=2026,
        vig_desde=datetime(2026, 1, 1, tzinfo=timezone.utc).date(),
        estado="Activa",
    )
    db_session.add(cohorte)
    await db_session.flush()

    uid = uuid.uuid4()
    user = Usuario(
        id=uid,
        tenant_id=tenant_id,
        email=f"alumno{uuid.uuid4().hex[:4]}@test.com",
        nombre="Alumno",
        apellidos="Test",
        estado="Activo",
    )
    db_session.add(user)
    await db_session.flush()

    vp = VersionPadron(
        tenant_id=tenant_id,
        materia_id=materia_id,
        cohorte_id=cohorte.id,
        cargado_por=uid,
        cargado_at=datetime.now(timezone.utc),
        activa=True,
    )
    db_session.add(vp)
    await db_session.flush()

    ep = EntradaPadron(
        tenant_id=tenant_id,
        version_id=vp.id,
        usuario_id=uid,
        nombre="Alumno",
        apellidos="Test",
        email=f"alumno{uuid.uuid4().hex[:4]}@test.com",
        comision="A",
    )
    db_session.add(ep)
    await db_session.flush()
    return ep.id


async def _seed_profesor_con_asignacion(
    db_session: AsyncSession, tenant_id: uuid.UUID, materia_id: uuid.UUID
) -> uuid.UUID:
    """Crea un usuario PROFESOR asignado a una materia. Retorna usuario_id."""
    from app.models.usuario import Usuario
    from app.models.asignacion import Asignacion

    uid = uuid.uuid4()
    user = Usuario(
        id=uid,
        tenant_id=tenant_id,
        email=f"prof{uuid.uuid4().hex[:4]}@test.com",
        nombre="Profe",
        apellidos="Test",
        estado="Activo",
    )
    db_session.add(user)
    await db_session.flush()

    asig = Asignacion(
        tenant_id=tenant_id,
        usuario_id=uid,
        rol="PROFESOR",
        materia_id=materia_id,
        desde=datetime.now(timezone.utc),
    )
    db_session.add(asig)
    await db_session.flush()
    return uid


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
async def service(
    tenant: Tenant, db_session: AsyncSession
) -> ComunicacionService:
    repo = ComunicacionRepository(db_session, tenant.id)
    return ComunicacionService(session=db_session, tenant_id=tenant.id, repo=repo)


# ── Tests: Preview ──────────────────────────────────────────────────


class TestPreview:
    async def test_genera_token_consistente(
        self,
        service: ComunicacionService,
    ) -> None:
        resultado = await service.generar_preview(
            asunto="Test",
            cuerpo="Cuerpo",
            destinatarios=[{"tipo": "email", "valor": "a@test.com"}],
        )
        assert "preview_token" in resultado
        assert resultado["cantidad_destinatarios"] == 1
        assert "preview_html" in resultado

        # Verificar consistencia
        resultado2 = await service.generar_preview(
            asunto="Test",
            cuerpo="Cuerpo",
            destinatarios=[{"tipo": "email", "valor": "a@test.com"}],
        )
        assert resultado["preview_token"] == resultado2["preview_token"]

    async def test_token_cambia_con_contenido(
        self,
        service: ComunicacionService,
    ) -> None:
        r1 = await service.generar_preview(
            asunto="Test",
            cuerpo="Cuerpo A",
            destinatarios=[{"tipo": "email", "valor": "a@test.com"}],
        )
        r2 = await service.generar_preview(
            asunto="Test",
            cuerpo="Cuerpo B",
            destinatarios=[{"tipo": "email", "valor": "a@test.com"}],
        )
        assert r1["preview_token"] != r2["preview_token"]


class TestValidarPreview:
    async def test_valida_token_valido(
        self,
        service: ComunicacionService,
    ) -> None:
        token = service._generar_hash(
            asunto="Test",
            cuerpo="Cuerpo",
            destinatarios=[{"tipo": "email", "valor": "a@test.com"}],
        )
        result = service.validar_preview(
            preview_token=token,
            asunto="Test",
            cuerpo="Cuerpo",
            destinatarios=[{"tipo": "email", "valor": "a@test.com"}],
        )
        assert result is True

    async def test_rechaza_token_invalido(
        self,
        service: ComunicacionService,
    ) -> None:
        result = service.validar_preview(
            preview_token="token_invalido",
            asunto="Test",
            cuerpo="Cuerpo",
            destinatarios=[{"tipo": "email", "valor": "a@test.com"}],
        )
        assert result is False


# ── Tests: Encolar Envío ────────────────────────────────────────────


class TestEncolarEnvio:
    async def test_encola_comunicaciones(
        self,
        tenant: Tenant,
        materia: uuid.UUID,
        usuario: uuid.UUID,
        service: ComunicacionService,
        db_session: AsyncSession,
    ) -> None:
        destinatarios = [
            {"tipo": "email", "valor": f"alumno{i}@test.com"}
            for i in range(2)
        ]
        token = service._generar_hash(
            asunto="Test", cuerpo="Cuerpo", destinatarios=destinatarios
        )

        resultado = await service.encolar_envio(
            usuario_id=usuario,
            tenant_id=tenant.id,
            preview_token=token,
            asunto="Test",
            cuerpo="Cuerpo",
            materia_id=materia,
            destinatarios=destinatarios,
            roles=["ADMIN"],
        )
        await db_session.commit()

        assert "lote_id" in resultado
        assert resultado["total_mensajes"] == 2
        assert resultado["estado_agregado"] == "Pendiente"

    async def test_rechaza_preview_invalida(
        self,
        tenant: Tenant,
        materia: uuid.UUID,
        usuario: uuid.UUID,
        service: ComunicacionService,
    ) -> None:
        from app.core.exceptions import BusinessError

        with pytest.raises(BusinessError, match="no coincide"):
            await service.encolar_envio(
                usuario_id=usuario,
                tenant_id=tenant.id,
                preview_token="token_invalido",
                asunto="Test",
                cuerpo="Cuerpo",
                materia_id=materia,
                destinatarios=[{"tipo": "email", "valor": "a@test.com"}],
                roles=["ADMIN"],
            )

    async def test_profesor_envia_a_su_comision(
        self,
        tenant: Tenant,
        materia: uuid.UUID,
        service: ComunicacionService,
        db_session: AsyncSession,
    ) -> None:
        profe_id = await _seed_profesor_con_asignacion(db_session, tenant.id, materia)
        await _seed_alumno_en_padron(db_session, tenant.id, materia)
        await db_session.commit()

        destinatarios = [{"tipo": "email", "valor": "alumno@test.com"}]
        token = service._generar_hash(
            asunto="Test", cuerpo="Cuerpo", destinatarios=destinatarios
        )

        resultado = await service.encolar_envio(
            usuario_id=profe_id,
            tenant_id=tenant.id,
            preview_token=token,
            asunto="Test",
            cuerpo="Cuerpo",
            materia_id=materia,
            destinatarios=destinatarios,
            roles=["PROFESOR"],
        )
        await db_session.commit()

        assert resultado["total_mensajes"] == 1

    async def test_encolar_con_aprobacion_requerida(
        self,
        tenant: Tenant,
        materia: uuid.UUID,
        usuario: uuid.UUID,
        service: ComunicacionService,
        db_session: AsyncSession,
    ) -> None:
        from app.services.comunicacion_service import hash_destinatarios

        destinatarios = [
            {"tipo": "email", "valor": f"alumno{i}@test.com"}
            for i in range(3)
        ]
        token = service._generar_hash(
            asunto="Test", cuerpo="Cuerpo", destinatarios=destinatarios
        )

        resultado = await service.encolar_envio(
            usuario_id=usuario,
            tenant_id=tenant.id,
            preview_token=token,
            asunto="Test",
            cuerpo="Cuerpo",
            materia_id=materia,
            destinatarios=destinatarios,
            roles=["ADMIN"],
            requiere_aprobacion=True,
        )
        await db_session.commit()

        assert resultado["requiere_aprobacion"] is True
        assert resultado["estado_agregado"] == "Pendiente"


class TestEncolarEnvioIndividual:
    async def test_encola_individual(
        self,
        tenant: Tenant,
        materia: uuid.UUID,
        usuario: uuid.UUID,
        service: ComunicacionService,
        db_session: AsyncSession,
    ) -> None:
        ep_id = await _seed_alumno_en_padron(db_session, tenant.id, materia)
        await db_session.commit()

        token = service._generar_hash(
            asunto="Test",
            cuerpo="Cuerpo",
            destinatarios=[{"tipo": "entrada_padron_id", "valor": str(ep_id)}],
        )

        resultado = await service.encolar_envio_individual(
            usuario_id=usuario,
            tenant_id=tenant.id,
            preview_token=token,
            asunto="Test",
            cuerpo="Cuerpo",
            materia_id=materia,
            entrada_padron_id=ep_id,
            roles=["ADMIN"],
        )
        await db_session.commit()

        assert resultado["total_mensajes"] == 1
        assert resultado["estado_agregado"] == "Pendiente"


class TestObtenerEstadoLote:
    async def test_devuelve_estado(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        service: ComunicacionService,
        db_session: AsyncSession,
    ) -> None:
        lote_id = uuid.uuid4()
        from app.models.comunicacion import Comunicacion

        for estado in [EstadoComunicacion.Enviado, EstadoComunicacion.Error]:
            c = Comunicacion(
                tenant_id=tenant.id,
                enviado_por_id=usuario,
                materia_id=materia,
                destinatario="a@test.com",
                asunto="Test",
                cuerpo="Cuerpo",
                estado=estado,
                lote_id=lote_id,
            )
            db_session.add(c)
        await db_session.commit()

        resultado = await service.obtener_estado_lote(tenant.id, lote_id)
        assert resultado["total"] == 2
        assert resultado["enviados"] == 1
        assert resultado["fallidos"] == 1


class TestCancelarComunicacion:
    async def test_cancela_pendiente(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        service: ComunicacionService,
        db_session: AsyncSession,
    ) -> None:
        c = Comunicacion(
            tenant_id=tenant.id,
            enviado_por_id=usuario,
            materia_id=materia,
            destinatario="a@test.com",
            asunto="Test",
            cuerpo="Cuerpo",
            estado=EstadoComunicacion.Pendiente,
            lote_id=uuid.uuid4(),
        )
        db_session.add(c)
        await db_session.commit()

        resultado = await service.cancelar_comunicacion(c.lote_id, usuario)
        assert resultado["estado"] == "Cancelado"


class TestAprobarRechazarLote:
    async def test_aprueba_lote(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        service: ComunicacionService,
        db_session: AsyncSession,
    ) -> None:
        lote_id = uuid.uuid4()
        c = Comunicacion(
            tenant_id=tenant.id,
            enviado_por_id=usuario,
            materia_id=materia,
            destinatario="a@test.com",
            asunto="Test",
            cuerpo="Cuerpo",
            estado=EstadoComunicacion.Pendiente,
            lote_id=lote_id,
            necesita_aprobacion=uuid.uuid4(),
        )
        db_session.add(c)
        await db_session.commit()

        await service.aprobar_lote(lote_id, usuario)
        from sqlalchemy import select
        stmt = select(Comunicacion).where(Comunicacion.id == c.id).execution_options(populate_existing=True)
        result = await db_session.execute(stmt)
        actualizada = result.scalar_one()
        assert actualizada is not None
        assert actualizada.necesita_aprobacion is None
        assert actualizada.aprobado_por_id == usuario

    async def test_rechaza_lote(
        self,
        tenant: Tenant,
        usuario: uuid.UUID,
        materia: uuid.UUID,
        service: ComunicacionService,
        db_session: AsyncSession,
    ) -> None:
        lote_id = uuid.uuid4()
        c = Comunicacion(
            tenant_id=tenant.id,
            enviado_por_id=usuario,
            materia_id=materia,
            destinatario="a@test.com",
            asunto="Test",
            cuerpo="Cuerpo",
            estado=EstadoComunicacion.Pendiente,
            lote_id=lote_id,
            necesita_aprobacion=uuid.uuid4(),
        )
        db_session.add(c)
        await db_session.commit()

        await service.rechazar_lote(lote_id, usuario)
        from sqlalchemy import select
        stmt = select(Comunicacion).where(Comunicacion.id == c.id).execution_options(populate_existing=True)
        result = await db_session.execute(stmt)
        actualizada = result.scalar_one()
        assert actualizada is not None
        assert actualizada.estado == EstadoComunicacion.Cancelado
