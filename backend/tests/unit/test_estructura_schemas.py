"""Tests para los DTOs de estructura académica (C-06).

Cubren:
- ``extra='forbid'`` rechaza campos no declarados (regla dura #5).
- Validaciones de campo: min_length, max_length, pattern, ge/le.
- ``CohorteCreate`` valida que ``vig_hasta > vig_desde``.
"""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError


# ===========================================================================
# extra='forbid' (regla dura #5)
# ===========================================================================


class TestCarreraSchemasExtraForbid:
    """Schemas de Carrera rechazan campos extra."""

    def test_carrera_create_rejects_unknown(self):
        from app.schemas.carrera import CarreraCreate

        with pytest.raises(ValidationError) as exc:
            CarreraCreate(codigo="LIC", nombre="Licenciatura", extra="x")  # type: ignore[call-arg]
        assert "extra" in str(exc.value).lower()

    def test_carrera_update_rejects_unknown(self):
        from app.schemas.carrera import CarreraUpdate

        with pytest.raises(ValidationError) as exc:
            CarreraUpdate(nombre="Nuevo", hacker=True)  # type: ignore[call-arg]
        assert "hacker" in str(exc.value).lower()

    def test_carrera_response_rejects_unknown(self):
        from app.schemas.carrera import CarreraResponse

        with pytest.raises(ValidationError) as exc:
            CarreraResponse(
                id="x", tenant_id="x", codigo="L", nombre="N",
                estado="Activa", created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00", secret="leak",
            )  # type: ignore[call-arg]
        assert "secret" in str(exc.value).lower()


class TestMateriaSchemasExtraForbid:
    """Schemas de Materia rechazan campos extra."""

    def test_materia_create_rejects_unknown(self):
        from app.schemas.materia import MateriaCreate

        with pytest.raises(ValidationError) as exc:
            MateriaCreate(codigo="M01", nombre="Matematicas", injected="x")  # type: ignore[call-arg]
        assert "injected" in str(exc.value).lower()

    def test_materia_update_rejects_unknown(self):
        from app.schemas.materia import MateriaUpdate

        with pytest.raises(ValidationError) as exc:
            MateriaUpdate(estado="Inactiva", backdoor="x")  # type: ignore[call-arg]
        assert "backdoor" in str(exc.value).lower()

    def test_materia_response_rejects_unknown(self):
        from app.schemas.materia import MateriaResponse

        with pytest.raises(ValidationError) as exc:
            MateriaResponse(
                id="x", tenant_id="x", codigo="M", nombre="N",
                estado="Activa", created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00", password_hash="x",
            )  # type: ignore[call-arg]
        assert "password_hash" in str(exc.value).lower()


class TestCohorteSchemasExtraForbid:
    """Schemas de Cohorte rechazan campos extra."""

    def test_cohorte_create_rejects_unknown(self):
        from app.schemas.cohorte import CohorteCreate

        with pytest.raises(ValidationError) as exc:
            CohorteCreate(
                carrera_id="a" * 36, nombre="2024A", anio=2024,
                vig_desde=date(2024, 3, 1), admin=True,
            )  # type: ignore[call-arg]
        assert "admin" in str(exc.value).lower()

    def test_cohorte_update_rejects_unknown(self):
        from app.schemas.cohorte import CohorteUpdate

        with pytest.raises(ValidationError) as exc:
            CohorteUpdate(estado="Inactiva", debug=True)  # type: ignore[call-arg]
        assert "debug" in str(exc.value).lower()

    def test_cohorte_response_rejects_unknown(self):
        from app.schemas.cohorte import CohorteResponse

        with pytest.raises(ValidationError) as exc:
            CohorteResponse(
                id="x", tenant_id="x", carrera_id="x", nombre="N",
                anio=2024, vig_desde=date(2024, 1, 1), estado="Activa",
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00", ghost="x",
            )  # type: ignore[call-arg]
        assert "ghost" in str(exc.value).lower()


# ===========================================================================
# CarreraCreate / CarreraUpdate
# ===========================================================================


