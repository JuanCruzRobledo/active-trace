"""Tests de servicio de padron-ingesta (C-09) para reglas de negocio.

Cubre:
- RN-04: Vaciar borra solo la materia indicada, no afecta otras
- Multi-tenancy: tenants distintos NO ven entradas del otro
- Matching por email contra usuarios del tenant
- Versionado: nueva importacion desactiva version anterior
- Confirm con cache invalido
- Preview token expirado
"""

from __future__ import annotations

import io
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.services.padron_service import PadronService
from tests.conftest import db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]

_DEV_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
_OTHER_TENANT_ID = UUID("00000000-0000-0000-0000-000000000002")


def _make_xlsx_bytes(filas: list[tuple[str, str, str, str, str]]) -> bytes:
    """Genera un xlsx en memoria con las filas dadas."""
    try:
        import openpyxl  # noqa: PLC0415
    except ImportError:
        pytest.skip("openpyxl no instalado")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Alumnos"
    ws.append(["nombre", "apellidos", "email", "comision", "regional"])
    for row in filas:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


async def _seed_tenant(
    db_session: AsyncSession, tenant_id: UUID, nombre: str = "Test Tenant"
) -> None:
    await db_session.execute(
        text(
            "INSERT INTO tenant (id, nombre, created_at, updated_at) "
            "VALUES (:id, :nombre, now(), now()) "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {"id": tenant_id, "nombre": nombre},
    )
    await db_session.commit()


async def _seed_materia(
    db_session: AsyncSession, tenant_id: UUID, materia_id: UUID | None = None
) -> UUID:
    materia_id = materia_id or uuid4()
    carrera_id = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO carrera (id, tenant_id, nombre, codigo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :nombre, :codigo, now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {
            "id": carrera_id,
            "tenant_id": tenant_id,
            "nombre": "Carrera Test",
            "codigo": "TEST",
        },
    )
    await db_session.execute(
        text(
            "INSERT INTO materia (id, tenant_id, nombre, codigo, "
            "carrera_id, carga_horaria, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :nombre, :codigo, :carrera_id, :carga, now(), now()) "
            "ON CONFLICT (tenant_id, codigo) DO NOTHING"
        ),
        {
            "id": materia_id,
            "tenant_id": tenant_id,
            "nombre": "Materia Test",
            "codigo": f"MAT{materia_id.hex[:4].upper()}",
            "carrera_id": carrera_id,
            "carga": 60,
        },
    )
    await db_session.commit()
    return materia_id


async def _seed_cohorte(
    db_session: AsyncSession, tenant_id: UUID, cohorte_id: UUID | None = None
) -> UUID:
    cohorte_id = cohorte_id or uuid4()
    await db_session.execute(
        text(
            "INSERT INTO cohorte (id, tenant_id, nombre, codigo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :nombre, :codigo, now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {
            "id": cohorte_id,
            "tenant_id": tenant_id,
            "nombre": "Cohorte Test",
            "codigo": f"COH{cohorte_id.hex[:4].upper()}",
        },
    )
    await db_session.commit()
    return cohorte_id


async def _seed_usuario(
    db_session: AsyncSession, tenant_id: UUID, email: str
) -> UUID:
    user_id = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO usuario (id, tenant_id, email, nombres, apellidos, "
            "activo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :email, :nombres, :apellidos, true, now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {
            "id": user_id,
            "tenant_id": tenant_id,
            "email": email,
            "nombres": "Nombre",
            "apellidos": "Apellido",
        },
    )
    await db_session.commit()
    return user_id


@pytest.fixture
async def padron_service(db_session: AsyncSession) -> PadronService:
    return PadronService(session=db_session, tenant_id=_DEV_TENANT_ID)


# ═══════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════


