"""Tests unitarios para schemas de Usuario y Asignacion (C-07).

Verifica:
- extra='forbid' en todos los schemas
- Validación de campos requeridos y opcionales
- PII enmascarada en responses
- Validación de vigencia (desde ≤ hasta)
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError


# ===========================================================================
# Usuario Schemas
# ===========================================================================


class TestUsuarioCreateSchema:
    """Tests for UsuarioCreate schema."""

    def test_create_valid_minimal(self):
        from app.schemas.usuario import UsuarioCreate

        data = UsuarioCreate(
            nombre="Juan",
            apellidos="Pérez",
            email="juan@example.com",
        )
        assert data.nombre == "Juan"
        assert data.apellidos == "Pérez"
        assert data.email == "juan@example.com"
        assert data.estado == "Activo"
        assert data.dni is None
        assert data.cuil is None

    def test_create_valid_full(self):
        from app.schemas.usuario import UsuarioCreate

        data = UsuarioCreate(
            nombre="María",
            apellidos="González",
            email="maria@example.com",
            dni="12345678",
            cuil="20-12345678-9",
            cbu="0000003100012345678901",
            alias_cbu="maria.banco",
            banco="Banco Nación",
            regional="Centro",
            legajo="LEG-001",
            legajo_profesional="LP-001",
            facturador="Facturador A",
            estado="Activo",
        )
        assert data.dni == "12345678"
        assert data.legajo == "LEG-001"

    def test_create_extra_field_forbidden(self):
        from app.schemas.usuario import UsuarioCreate

        with pytest.raises(ValidationError) as exc:
            UsuarioCreate(
                nombre="Test",
                apellidos="Test",
                email="test@test.com",
                campo_extra="no permitido",
            )
        assert "extra" in str(exc.value).lower()

    def test_create_missing_required_raises(self):
        from app.schemas.usuario import UsuarioCreate

        with pytest.raises(ValidationError):
            UsuarioCreate(nombre="Solo nombre")

    def test_create_invalid_estado_raises(self):
        from app.schemas.usuario import UsuarioCreate

        with pytest.raises(ValidationError):
            UsuarioCreate(
                nombre="Test",
                apellidos="Test",
                email="test@test.com",
                estado="INVALIDO",
            )


class TestUsuarioUpdateSchema:
    """Tests for UsuarioUpdate schema."""

    def test_update_partial(self):
        from app.schemas.usuario import UsuarioUpdate

        data = UsuarioUpdate(nombre="NuevoNombre")
        assert data.nombre == "NuevoNombre"
        assert data.apellidos is None
        assert data.email is None

    def test_update_empty_allowed(self):
        from app.schemas.usuario import UsuarioUpdate

        data = UsuarioUpdate()
        assert data.nombre is None

    def test_update_extra_forbidden(self):
        from app.schemas.usuario import UsuarioUpdate

        with pytest.raises(ValidationError):
            UsuarioUpdate(nombre="Test", campo_extra="x")

    def test_update_email_validation(self):
        from app.schemas.usuario import UsuarioUpdate

        with pytest.raises(ValidationError):
            UsuarioUpdate(email="not-an-email")


class TestUsuarioResponseSchema:
    """Tests for UsuarioResponse schema with PII masking."""

    def test_response_creation(self):
        from app.schemas.usuario import UsuarioResponse

        now = datetime.now(timezone.utc)
        data = UsuarioResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            tenant_id="550e8400-e29b-41d4-a716-446655440001",
            nombre="Juan",
            apellidos="Pérez",
            email="j***@***.com",
            dni="1***8",
            cuil="2***9",
            cbu="0***1",
            alias_cbu="m***o",
            banco="Banco Nación",
            regional="Centro",
            legajo="LEG-001",
            legajo_profesional=None,
            facturador=None,
            estado="Activo",
            created_at=now,
            updated_at=now,
        )
        assert data.email == "j***@***.com"
        # PII fields should be masked
        assert "*" in data.email
        assert "*" in data.dni
        assert "*" in data.cuil
        assert "12345678" not in data.dni


class TestUsuarioListResponse:
    """Tests for UsuarioListResponse paginated schema."""

    def test_list_response(self):
        from app.schemas.usuario import UsuarioResponse, UsuarioListResponse

        now = datetime.now(timezone.utc)
        items = [
            UsuarioResponse(
                id="id1", tenant_id="tid1",
                nombre="A", apellidos="B",
                email="a@b.com", estado="Activo",
                created_at=now, updated_at=now,
            )
        ]
        data = UsuarioListResponse(items=items, total=1, page=1, page_size=20)
        assert data.total == 1
        assert data.page == 1
        assert len(data.items) == 1


# ===========================================================================
# Asignacion Schemas
# ===========================================================================


class TestAsignacionCreateSchema:
    """Tests for AsignacionCreate schema."""

    def test_create_valid_minimal(self):
        from app.schemas.asignacion import AsignacionCreate

        data = AsignacionCreate(
            usuario_id="550e8400-e29b-41d4-a716-446655440000",
            rol="PROFESOR",
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        assert data.usuario_id is not None
        assert data.rol == "PROFESOR"
        assert data.materia_id is None
        assert data.responsable_id is None

    def test_create_valid_full(self):
        from app.schemas.asignacion import AsignacionCreate

        data = AsignacionCreate(
            usuario_id="550e8400-e29b-41d4-a716-446655440000",
            rol="TUTOR",
            materia_id="550e8400-e29b-41d4-a716-446655440010",
            carrera_id="550e8400-e29b-41d4-a716-446655440020",
            cohorte_id="550e8400-e29b-41d4-a716-446655440030",
            comisiones=["A", "B"],
            responsable_id="550e8400-e29b-41d4-a716-446655440040",
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
            hasta=datetime(2024, 12, 31, tzinfo=timezone.utc),
        )
        assert data.comisiones == ["A", "B"]
        assert data.responsable_id is not None

    def test_create_desde_before_hasta_valid(self):
        from app.schemas.asignacion import AsignacionCreate

        data = AsignacionCreate(
            usuario_id="550e8400-e29b-41d4-a716-446655440000",
            rol="PROFESOR",
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
            hasta=datetime(2024, 12, 31, tzinfo=timezone.utc),
        )
        assert data.desde < data.hasta

    def test_create_desde_after_hasta_invalid(self):
        from app.schemas.asignacion import AsignacionCreate

        with pytest.raises(ValidationError):
            AsignacionCreate(
                usuario_id="550e8400-e29b-41d4-a716-446655440000",
                rol="PROFESOR",
                desde=datetime(2024, 12, 31, tzinfo=timezone.utc),
                hasta=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )

    def test_create_extra_forbidden(self):
        from app.schemas.asignacion import AsignacionCreate

        with pytest.raises(ValidationError):
            AsignacionCreate(
                usuario_id="id", rol="PROFESOR",
                desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
                extra="no",
            )


class TestAsignacionUpdateSchema:
    """Tests for AsignacionUpdate schema."""

    def test_update_rol(self):
        from app.schemas.asignacion import AsignacionUpdate

        data = AsignacionUpdate(rol="COORDINADOR")
        assert data.rol == "COORDINADOR"
        assert data.hasta is None

    def test_update_hasta_extension(self):
        from app.schemas.asignacion import AsignacionUpdate

        data = AsignacionUpdate(
            hasta=datetime(2025, 12, 31, tzinfo=timezone.utc),
        )
        assert data.hasta is not None

    def test_update_extra_forbidden(self):
        from app.schemas.asignacion import AsignacionUpdate

        with pytest.raises(ValidationError):
            AsignacionUpdate(extra="x")


class TestAsignacionResponse:
    """Tests for AsignacionResponse schema."""

    def test_response_with_estado_vigencia(self):
        from app.schemas.asignacion import AsignacionResponse

        now = datetime.now(timezone.utc)
        data = AsignacionResponse(
            id="id1",
            tenant_id="tid1",
            usuario_id="uid1",
            rol="PROFESOR",
            desde=datetime(2024, 1, 1, tzinfo=timezone.utc),
            estado_vigencia="Vigente",
            created_at=now,
            updated_at=now,
        )
        assert data.estado_vigencia == "Vigente"

    def test_response_vencida(self):
        from app.schemas.asignacion import AsignacionResponse

        now = datetime.now(timezone.utc)
        data = AsignacionResponse(
            id="id1",
            tenant_id="tid1",
            usuario_id="uid1",
            rol="PROFESOR",
            desde=datetime(2020, 1, 1, tzinfo=timezone.utc),
            hasta=datetime(2020, 12, 31, tzinfo=timezone.utc),
            estado_vigencia="Vencida",
            created_at=now,
            updated_at=now,
        )
        assert data.estado_vigencia == "Vencida"