class TestCarreraCreate:
    """``CarreraCreate`` requiere codigo, nombre; estado opcional con valores válidos."""

    def test_valid_carrera_create(self):
        from app.schemas.carrera import CarreraCreate

        c = CarreraCreate(codigo="LIC", nombre="Licenciatura en Sistemas")
        assert c.codigo == "LIC"
        assert c.nombre == "Licenciatura en Sistemas"
        assert c.estado == "Activa"

    def test_accepts_custom_estado(self):
        from app.schemas.carrera import CarreraCreate

        c = CarreraCreate(codigo="LIC", nombre="Lic.", estado="Inactiva")
        assert c.estado == "Inactiva"

    def test_rejects_empty_codigo(self):
        from app.schemas.carrera import CarreraCreate

        with pytest.raises(ValidationError):
            CarreraCreate(codigo="", nombre="Licenciatura")

    def test_rejects_long_codigo(self):
        from app.schemas.carrera import CarreraCreate

        with pytest.raises(ValidationError):
            CarreraCreate(codigo="A" * 51, nombre="X")

    def test_rejects_invalid_estado(self):
        from app.schemas.carrera import CarreraCreate

        with pytest.raises(ValidationError):
            CarreraCreate(codigo="LIC", nombre="Lic.", estado="Suspendida")

    def test_rejects_missing_codigo(self):
        from app.schemas.carrera import CarreraCreate

        with pytest.raises(ValidationError):
            CarreraCreate(nombre="Licenciatura")  # type: ignore[call-arg]

    def test_rejects_missing_nombre(self):
        from app.schemas.carrera import CarreraCreate

        with pytest.raises(ValidationError):
            CarreraCreate(codigo="LIC")  # type: ignore[call-arg]


class TestCarreraUpdate:
    """``CarreraUpdate`` permite actualización parcial."""

    def test_empty_update_is_valid(self):
        """Update con todos los campos opcionales: pasar {} es válido."""
        from app.schemas.carrera import CarreraUpdate

        u = CarreraUpdate()
        assert u.nombre is None
        assert u.estado is None

    def test_update_nombre(self):
        from app.schemas.carrera import CarreraUpdate

        u = CarreraUpdate(nombre="Nuevo nombre")
        assert u.nombre == "Nuevo nombre"

    def test_update_estado(self):
        from app.schemas.carrera import CarreraUpdate

        u = CarreraUpdate(estado="Inactiva")
        assert u.estado == "Inactiva"

    def test_rejects_long_nombre(self):
        from app.schemas.carrera import CarreraUpdate

        with pytest.raises(ValidationError):
            CarreraUpdate(nombre="A" * 201)

    def test_rejects_invalid_estado(self):
        from app.schemas.carrera import CarreraUpdate

        with pytest.raises(ValidationError):
            CarreraUpdate(estado="Cancelada")


# ===========================================================================
# MateriaCreate / MateriaUpdate
# ===========================================================================


class TestMateriaCreate:
    """``MateriaCreate`` mismas reglas que CarreraCreate."""

    def test_valid_materia_create(self):
        from app.schemas.materia import MateriaCreate

        m = MateriaCreate(codigo="M01", nombre="Matematicas I")
        assert m.codigo == "M01"
        assert m.nombre == "Matematicas I"
        assert m.estado == "Activa"

    def test_rejects_empty_codigo(self):
        from app.schemas.materia import MateriaCreate

        with pytest.raises(ValidationError):
            MateriaCreate(codigo="", nombre="X")

    def test_rejects_long_nombre(self):
        from app.schemas.materia import MateriaCreate

        with pytest.raises(ValidationError):
            MateriaCreate(codigo="M01", nombre="A" * 201)


class TestMateriaUpdate:
    """``MateriaUpdate`` actualización parcial."""

    def test_empty_update(self):
        from app.schemas.materia import MateriaUpdate

        u = MateriaUpdate()
        assert u.nombre is None
        assert u.estado is None

    def test_update_estado(self):
        from app.schemas.materia import MateriaUpdate

        u = MateriaUpdate(estado="Inactiva")
        assert u.estado == "Inactiva"


# ===========================================================================
# CohorteCreate / CohorteUpdate
# ===========================================================================


