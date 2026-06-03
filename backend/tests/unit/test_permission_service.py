"""Unit tests for PermissionService — TDD cycle.

Tests use mocked repositories to verify permission resolution logic.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.services.permission_service import PermissionService


@pytest.fixture
def tenant_id() -> UUID:
    return uuid4()


@pytest.fixture
def mock_rol_repo():
    return AsyncMock()


@pytest.fixture
def mock_permiso_repo():
    return AsyncMock()


@pytest.fixture
def mock_rol_permiso_repo():
    return AsyncMock()


@pytest.fixture
def service(tenant_id, mock_rol_repo, mock_permiso_repo, mock_rol_permiso_repo):
    svc = PermissionService.__new__(PermissionService)
    svc.rol_repo = mock_rol_repo
    svc.permiso_repo = mock_permiso_repo
    svc.rol_permiso_repo = mock_rol_permiso_repo
    svc.tenant_id = tenant_id
    return svc


class TestGetEffectivePermissions:
    """get_effective_permissions resolves permissions from role codes."""

    async def test_single_role_resolves_its_permissions(
        self, service, mock_rol_repo, mock_rol_permiso_repo
    ):
        mock_rol_repo.get_by_codigos.return_value = [
            AsyncMock(id=uuid4())
        ]
        mock_rol_permiso_repo.get_codigos_by_roles.return_value = [
            "calificaciones:importar",
            "atrasados:ver",
            "comunicacion:enviar",
        ]
        result = await service.get_effective_permissions(["PROFESOR"])
        assert result == {
            "calificaciones:importar",
            "atrasados:ver",
            "comunicacion:enviar",
        }

    async def test_multiple_roles_union(
        self, service, mock_rol_repo, mock_rol_permiso_repo
    ):
        rol_a = AsyncMock(id=uuid4())
        rol_b = AsyncMock(id=uuid4())
        mock_rol_repo.get_by_codigos.return_value = [rol_a, rol_b]
        mock_rol_permiso_repo.get_codigos_by_roles.return_value = [
            "comunicacion:enviar",
            "atrasados:ver",
            "auditoria:ver",
        ]
        result = await service.get_effective_permissions(
            ["PROFESOR", "COORDINADOR"]
        )
        assert result == {
            "comunicacion:enviar",
            "atrasados:ver",
            "auditoria:ver",
        }

    async def test_role_with_no_permissions_returns_empty(
        self, service, mock_rol_repo, mock_rol_permiso_repo
    ):
        mock_rol_repo.get_by_codigos.return_value = [AsyncMock(id=uuid4())]
        mock_rol_permiso_repo.get_codigos_by_roles.return_value = []
        result = await service.get_effective_permissions(["CUSTOM"])
        assert result == set()

    async def test_empty_roles_list_returns_empty(
        self, service
    ):
        result = await service.get_effective_permissions([])
        assert result == set()

    async def test_invalid_role_codes_return_empty(
        self, service, mock_rol_repo
    ):
        mock_rol_repo.get_by_codigos.return_value = []
        result = await service.get_effective_permissions(
            ["NONEXISTENT_ROLE"]
        )
        assert result == set()


class TestHasPermission:
    """has_permission checks if a specific permission is present."""

    async def test_has_permission_returns_true_when_present(
        self, service, mock_rol_repo, mock_rol_permiso_repo
    ):
        mock_rol_repo.get_by_codigos.return_value = [AsyncMock(id=uuid4())]
        mock_rol_permiso_repo.get_codigos_by_roles.return_value = [
            "calificaciones:importar",
        ]
        result = await service.has_permission(
            ["PROFESOR"], "calificaciones:importar"
        )
        assert result is True

    async def test_has_permission_returns_false_when_missing(
        self, service, mock_rol_repo, mock_rol_permiso_repo
    ):
        mock_rol_repo.get_by_codigos.return_value = [AsyncMock(id=uuid4())]
        mock_rol_permiso_repo.get_codigos_by_roles.return_value = [
            "comunicacion:enviar",
        ]
        result = await service.has_permission(
            ["PROFESOR"], "comunicacion:aprobar"
        )
        assert result is False

    async def test_has_permission_with_empty_roles_returns_false(
        self, service
    ):
        result = await service.has_permission(
            [], "calificaciones:importar"
        )
        assert result is False