class TestPadronServicePreview:
    """Preview de archivos."""

    async def test_preview_xlsx_valido(
        self, db_session: AsyncSession, padron_service: PadronService
    ):
        """F1a: Preview de xlsx con datos correctos."""
        data = _make_xlsx_bytes([
            ("Juan", "Perez", "juan@test.com", "A", "CABA"),
            ("Maria", "Garcia", "maria@test.com", "B", "GBA"),
        ])
        result = await padron_service.preview_importacion(data, "alumnos.xlsx")
        assert result["filas_leidas"] == 2
        assert result["preview"] is True
        assert "preview_token" in result
        assert len(result["filas"]) == 2

    async def test_preview_csv_valido(
        self, db_session: AsyncSession, padron_service: PadronService
    ):
        """F1a: Preview de csv con datos correctos."""
        import csv
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["nombre", "apellidos", "email", "comision", "regional"])
        writer.writerow(["Ana", "Diaz", "ana@test.com", "A", "CABA"])
        data = buf.getvalue().encode("utf-8-sig")

        result = await padron_service.preview_importacion(data, "alumnos.csv")
        assert result["filas_leidas"] == 1
        assert result["preview"] is True

    async def test_preview_formato_invalido(
        self, db_session: AsyncSession, padron_service: PadronService
    ):
        """F1g: Formato de archivo invalido → BusinessError."""
        with pytest.raises(BusinessError, match="formato"):
            await padron_service.preview_importacion(b"not a file", "datos.pdf")


class TestPadronServiceConfirm:
    """Confirm de importacion y versionado."""

    async def test_confirm_crea_version_activa(
        self, db_session: AsyncSession, padron_service: PadronService
    ):
        """F2a: Confirm crea version activa con entradas."""
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        materia_id = await _seed_materia(db_session, _DEV_TENANT_ID)
        cohorte_id = await _seed_cohorte(db_session, _DEV_TENANT_ID)
        user_id = uuid4()

        data = _make_xlsx_bytes([
            ("Juan", "Perez", "juan@test.com", "A", "CABA"),
        ])
        preview = await padron_service.preview_importacion(data, "alumnos.xlsx")
        preview_token = preview["preview_token"]

        version = await padron_service.confirmar_importacion(
            preview_token=preview_token,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            cargado_por=user_id,
        )

        assert version.materia_id == materia_id
        assert version.cohorte_id == cohorte_id
        assert version.activa is True
        assert version.cargado_por == user_id

    async def test_confirm_desactiva_version_anterior(
        self, db_session: AsyncSession, padron_service: PadronService
    ):
        """F2b: Nueva importacion desactiva version anterior de la misma materia."""
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        materia_id = await _seed_materia(db_session, _DEV_TENANT_ID)
        cohorte_id = await _seed_cohorte(db_session, _DEV_TENANT_ID)
        user_id = uuid4()

        data = _make_xlsx_bytes([
            ("Juan", "Perez", "juan@test.com", "A", "CABA"),
        ])

        # Primera importacion
        preview1 = await padron_service.preview_importacion(data, "alumnos.xlsx")
        version1 = await padron_service.confirmar_importacion(
            preview_token=preview1["preview_token"],
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            cargado_por=user_id,
        )
        assert version1.activa is True

        # Segunda importacion
        preview2 = await padron_service.preview_importacion(data, "alumnos.xlsx")
        version2 = await padron_service.confirmar_importacion(
            preview_token=preview2["preview_token"],
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            cargado_por=user_id,
        )
        assert version2.activa is True

        # Version 1 deberia estar inactiva
        act = await padron_service.obtener_activo(materia_id, cohorte_id)
        assert act is not None
        assert act.id == version2.id

    async def test_confirm_token_invalido(
        self, db_session: AsyncSession, padron_service: PadronService
    ):
        """F2c: Preview token invalido → BusinessError."""
        materia_id = uuid4()
        cohorte_id = uuid4()

        with pytest.raises(BusinessError, match="preview"):
            await padron_service.confirmar_importacion(
                preview_token="invalid",
                materia_id=materia_id,
                cohorte_id=cohorte_id,
                cargado_por=uuid4(),
            )