class TestCohorteCreate:
    """``CohorteCreate`` con validaciones específicas (vig_hasta > vig_desde)."""

    def test_valid_cohorte_create(self):
        from app.schemas.cohorte import CohorteCreate

        c = CohorteCreate(
            carrera_id="a" * 36, nombre="2024A", anio=2024,
            vig_desde=date(2024, 3, 1),
        )
        assert c.carrera_id == "a" * 36
        assert c.nombre == "2024A"
        assert c.anio == 2024
        assert c.vig_desde == date(2024, 3, 1)
        assert c.vig_hasta is None
        assert c.estado == "Activa"

    def test_valid_with_vig_hasta(self):
        from app.schemas.cohorte import CohorteCreate

        c = CohorteCreate(
            carrera_id="b" * 36, nombre="2024B", anio=2024,
            vig_desde=date(2024, 3, 1),
            vig_hasta=date(2025, 2, 28),
        )
        assert c.vig_hasta == date(2025, 2, 28)

    def test_rejects_vig_hasta_before_vig_desde(self):
        """vig_hasta debe ser posterior a vig_desde."""
        from app.schemas.cohorte import CohorteCreate

        with pytest.raises(ValidationError) as exc:
            CohorteCreate(
                carrera_id="a" * 36, nombre="2024A", anio=2024,
                vig_desde=date(2024, 3, 1),
                vig_hasta=date(2024, 2, 1),
            )
        msg = str(exc.value).lower()
        assert "vig_hasta" in msg

    def test_rejects_vig_hasta_equal_to_vig_desde(self):
        """vig_hasta == vig_desde también es inválido."""
        from app.schemas.cohorte import CohorteCreate

        with pytest.raises(ValidationError):
            CohorteCreate(
                carrera_id="a" * 36, nombre="2024A", anio=2024,
                vig_desde=date(2024, 3, 1),
                vig_hasta=date(2024, 3, 1),
            )

    def test_rejects_invalid_carrera_id_length(self):
        """carrera_id debe ser UUID (36 chars)."""
        from app.schemas.cohorte import CohorteCreate

        with pytest.raises(ValidationError):
            CohorteCreate(
                carrera_id="short", nombre="2024A", anio=2024,
                vig_desde=date(2024, 3, 1),
            )

    def test_rejects_anio_less_than_1900(self):
        from app.schemas.cohorte import CohorteCreate

        with pytest.raises(ValidationError):
            CohorteCreate(
                carrera_id="a" * 36, nombre="2024A", anio=1800,
                vig_desde=date(2024, 3, 1),
            )

    def test_rejects_anio_greater_than_2150(self):
        from app.schemas.cohorte import CohorteCreate

        with pytest.raises(ValidationError):
            CohorteCreate(
                carrera_id="a" * 36, nombre="2024A", anio=2200,
                vig_desde=date(2024, 3, 1),
            )


class TestCohorteUpdate:
    """``CohorteUpdate`` actualización parcial."""

    def test_empty_update(self):
        from app.schemas.cohorte import CohorteUpdate

        u = CohorteUpdate()
        assert u.nombre is None
        assert u.vig_desde is None
        assert u.vig_hasta is None
        assert u.estado is None

    def test_update_nombre(self):
        from app.schemas.cohorte import CohorteUpdate

        u = CohorteUpdate(nombre="2025A")
        assert u.nombre == "2025A"


# ===========================================================================
# Response schemas — shape checks
# ===========================================================================


class TestCarreraResponse:
    def test_minimal_response(self):
        from app.schemas.carrera import CarreraResponse

        r = CarreraResponse(
            id="uuid-1", tenant_id="uuid-t",
            codigo="LIC", nombre="Lic.", estado="Activa",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        assert r.id == "uuid-1"
        assert r.codigo == "LIC"
        assert r.nombre == "Lic."


class TestMateriaResponse:
    def test_minimal_response(self):
        from app.schemas.materia import MateriaResponse

        r = MateriaResponse(
            id="uuid-1", tenant_id="uuid-t",
            codigo="M01", nombre="Mat.", estado="Activa",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        assert r.id == "uuid-1"
        assert r.codigo == "M01"


class TestCohorteResponse:
    def test_minimal_response(self):
        from app.schemas.cohorte import CohorteResponse

        r = CohorteResponse(
            id="uuid-1", tenant_id="uuid-t", carrera_id="uuid-c",
            nombre="2024A", anio=2024,
            vig_desde=date(2024, 3, 1), estado="Activa",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        assert r.id == "uuid-1"
        assert r.nombre == "2024A"
        assert r.anio == 2024


# ===========================================================================
# Triangulación
# ===========================================================================


class TestEstructuraSchemasTriangulate:
    """Todos los schemas de estructura tienen extra='forbid'."""

    def test_all_create_schemas_have_extra_forbid(self):
        from app.schemas import carrera, materia, cohorte

        schemas = [
            carrera.CarreraCreate,
            carrera.CarreraUpdate,
            carrera.CarreraResponse,
            materia.MateriaCreate,
            materia.MateriaUpdate,
            materia.MateriaResponse,
            cohorte.CohorteCreate,
            cohorte.CohorteUpdate,
            cohorte.CohorteResponse,
        ]
        for schema in schemas:
            assert (
                schema.model_config.get("extra") == "forbid"
            ), f"{schema.__name__} SHOULD forbid extra fields"
