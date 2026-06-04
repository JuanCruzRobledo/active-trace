"""Tests de integración para UmbralMateriaRepository (C-10).

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
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
    t = Tenant(id=tid, tenant_id=tid, nombre="UmbralRepoTest")
    db_session.add(t)
    await db_session.flush()
    return t


@pytest_asyncio.fixture
async def materia(tenant: Tenant, db_session: AsyncSession) -> object:
    from app.models.materia import Materia

    m = Materia(tenant_id=tenant.id, codigo="MAT-UMB-1", nombre="Umbral Materia")
    db_session.add(m)
    await db_session.flush()
    return m


@pytest_asyncio.fixture
async def materia_otra(tenant: Tenant, db_session: AsyncSession) -> object:
    from app.models.materia import Materia

    m = Materia(tenant_id=tenant.id, codigo="MAT-UMB-2", nombre="Otra Umbral")
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
        email="coord.umbral.repo@test.com",
        dni="22222222",
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
async def repo(tenant: Tenant, db_session: AsyncSession) -> object:
    from app.repositories.umbral_materia_repository import UmbralMateriaRepository

    return UmbralMateriaRepository(session=db_session, tenant_id=tenant.id)


class TestUmbralMateriaRepositoryFindByAsignacion:
    async def test_retorna_umbral_correcto(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        asignacion: object,
        repo: object,
    ) -> None:
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

        result = await repo.find_by_asignacion(asignacion.id)

        assert result is not None
        assert result.id == u.id
        assert result.umbral_pct == 75
        assert result.valores_aprobatorios == ["Aprobado"]

    async def test_retorna_none_si_no_existe(
        self,
        asignacion: object,
        repo: object,
    ) -> None:
        result = await repo.find_by_asignacion(asignacion.id)

        assert result is None

    async def test_excluye_soft_deleted(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        asignacion: object,
        repo: object,
    ) -> None:
        from app.models.umbral_materia import UmbralMateria

        u = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=asignacion.id,
            materia_id=materia.id,
            umbral_pct=60,
        )
        db_session.add(u)
        await db_session.flush()
        await db_session.refresh(u)

        u.deleted_at = datetime.now(timezone.utc)
        await db_session.flush()

        result = await repo.find_by_asignacion(asignacion.id)

        assert result is None


class TestUmbralMateriaRepositoryFindByMateria:
    async def test_lista_todos_los_umbrales_de_una_materia(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        usuario: object,
        repo: object,
    ) -> None:
        from app.models.asignacion import Asignacion
        from app.models.umbral_materia import UmbralMateria

        a1 = Asignacion(
            tenant_id=tenant.id,
            usuario_id=usuario.id,
            rol="PROFESOR",
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        a2 = Asignacion(
            tenant_id=tenant.id,
            usuario_id=usuario.id,
            rol="PROFESOR",
            desde=datetime(2024, 2, 1, tzinfo=timezone.utc),
        )
        db_session.add_all([a1, a2])
        await db_session.flush()

        u1 = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=a1.id,
            materia_id=materia.id,
            umbral_pct=60,
        )
        u2 = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=a2.id,
            materia_id=materia.id,
            umbral_pct=80,
        )
        db_session.add_all([u1, u2])
        await db_session.flush()

        result = await repo.find_by_materia(materia.id)

        assert len(result) == 2
        ids = {r.id for r in result}
        assert ids == {u1.id, u2.id}

    async def test_excluye_soft_deleted(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        usuario: object,
        repo: object,
    ) -> None:
        from app.models.asignacion import Asignacion
        from app.models.umbral_materia import UmbralMateria

        a1 = Asignacion(
            tenant_id=tenant.id,
            usuario_id=usuario.id,
            rol="PROFESOR",
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        a2 = Asignacion(
            tenant_id=tenant.id,
            usuario_id=usuario.id,
            rol="PROFESOR",
            desde=datetime(2024, 2, 1, tzinfo=timezone.utc),
        )
        db_session.add_all([a1, a2])
        await db_session.flush()

        u1 = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=a1.id,
            materia_id=materia.id,
            umbral_pct=60,
        )
        u2 = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=a2.id,
            materia_id=materia.id,
            umbral_pct=70,
        )
        db_session.add_all([u1, u2])
        await db_session.flush()
        await db_session.refresh(u1)
        await db_session.refresh(u2)

        u1.deleted_at = datetime.now(timezone.utc)
        await db_session.flush()

        result = await repo.find_by_materia(materia.id)

        assert len(result) == 1
        assert result[0].id == u2.id

    async def test_filtra_por_tenant(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        materia_otra: object,
        usuario: object,
        repo: object,
    ) -> None:
        from app.models.asignacion import Asignacion
        from app.models.umbral_materia import UmbralMateria

        a = Asignacion(
            tenant_id=tenant.id,
            usuario_id=usuario.id,
            rol="PROFESOR",
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        db_session.add(a)
        await db_session.flush()

        u1 = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=a.id,
            materia_id=materia.id,
            umbral_pct=60,
        )
        u2 = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=a.id,
            materia_id=materia_otra.id,
            umbral_pct=70,
        )
        db_session.add_all([u1, u2])
        await db_session.flush()

        result = await repo.find_by_materia(materia.id)

        assert len(result) == 1
        assert result[0].id == u1.id


class TestUmbralMateriaRepositoryUpsert:
    async def test_crea_si_no_existe(
        self,
        tenant: Tenant,
        materia: object,
        asignacion: object,
        repo: object,
    ) -> None:
        result = await repo.upsert(
            asignacion_id=asignacion.id,
            materia_id=materia.id,
            umbral_pct=80,
            valores_aprobatorios=["Aprobado"],
        )

        assert result.id is not None
        assert result.asignacion_id == asignacion.id
        assert result.materia_id == materia.id
        assert result.umbral_pct == 80
        assert result.valores_aprobatorios == ["Aprobado"]
        assert result.deleted_at is None

    async def test_actualiza_si_ya_existe(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        asignacion: object,
        repo: object,
    ) -> None:
        from app.models.umbral_materia import UmbralMateria

        u = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=asignacion.id,
            materia_id=materia.id,
            umbral_pct=60,
        )
        db_session.add(u)
        await db_session.flush()
        original_id = u.id

        result = await repo.upsert(
            asignacion_id=asignacion.id,
            materia_id=materia.id,
            umbral_pct=85,
            valores_aprobatorios=["Promocionado"],
        )

        assert result.id == original_id
        assert result.umbral_pct == 85
        assert result.valores_aprobatorios == ["Promocionado"]
        assert result.deleted_at is None

    async def test_reactiva_si_esta_soft_deleted(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        asignacion: object,
        repo: object,
    ) -> None:
        from app.models.umbral_materia import UmbralMateria

        u = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=asignacion.id,
            materia_id=materia.id,
            umbral_pct=60,
        )
        db_session.add(u)
        await db_session.flush()
        await db_session.refresh(u)

        u.deleted_at = datetime.now(timezone.utc)
        await db_session.flush()

        result = await repo.upsert(
            asignacion_id=asignacion.id,
            materia_id=materia.id,
            umbral_pct=90,
            valores_aprobatorios=None,
        )

        assert result.id == u.id
        assert result.deleted_at is None
        assert result.umbral_pct == 90
        assert result.valores_aprobatorios is None

    async def test_mantiene_unique_constraint_con_otra_asignacion(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        usuario: object,
        repo: object,
    ) -> None:
        from app.models.asignacion import Asignacion
        from app.models.umbral_materia import UmbralMateria

        a1 = Asignacion(
            tenant_id=tenant.id,
            usuario_id=usuario.id,
            rol="PROFESOR",
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        a2 = Asignacion(
            tenant_id=tenant.id,
            usuario_id=usuario.id,
            rol="PROFESOR",
            desde=datetime(2024, 2, 1, tzinfo=timezone.utc),
        )
        db_session.add_all([a1, a2])
        await db_session.flush()

        u1 = await repo.upsert(
            asignacion_id=a1.id,
            materia_id=materia.id,
            umbral_pct=60,
            valores_aprobatorios=None,
        )
        u2 = await repo.upsert(
            asignacion_id=a2.id,
            materia_id=materia.id,
            umbral_pct=75,
            valores_aprobatorios=None,
        )

        assert u1.id != u2.id
        assert u1.umbral_pct == 60
        assert u2.umbral_pct == 75
