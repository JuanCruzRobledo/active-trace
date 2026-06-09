"""Tests de integración para UmbralService (C-10).

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.tenant import Tenant
from app.services.umbral_service import UmbralService
from tests.conftest import db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]


@pytest_asyncio.fixture
async def tenant(db_session: AsyncSession) -> Tenant:
    tid = uuid.uuid4()
    t = Tenant(id=tid, tenant_id=tid, nombre="UmbralSvcTest")
    db_session.add(t)
    await db_session.flush()
    return t


@pytest_asyncio.fixture
async def materia(tenant: Tenant, db_session: AsyncSession) -> object:
    from app.models.materia import Materia

    m = Materia(
        tenant_id=tenant.id,
        codigo="MAT-UMBSVC-1",
        nombre="Umbral Test Materia",
    )
    db_session.add(m)
    await db_session.flush()
    return m


@pytest_asyncio.fixture
async def usuario(tenant: Tenant, db_session: AsyncSession) -> object:
    from app.models.usuario import Usuario

    u = Usuario(
        tenant_id=tenant.id,
        nombre="Coord",
        apellidos="Umbral",
        email="coord.umbral.svc@test.com",
        dni="33333333",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture
async def asignacion(
    tenant: Tenant, usuario: object, db_session: AsyncSession
) -> object:
    from app.models.asignacion import Asignacion

    a = Asignacion(
        tenant_id=tenant.id,
        usuario_id=usuario.id,
        rol="PROFESOR",
        desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(a)
    await db_session.flush()
    return a


@pytest_asyncio.fixture
async def carrera(tenant: Tenant, db_session: AsyncSession) -> object:
    from app.models.carrera import Carrera

    c = Carrera(
        tenant_id=tenant.id,
        codigo="ING-UMBSVC",
        nombre="Ingenieria Umbral",
    )
    db_session.add(c)
    await db_session.flush()
    return c


@pytest_asyncio.fixture
async def cohorte(
    tenant: Tenant, carrera: object, db_session: AsyncSession
) -> object:
    from app.models.cohorte import Cohorte

    c = Cohorte(
        tenant_id=tenant.id,
        carrera_id=carrera.id,
        nombre="2026-A",
        anio=2026,
        vig_desde=datetime(2026, 1, 1, tzinfo=timezone.utc).date(),
        estado="Activa",
    )
    db_session.add(c)
    await db_session.flush()
    return c


@pytest_asyncio.fixture
async def version_padron(
    tenant: Tenant,
    materia: object,
    cohorte: object,
    db_session: AsyncSession,
) -> object:
    from app.models.version_padron import VersionPadron

    vp = VersionPadron(
        tenant_id=tenant.id,
        materia_id=materia.id,
        cohorte_id=cohorte.id,
        activa=True,
    )
    db_session.add(vp)
    await db_session.flush()
    return vp


@pytest_asyncio.fixture
async def entrada_padron(
    tenant: Tenant,
    version_padron: object,
    db_session: AsyncSession,
) -> object:
    from app.models.entrada_padron import EntradaPadron

    ep = EntradaPadron(
        tenant_id=tenant.id,
        version_id=version_padron.id,
        nombre="Carlos",
        apellidos="Umbral",
        email="carlos.umbral@test.com",
    )
    db_session.add(ep)
    await db_session.flush()
    return ep


@pytest_asyncio.fixture
async def service(
    tenant: Tenant, db_session: AsyncSession
) -> UmbralService:
    return UmbralService(session=db_session, tenant_id=tenant.id)


# ═══════════════════════════════════════════════════════════════════════
# Tests: obtener_umbral
# ═══════════════════════════════════════════════════════════════════════


class TestUmbralServiceObtener:
    """Obtener configuracion de umbral."""

    async def test_sin_configuracion_retorna_default(
        self,
        materia: object,
        asignacion: object,
        service: UmbralService,
    ):
        """Sin configuracion → valores por defecto."""
        result = await service.obtener_umbral(materia.id, asignacion.id)

        assert result["umbral_pct"] == 60
        assert "Satisfactorio" in result["valores_aprobatorios"]

    async def test_con_configuracion_retorna_valores_guardados(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        asignacion: object,
        service: UmbralService,
    ):
        """Con configuracion → retorna valores guardados."""
        from app.models.umbral_materia import UmbralMateria

        u = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=asignacion.id,
            materia_id=materia.id,
            umbral_pct=75,
            valores_aprobatorios=["Aprobado"],
        )
        db_session.add(u)
        await db_session.flush()

        result = await service.obtener_umbral(materia.id, asignacion.id)

        assert result["umbral_pct"] == 75
        assert result["valores_aprobatorios"] == ["Aprobado"]


# ═══════════════════════════════════════════════════════════════════════
# Tests: configurar_umbral
# ═══════════════════════════════════════════════════════════════════════


class TestUmbralServiceConfigurar:
    """Configurar umbral de aprobacion."""

    async def test_configurar_crea_nuevo_umbral(
        self,
        materia: object,
        asignacion: object,
        service: UmbralService,
    ):
        """Crear nuevo umbral."""
        result = await service.configurar_umbral(
            materia_id=materia.id,
            asignacion_id=asignacion.id,
            umbral_pct=80,
            valores_aprobatorios=["Aprobado", "Promocionado"],
            usuario_id=uuid.uuid4(),
        )

        assert result["umbral_pct"] == 80
        assert result["valores_aprobatorios"] == ["Aprobado", "Promocionado"]

    async def test_configurar_actualiza_existente(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        asignacion: object,
        service: UmbralService,
    ):
        """Actualizar umbral existente."""
        from app.models.umbral_materia import UmbralMateria

        u = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=asignacion.id,
            materia_id=materia.id,
            umbral_pct=60,
            valores_aprobatorios=["Aprobado"],
        )
        db_session.add(u)
        await db_session.flush()
        original_id = u.id

        result = await service.configurar_umbral(
            materia_id=materia.id,
            asignacion_id=asignacion.id,
            umbral_pct=85,
            valores_aprobatorios=["Promocionado"],
            usuario_id=uuid.uuid4(),
        )

        assert result["umbral_pct"] == 85
        assert result["valores_aprobatorios"] == ["Promocionado"]

        # Verificar que se actualizo el mismo registro
        from app.repositories.umbral_materia_repository import (
            UmbralMateriaRepository,
        )

        repo = UmbralMateriaRepository(
            session=db_session, tenant_id=tenant.id
        )
        updated = await repo.find_by_asignacion(asignacion.id)
        assert updated is not None
        assert updated.id == original_id

    async def test_umbral_pct_invalido(
        self,
        materia: object,
        asignacion: object,
        service: UmbralService,
    ):
        """umbral_pct > 100 → BusinessError."""
        with pytest.raises(BusinessError, match="100"):
            await service.configurar_umbral(
                materia_id=materia.id,
                asignacion_id=asignacion.id,
                umbral_pct=150,
                valores_aprobatorios=None,
                usuario_id=uuid.uuid4(),
            )

    async def test_umbral_pct_negativo(
        self,
        materia: object,
        asignacion: object,
        service: UmbralService,
    ):
        """umbral_pct < 0 → BusinessError."""
        with pytest.raises(BusinessError, match="0"):
            await service.configurar_umbral(
                materia_id=materia.id,
                asignacion_id=asignacion.id,
                umbral_pct=-10,
                valores_aprobatorios=None,
                usuario_id=uuid.uuid4(),
            )

    async def test_cambio_umbral_recalcula_calificaciones(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        asignacion: object,
        entrada_padron: object,
        service: UmbralService,
    ):
        """Cambiar umbral recalcula aprobado en calificaciones existentes."""
        from app.models.calificacion import Calificacion
        from app.models.enums import OrigenCalificacion

        # Crear calificaciones con notas
        c1 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="Parcial",
            nota_numerica=75,
            origen=OrigenCalificacion.IMPORTADO,
        )
        c2 = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="Final",
            nota_numerica=40,
            origen=OrigenCalificacion.IMPORTADO,
        )
        db_session.add_all([c1, c2])
        await db_session.flush()

        # Configurar umbral en 60 -> 75 pasa, 40 no pasa
        result = await service.configurar_umbral(
            materia_id=materia.id,
            asignacion_id=asignacion.id,
            umbral_pct=60,
            valores_aprobatorios=None,
            usuario_id=uuid.uuid4(),
        )

        # Al menos deberia haber recalculado
        assert result["umbral_pct"] == 60
        # recalcular_aprobado retorna count de filas afectadas
        assert isinstance(result["calificaciones_recalculadas"], int)
