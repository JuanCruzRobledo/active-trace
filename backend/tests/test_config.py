"""Tests for core configuration (Settings)."""

import os
import pytest
from pydantic import ValidationError


@pytest.fixture(autouse=True)
def clear_env() -> None:
    """Clear activia-trace env vars before each test and restore after."""
    saved = {}
    keys = [
        "DATABASE_URL",
        "DATABASE_URL_TEST",
        "SECRET_KEY",
        "ENCRYPTION_KEY",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "REFRESH_TOKEN_EXPIRE_DAYS",
        "PASSWORD_RESET_EXPIRE_MINUTES",
        "TWO_FA_CHALLENGE_EXPIRE_MINUTES",
        "TOTP_ISSUER",
        "LOGIN_RATE_LIMIT",
        "MAILER_MODE",
        "ENVIRONMENT",
        "LOG_LEVEL",
    ]
    for key in keys:
        saved[key] = os.environ.pop(key, None)
    yield
    for key in keys:
        if saved[key] is not None:
            os.environ[key] = saved[key]
        else:
            os.environ.pop(key, None)


class TestSettingsValid:
    """Scenario: Carga válida desde el entorno."""

    def test_instantiates_with_all_required_vars(self) -> None:
        """WHEN all required env vars are present and valid → Settings instantiates successfully."""
        # Arrange
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/db"
        os.environ["SECRET_KEY"] = "a" * 64
        os.environ["ENCRYPTION_KEY"] = "b" * 32
        # Act
        from app.core.config import Settings

        settings = Settings()  # type: ignore[call-arg]
        # Assert
        assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/db"
        assert settings.SECRET_KEY == "a" * 64
        assert settings.ENCRYPTION_KEY == "b" * 32
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 15  # default
        assert settings.ENVIRONMENT == "development"
        assert settings.LOG_LEVEL == "DEBUG"

    def test_access_token_expire_minutes_custom(self) -> None:
        """WHEN ACCESS_TOKEN_EXPIRE_MINUTES is set → Settings uses the custom value."""
        # Arrange
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/db"
        os.environ["SECRET_KEY"] = "a" * 64
        os.environ["ENCRYPTION_KEY"] = "b" * 32
        os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
        # Act
        from app.core.config import Settings

        settings = Settings()  # type: ignore[call-arg]
        # Assert
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30


class TestSettingsInvalid:
    """Scenario: Configuración inválida o incompleta."""

    def test_fails_when_database_url_missing(self) -> None:
        """WHEN DATABASE_URL is missing → Settings instantiation raises ValidationError."""
        # Arrange
        os.environ["SECRET_KEY"] = "a" * 64
        os.environ["ENCRYPTION_KEY"] = "b" * 32
        # Act & Assert
        from app.core.config import Settings

        with pytest.raises(ValidationError):
            Settings(_env_file=None)  # type: ignore[call-arg]

    def test_fails_when_secret_key_too_short(self) -> None:
        """WHEN SECRET_KEY is shorter than 32 chars → Settings instantiation raises ValidationError."""
        # Arrange
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/db"
        os.environ["SECRET_KEY"] = "too-short"
        os.environ["ENCRYPTION_KEY"] = "b" * 32
        # Act & Assert
        from app.core.config import Settings

        with pytest.raises(ValidationError):
            Settings()  # type: ignore[call-arg]

    def test_fails_when_encryption_key_not_32_chars(self) -> None:
        """WHEN ENCRYPTION_KEY is not exactly 32 characters → Settings instantiation raises ValidationError."""
        # Arrange
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/db"
        os.environ["SECRET_KEY"] = "a" * 64
        os.environ["ENCRYPTION_KEY"] = "wrong-length"
        # Act & Assert
        from app.core.config import Settings

        with pytest.raises(ValidationError):
            Settings()  # type: ignore[call-arg]

    def test_fails_when_access_token_expire_not_int(self) -> None:
        """WHEN ACCESS_TOKEN_EXPIRE_MINUTES is not a valid integer → ValidationError."""
        # Arrange
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/db"
        os.environ["SECRET_KEY"] = "a" * 64
        os.environ["ENCRYPTION_KEY"] = "b" * 32
        os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "not-a-number"
        # Act & Assert
        from app.core.config import Settings

        with pytest.raises(ValidationError):
            Settings()  # type: ignore[call-arg]


