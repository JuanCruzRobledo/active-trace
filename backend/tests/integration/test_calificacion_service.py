"""Tests de integración para CalificacionService (C-10).

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessError
from app.models.tenant import Tenant
from app.services.calificacion_service import CalificacionService
from tests.conftest import db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]


def _make_xlsx_bytes(
    headers: list[str], filas: list[tuple[str, ...]]
) -> bytes:
    try:
        import openpyxl  # noqa: PLC0415
    except ImportError:
        pytest.skip("openpyxl no instalado")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Calificaciones"
    ws.append(headers)
    for row in filas:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


def _make_csv_bytes(
    headers: list[str], filas: list[tuple[str, ...]]
) -> bytes:
    import csv

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in filas:
        writer.writerow(list(row))
    return buf.getvalue().encode("utf-8-sig")


# ── Fixtures de dominio ──────────────────────────────────────────────


@pytest_asyncio.fixture
async def tenant(db_session: AsyncSession) -> Tenant:
    tid = uuid.uuid4()
    t = Tenant(id=tid, tenant_id=tid, nombre="CalifSvcTest")
    db_session.add(t)
    await db_session.flush()
    return t


@pytest_asyncio.fixture
async def materia(tenant: Tenant, db_session: AsyncSession) -> object:
    from app.models.materia import Materia

    m = Materia(
        tenant_id=tenant.id, codigo="MAT-CALSVC-1", nombre="Matematicas"
    )
    db_session.add(m)
    await db_session.flush()
    return m


@pytest_asyncio.fixture
async def usuario(tenant: Tenant, db_session: AsyncSession) -> object:
    from app.models.usuario import Usuario

    u = Usuario(
        tenant_id=tenant.id,
        nombre="Juan",
        apellidos="Docente",
        email="juan.docente@test.com",
        dni="11111111",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture
async def carrera(tenant: Tenant, db_session: AsyncSession) -> object:
    from app.models.carrera import Carrera

    c = Carrera(
        tenant_id=tenant.id,
        codigo="ING-CALSVC",
        nombre="Ingenieria",
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
        nombre="Ana",
        apellidos="Perez",
        email="ana.perez@test.com",
    )
    db_session.add(ep)
    await db_session.flush()
    return ep


@pytest_asyncio.fixture
async def entrada_padron_2(
    tenant: Tenant,
    version_padron: object,
    db_session: AsyncSession,
) -> object:
    from app.models.entrada_padron import EntradaPadron

    ep = EntradaPadron(
        tenant_id=tenant.id,
        version_id=version_padron.id,
        nombre="Luis",
        apellidos="Garcia",
        email="luis.garcia@test.com",
    )
    db_session.add(ep)
    await db_session.flush()
    return ep


@pytest_asyncio.fixture
async def service(
    tenant: Tenant, db_session: AsyncSession
) -> CalificacionService:
    return CalificacionService(session=db_session, tenant_id=tenant.id)


# ═══════════════════════════════════════════════════════════════════════
# Tests: importar_preview
# ═══════════════════════════════════════════════════════════════════════


class TestCalificacionPreview:
    """Preview de archivos de calificaciones."""

    async def test_preview_xlsx_valido(
        self,
        materia: object,
        service: CalificacionService,
    ):
        """Preview de xlsx con columnas numericas y textuales."""
        data = _make_xlsx_bytes(
            headers=[
                "Nombre",
                "Apellido",
                "Parcial 1 (Real)",
                "TP 1 (Real)",
                "TP Laboratorio",
            ],
            filas=[
                ("Ana", "Perez", "85", "90", "Satisfactorio"),
                ("Luis", "Garcia", "60", "75", "Aprobado"),
            ],
        )
        result = await service.importar_preview(
            data, "calificaciones.xlsx", materia.id
        )

        assert "preview_token" in result
        assert len(result["preview_token"]) == 64
        assert result["filas"] == 2
        assert result["alumnos_detectados"] == 2
        assert "Parcial 1 (Real)" in result["actividades_detectadas"]
        assert "TP 1 (Real)" in result["actividades_detectadas"]
        # Nota: TP Laboratorio no termina en (Real), se detecta como textual
        # segun los valores de la muestra

    async def test_preview_csv_valido(
        self,
        materia: object,
        service: CalificacionService,
    ):
        """Preview de csv con datos correctos."""
        data = _make_csv_bytes(
            headers=["Nombre", "Apellido", "Parcial (Real)", "TP (Real)"],
            filas=[
                ("Ana", "Perez", "85", "90"),
            ],
        )
        result = await service.importar_preview(
            data, "calificaciones.csv", materia.id
        )

        assert "preview_token" in result
        assert result["filas"] == 1
        assert len(result["actividades_detectadas"]) == 2

    async def test_preview_formato_invalido(
        self,
        materia: object,
        service: CalificacionService,
    ):
        """Formato invalido → BusinessError."""
        with pytest.raises(BusinessError, match="(?i)formato"):
            await service.importar_preview(
                b"datos", "calificaciones.pdf", materia.id
            )

    async def test_preview_archivo_vacio(
        self,
        materia: object,
        service: CalificacionService,
    ):
        """Archivo sin datos → BusinessError."""
        data = _make_xlsx_bytes(
            headers=["Nombre", "Parcial (Real)"],
            filas=[],
        )
        with pytest.raises(BusinessError, match="no contiene datos"):
            await service.importar_preview(
                data, "vacio.xlsx", materia.id
            )


# ═══════════════════════════════════════════════════════════════════════
# Tests: importar_confirm
# ═══════════════════════════════════════════════════════════════════════


class TestCalificacionConfirm:
    """Confirm de importacion de calificaciones."""

    async def test_confirm_crea_calificaciones(
        self,
        db_session: AsyncSession,
        materia: object,
        entrada_padron: object,
        service: CalificacionService,
    ):
        """Confirm con token valido crea calificaciones."""
        data = _make_xlsx_bytes(
            headers=["Nombre", "Apellido", "Parcial (Real)", "TP (Real)"],
            filas=[
                ("Ana", "Perez", "85", "90"),
            ],
        )
        preview = await service.importar_preview(
            data, "calificaciones.xlsx", materia.id
        )
        preview_token = preview["preview_token"]

        result = await service.importar_confirm(
            preview_token=preview_token,
            materia_id=materia.id,
            actividades_seleccionadas=["Parcial (Real)", "TP (Real)"],
            usuario_id=uuid.uuid4(),
        )

        assert result["calificaciones_importadas"] == 2
        assert len(result["actividades"]) == 2

    async def test_confirm_token_invalido(
        self,
        materia: object,
        service: CalificacionService,
    ):
        """Preview token invalido → BusinessError."""
        with pytest.raises(BusinessError, match="token"):
            await service.importar_confirm(
                preview_token="token-invalido",
                materia_id=materia.id,
                actividades_seleccionadas=[],
                usuario_id=uuid.uuid4(),
            )

    async def test_confirm_solo_actividades_seleccionadas(
        self,
        db_session: AsyncSession,
        materia: object,
        entrada_padron: object,
        service: CalificacionService,
    ):
        """Solo se importan las actividades seleccionadas."""
        data = _make_xlsx_bytes(
            headers=[
                "Nombre",
                "Apellido",
                "Parcial (Real)",
                "TP (Real)",
                "Final (Real)",
            ],
            filas=[
                ("Ana", "Perez", "85", "90", "70"),
            ],
        )
        preview = await service.importar_preview(
            data, "calificaciones.xlsx", materia.id
        )

        result = await service.importar_confirm(
            preview_token=preview["preview_token"],
            materia_id=materia.id,
            actividades_seleccionadas=["Parcial (Real)"],
            usuario_id=uuid.uuid4(),
        )

        assert result["calificaciones_importadas"] == 1
        assert result["actividades"][0]["nombre"] == "Parcial (Real)"

    async def test_confirm_materia_distinta(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        entrada_padron: object,
        service: CalificacionService,
    ):
        """Preview de otra materia → BusinessError."""
        from app.models.materia import Materia

        otra = Materia(
            tenant_id=tenant.id,
            codigo="MAT-OTRA",
            nombre="Otra Materia",
        )
        db_session.add(otra)
        await db_session.flush()

        data = _make_xlsx_bytes(
            headers=["Nombre", "Apellido", "Parcial (Real)"],
            filas=[("Ana", "Perez", "85")],
        )
        preview = await service.importar_preview(
            data, "calificaciones.xlsx", materia.id
        )

        with pytest.raises(BusinessError, match="no corresponde"):
            await service.importar_confirm(
                preview_token=preview["preview_token"],
                materia_id=otra.id,
                actividades_seleccionadas=["Parcial (Real)"],
                usuario_id=uuid.uuid4(),
            )


# ═══════════════════════════════════════════════════════════════════════
# Tests: procesar_finalizacion
# ═══════════════════════════════════════════════════════════════════════


class TestCalificacionFinalizacion:
    """Procesamiento de archivos de finalizacion."""

    async def test_detecta_entregas_sin_calificar(
        self,
        materia: object,
        service: CalificacionService,
    ):
        """Actividad textual con entrega y sin calificacion → posible sin
        corregir."""
        data = _make_xlsx_bytes(
            headers=["Nombre", "Apellido", "TP Laboratorio"],
            filas=[
                ("Ana", "Perez", "Satisfactorio"),
                ("Luis", "Garcia", "Aprobado"),
            ],
        )
        result = await service.procesar_finalizacion(
            data, "finalizacion.xlsx", materia.id
        )

        assert len(result["posibles_sin_corregir"]) == 2
        assert result["posibles_sin_corregir"][0]["actividad"] == "TP Laboratorio"

    async def test_actividad_ya_calificada_no_aparece(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        materia: object,
        entrada_padron: object,
        service: CalificacionService,
    ):
        """Actividad textual ya calificada → no aparece como sin corregir."""
        from app.models.calificacion import Calificacion
        from app.models.enums import OrigenCalificacion

        cal = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entrada_padron.id,
            materia_id=materia.id,
            actividad="TP Laboratorio",
            nota_textual="Satisfactorio",
            origen=OrigenCalificacion.IMPORTADO,
        )
        db_session.add(cal)
        await db_session.flush()

        data = _make_xlsx_bytes(
            headers=["Nombre", "Apellido", "TP Laboratorio"],
            filas=[
                ("Ana", "Perez", "Satisfactorio"),
            ],
        )
        result = await service.procesar_finalizacion(
            data, "finalizacion.xlsx", materia.id
        )

        assert len(result["posibles_sin_corregir"]) == 0
