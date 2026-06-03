"""Tests de arranque de la aplicación FastAPI."""

from app.main import create_app
from app.core.config import Settings


def _test_settings() -> Settings:
    """Settings mínimo para test de arranque (sin DB real)."""
    return Settings(  # type: ignore[call-arg]
        DATABASE_URL="postgresql+asyncpg://localhost:5432/test",
        SECRET_KEY="a" * 64,
        ENCRYPTION_KEY="b" * 32,
    )


class TestAppStartup:
    """Scenario: La aplicación se instancia sin error."""

    def test_create_app_returns_fastapi_instance(self) -> None:
        """WHEN create_app() con settings válidos → retorna FastAPI sin error."""
        # Act
        app = create_app(_test_settings())
        # Assert
        assert app.title == "activia-trace"
        assert app.version == "0.1.0"

    def test_health_router_is_registered(self) -> None:
        """WHEN create_app() → el router de health está registrado."""
        # Act
        app = create_app(_test_settings())
        routes = [r.path for r in app.routes]
        # Assert
        assert "/health" in routes
