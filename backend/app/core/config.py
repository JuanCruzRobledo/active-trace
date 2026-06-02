"""Tipada de configuración desde variables de entorno mediante Pydantic v2.

Carga desde variables de entorno y/o archivo ``.env``. Valida en el arranque:
valores inválidos o variables requeridas ausentes SHALL impedir que la aplicación
inicie lanzando ``ValidationError``.
"""

from pydantic import ConfigDict, Field
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

    # ── Security ──────────────────────────────────────────────────────────
    SECRET_KEY: str = Field(
        ...,
        min_length=32,
        description="Clave secreta para firma JWT (mínimo 32 caracteres)",
    )

    ENCRYPTION_KEY: str = Field(
        ...,
        min_length=32,
        max_length=32,
        description="Clave AES-256 para cifrado en reposo (exactamente 32 caracteres)",
    )

    # ── JWT ───────────────────────────────────────────────────────────────
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=15,
        ge=1,
        description="Minutos de validez del access token JWT (default: 15)",
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
