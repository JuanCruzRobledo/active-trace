"""Tipada de configuración desde variables de entorno mediante Pydantic v2.

Carga desde variables de entorno y/o archivo ``.env``. Valida en el arranque:
valores inválidos o variables requeridas ausentes SHALL impedir que la aplicación
inicie lanzando ``ValidationError``.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración tipada de activia-trace.

    Toda variable requerida DEBE estar presente en el entorno o en un archivo
    ``.env`` en el directorio de trabajo. La validación ocurre en la
    instanciación.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        ...,
        description="PostgreSQL DSN con driver asyncpg, "
        "ej. postgresql+asyncpg://user:pass@localhost:5432/db",
    )

    DATABASE_URL_TEST: str | None = Field(
        default=None,
        description="PostgreSQL DSN para tests (opcional, "
        "usa DATABASE_URL como fallback si no se provee)",
    )

    # ── Security ──────────────────────────────────────────────────────────
    SECRET_KEY: str = Field(
        ...,
        min_length=32,
        description="Clave secreta para firma JWT (mínimo 32 caracteres)",
    )

    ENCRYPTION_KEY: str = Field(
        ...,
        min_length=32,
        description="Clave AES-256 para cifrado en reposo (mínimo 32 caracteres; "
        "puede ser texto plano o base64 — la normalización la hace EncryptionService)",
    )

    # ── JWT ───────────────────────────────────────────────────────────────
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=15,
        ge=1,
        description="Minutos de validez del access token JWT (default: 15)",
    )

    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        ge=1,
        description="Días de validez del refresh token opaco (default: 7)",
    )

    # ── Password recovery ─────────────────────────────────────────────────
    PASSWORD_RESET_EXPIRE_MINUTES: int = Field(
        default=30,
        ge=1,
        description="Minutos de validez del token de reset de contraseña (default: 30)",
    )

    # ── 2FA ───────────────────────────────────────────────────────────────
    TWO_FA_CHALLENGE_EXPIRE_MINUTES: int = Field(
        default=5,
        ge=1,
        description="Minutos de validez del challenge token de 2FA (default: 5)",
    )

    TOTP_ISSUER: str = Field(
        default="activia-trace",
        min_length=1,
        max_length=64,
        description="Issuer del secret TOTP — aparece en apps authenticator",
    )

    # ── Rate limiting ─────────────────────────────────────────────────────
    LOGIN_RATE_LIMIT: str = Field(
        default="5/60s",
        description="Rate limit para endpoints sensibles (formato slowapi: count/period)",
    )

    # ── Mail ──────────────────────────────────────────────────────────────
    MAILER_MODE: str = Field(
        default="console",
        pattern=r"^(console|n8n)$",
        description="Modo de envío de mail: 'console' (log JSON) o 'n8n' (futuro)",
    )

    # ── Environment ───────────────────────────────────────────────────────
    ENVIRONMENT: str = Field(
        default="development",
        pattern=r"^(development|staging|production)$",
        description="Entorno de ejecución",
    )

    LOG_LEVEL: str = Field(
        default="DEBUG",
        pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Nivel de log",
    )