class TestPadronVaciar:
    """Vaciado de padron por materia (RN-04)."""

    async def test_vaciar_materia_desactiva_versiones(
        self, db_session: AsyncSession, padron_service: PadronService
    ):
        """F4a: Vaciar materia desactiva versiones y elimina entradas."""
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        materia_id = await _seed_materia(db_session, _DEV_TENANT_ID)
        cohorte_id = await _seed_cohorte(db_session, _DEV_TENANT_ID)
        user_id = uuid4()

        data = _make_xlsx_bytes([
            ("Juan", "Perez", "juan@test.com", "A", "CABA"),
            ("Maria", "Garcia", "maria@test.com", "B", "GBA"),
        ])
        preview = await padron_service.preview_importacion(data, "alumnos.xlsx")
        await padron_service.confirmar_importacion(
            preview_token=preview["preview_token"],
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            cargado_por=user_id,
        )

        result = await padron_service.vaciar_materia(materia_id)
        assert result["versiones_desactivadas"] >= 1
        assert result["entradas_eliminadas"] == 2

        activo = await padron_service.obtener_activo(materia_id, cohorte_id)
        assert activo is None

    async def test_vaciar_solo_materia_indicada(
        self, db_session: AsyncSession, padron_service: PadronService
    ):
        """RN-04: Vaciar no afecta versiones de otra materia."""
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        materia_a = await _seed_materia(db_session, _DEV_TENANT_ID)
        materia_b = await _seed_materia(db_session, _DEV_TENANT_ID)
        cohorte_id = await _seed_cohorte(db_session, _DEV_TENANT_ID)
        user_id = uuid4()

        data = _make_xlsx_bytes([("Juan", "Perez", "juan@test.com", "A", "CABA")])

        # Importar en ambas materias
        for materia_id in (materia_a, materia_b):
            preview = await padron_service.preview_importacion(data, "alumnos.xlsx")
            await padron_service.confirmar_importacion(
                preview_token=preview["preview_token"],
                materia_id=materia_id,
                cohorte_id=cohorte_id,
                cargado_por=user_id,
            )

        # Vaciar solo materia A
        await padron_service.vaciar_materia(materia_a)

        # Materia B debe seguir teniendo padron activo
        activo_b = await padron_service.obtener_activo(materia_b, cohorte_id)
        assert activo_b is not None
        assert activo_b.activa is True


class TestPadronMultiTenant:
    """Aislamiento multi-tenant."""

    async def test_tenant_distinto_no_ve_entradas(
        self, db_session: AsyncSession
    ):
        """F5a: Tenant B no ve entradas del Tenant A."""
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        await _seed_tenant(db_session, _OTHER_TENANT_ID)

        materia_a = await _seed_materia(db_session, _DEV_TENANT_ID)
        cohorte_a = await _seed_cohorte(db_session, _DEV_TENANT_ID)
        materia_b = await _seed_materia(db_session, _OTHER_TENANT_ID, uuid4())
        cohorte_b = await _seed_cohorte(db_session, _OTHER_TENANT_ID, uuid4())

        user_id = uuid4()
        data = _make_xlsx_bytes([("Juan", "Perez", "juan@test.com", "A", "CABA")])

        # Importar en tenant A
        svc_a = PadronService(session=db_session, tenant_id=_DEV_TENANT_ID)
        preview_a = await svc_a.preview_importacion(data, "alumnos.xlsx")
        await svc_a.confirmar_importacion(
            preview_token=preview_a["preview_token"],
            materia_id=materia_a,
            cohorte_id=cohorte_a,
            cargado_por=user_id,
        )

        # Tenant B no deberia ver el padron de A
        activo_b = await PadronService(
            session=db_session, tenant_id=_OTHER_TENANT_ID
        ).obtener_activo(materia_a, cohorte_a)
        assert activo_b is None


class TestMatchingEmail:
    """Matching de entradas por email."""

    async def test_matching_email_vincula_usuario(
        self, db_session: AsyncSession, padron_service: PadronService
    ):
        """F2a: Entrada con email coincidente se vincula al usuario."""
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        materia_id = await _seed_materia(db_session, _DEV_TENANT_ID)
        cohorte_id = await _seed_cohorte(db_session, _DEV_TENANT_ID)
        user_id = await _seed_usuario(db_session, _DEV_TENANT_ID, "juan@test.com")

        data = _make_xlsx_bytes([
            ("Juan", "Perez", "juan@test.com", "A", "CABA"),
            ("Sin", "Cuenta", "sin@cuenta.com", "B", "GBA"),
        ])
        preview = await padron_service.preview_importacion(data, "alumnos.xlsx")
        version = await padron_service.confirmar_importacion(
            preview_token=preview["preview_token"],
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            cargado_por=uuid4(),
        )

        # Verificar vinculacion
        entradas = await db_session.execute(
            text(
                "SELECT nombre, email, usuario_id FROM entrada_padron "
                "WHERE version_id = :v"
            ),
            {"v": version.id},
        )
        rows = entradas.fetchall()

        juan = next(r for r in rows if r.email == "juan@test.com")
        assert juan.usuario_id is not None

        sin = next(r for r in rows if r.email == "sin@cuenta.com")
        assert sin.usuario_id is None
