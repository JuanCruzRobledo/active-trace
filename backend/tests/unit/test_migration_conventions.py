"""Tests estáticos de convenciones de migraciones Alembic.

No requieren base de datos — solo verifican nombres de archivo y estructura.
"""

from app.core.migration_conventions import validate_naming_convention


class TestMigrationConventions:
    """Suite de tests estáticos para migraciones Alembic."""

    def test_migration_files_follow_naming_convention(self) -> None:
        """Todas las migraciones deben seguir el naming NNN_descripcion.py."""
        errors = validate_naming_convention()
        assert not errors, (
            "Violaciones a la convención de migraciones:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    def test_migration_001_exists(self) -> None:
        """Debe existir al menos la migración 001."""
        from app.core.migration_conventions import get_migration_files  # noqa

        files = get_migration_files()
        assert any(f.name.startswith("001_") for f in files), (
            "No se encontró la migración 001. ¿Ya fue creada?"
        )