class TestC03Settings:
    """Settings C-03: nuevas variables de auth, 2FA, recovery y rate limit."""

    def test_refresh_token_expire_days_default(self) -> None:
        """WHEN sin env var → REFRESH_TOKEN_EXPIRE_DAYS = 7."""
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/db"
        os.environ["SECRET_KEY"] = "a" * 64
        os.environ["ENCRYPTION_KEY"] = "b" * 32
        from app.core.config import Settings

        s = Settings()  # type: ignore[call-arg]
        assert s.REFRESH_TOKEN_EXPIRE_DAYS == 7

    def test_password_reset_expire_minutes_default(self) -> None:
        """WHEN sin env var → PASSWORD_RESET_EXPIRE_MINUTES = 30."""
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/db"
        os.environ["SECRET_KEY"] = "a" * 64
        os.environ["ENCRYPTION_KEY"] = "b" * 32
        from app.core.config import Settings

        s = Settings()  # type: ignore[call-arg]
        assert s.PASSWORD_RESET_EXPIRE_MINUTES == 30

    def test_two_fa_challenge_expire_minutes_default(self) -> None:
        """WHEN sin env var → TWO_FA_CHALLENGE_EXPIRE_MINUTES = 5."""
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/db"
        os.environ["SECRET_KEY"] = "a" * 64
        os.environ["ENCRYPTION_KEY"] = "b" * 32
        from app.core.config import Settings

        s = Settings()  # type: ignore[call-arg]
        assert s.TWO_FA_CHALLENGE_EXPIRE_MINUTES == 5

    def test_totp_issuer_default(self) -> None:
        """WHEN sin env var → TOTP_ISSUER = 'activia-trace'."""
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/db"
        os.environ["SECRET_KEY"] = "a" * 64
        os.environ["ENCRYPTION_KEY"] = "b" * 32
        from app.core.config import Settings

        s = Settings()  # type: ignore[call-arg]
        assert s.TOTP_ISSUER == "activia-trace"

    def test_login_rate_limit_default(self) -> None:
        """WHEN sin env var → LOGIN_RATE_LIMIT = '5/60s'."""
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/db"
        os.environ["SECRET_KEY"] = "a" * 64
        os.environ["ENCRYPTION_KEY"] = "b" * 32
        from app.core.config import Settings

        s = Settings()  # type: ignore[call-arg]
        assert s.LOGIN_RATE_LIMIT == "5/60s"

    def test_mailer_mode_default(self) -> None:
        """WHEN sin env var → MAILER_MODE = 'console'."""
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/db"
        os.environ["SECRET_KEY"] = "a" * 64
        os.environ["ENCRYPTION_KEY"] = "b" * 32
        from app.core.config import Settings

        s = Settings()  # type: ignore[call-arg]
        assert s.MAILER_MODE == "console"

    def test_mailer_mode_rejects_invalid_value(self) -> None:
        """WHEN MAILER_MODE = 'smtp' (no soportado) → ValidationError."""
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/db"
        os.environ["SECRET_KEY"] = "a" * 64
        os.environ["ENCRYPTION_KEY"] = "b" * 32
        os.environ["MAILER_MODE"] = "smtp"
        from app.core.config import Settings

        with pytest.raises(ValidationError):
            Settings()  # type: ignore[call-arg]

    def test_refresh_token_expire_days_custom(self) -> None:
        """WHEN REFRESH_TOKEN_EXPIRE_DAYS=30 → Settings usa el valor."""
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/db"
        os.environ["SECRET_KEY"] = "a" * 64
        os.environ["ENCRYPTION_KEY"] = "b" * 32
        os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "30"
        from app.core.config import Settings

        s = Settings()  # type: ignore[call-arg]
        assert s.REFRESH_TOKEN_EXPIRE_DAYS == 30
