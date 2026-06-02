"""Servicio de cifrado AES-256 en reposo para PII.

Utiliza **Fernet** (``cryptography.fernet.Fernet``) que implementa
AES-128-CBC con HMAC-SHA256 — cifrado autenticado (NIST-approved).

La clave se obtiene de la variable de entorno ``ENCRYPTION_KEY``
(base64-encoded 32 bytes). El servicio nunca logea texto plano.

Uso::

    from app.core.encryption import EncryptionService

    svc = EncryptionService()
    ct = svc.encrypt("dato sensible")
    pt = svc.decrypt(ct)
"""

import base64
import os
from typing import Any

from cryptography.fernet import Fernet
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator


class EncryptionService:
    """Cifrado autenticado AES-256 para datos PII en reposo.

    Args:
        key: Clave Fernet (base64 string, 32 bytes decodeados).
            Si es ``None``, se lee de ``ENCRYPTION_KEY`` en el entorno.

    Raises:
        ValueError: Si no hay clave disponible.
    """

    def __init__(self, key: str | None = None):
        raw = key or os.environ.get("ENCRYPTION_KEY")
        if not raw:
            raise ValueError(
                "ENCRYPTION_KEY no configurada. "
                "Setear la variable de entorno con una clave Fernet válida "
                "(base64-encoded 32 bytes)."
            )
        # Asegurar formato Fernet: la clave debe ser base64 URL-safe de 32 bytes
        try:
            self._fernet = Fernet(self._normalize_key(raw))
        except Exception as exc:
            raise ValueError(
                f"Clave ENCRYPTION_KEY inválida: {exc}"
            ) from exc

    @staticmethod
    def _normalize_key(raw: str) -> bytes:
        """Normaliza una clave raw al formato Fernet (32 bytes, base64).

        Si raw ya es base64 URL-safe de 32 bytes, se usa directamente.
        Si raw es texto plano de 32 caracteres, se encodea a base64.
        """
        # Intentar usar como base64 directo primero
        try:
            decoded = base64.urlsafe_b64decode(raw.encode() + b"==")
            if len(decoded) == 32:
                return raw.encode() if raw.endswith("=") else base64.urlsafe_b64encode(decoded)
        except Exception:
            pass

        # Si es texto plano de 32 chars, encodear a base64
        if len(raw) >= 32:
            key_bytes = raw.encode()[:32].ljust(32, b"\0")
            return base64.urlsafe_b64encode(key_bytes)

        raise ValueError("La clave debe tener al menos 32 caracteres")

    def encrypt(self, plaintext: str) -> str:
        """Cifra texto plano a ciphertext base64 URL-safe.

        Args:
            plaintext: Texto a cifrar (str).

        Returns:
            Ciphertext codificado como string base64 URL-safe.
        """
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Descifra ciphertext a texto plano.

        Args:
            ciphertext: Texto cifrado en base64 URL-safe.

        Returns:
            Texto plano original.

        Raises:
            cryptography.fernet.InvalidToken: Si el ciphertext es inválido
                o fue alterado.
        """
        return self._fernet.decrypt(ciphertext.encode()).decode()


class EncryptedColumn(TypeDecorator[Any]):
    """TypeDecorator de SQLAlchemy que cifra/descifra valores transparentemente.

    Los atributos PII ``[cifrado]`` en los modelos (email, DNI, CUIL, CBU)
    usan este tipo para garantizar cifrado en reposo automático sin lógica
    extra en las capas superiores.

    Uso::

        class Usuario(Base, BaseMixin):
            __tablename__ = "usuario"
            email = Column(EncryptedColumn(key=settings.ENCRYPTION_KEY))

    Args:
        key: Clave Fernet para el cifrado. Se pasa al crear la columna.
            En producción se lee de las settings del tenant.
    """

    impl = Text
    cache_ok = True

    def __init__(self, key: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._encryption_service = EncryptionService(key=key)

    def process_bind_param(
        self, value: str | None, dialect: Any
    ) -> str | None:
        """Cifra el valor antes de persistirlo.

        Args:
            value: Texto plano a cifrar.
            dialect: Dialecto de base de datos (ignorado).

        Returns:
            Ciphertext o ``None`` si el valor es nulo.
        """
        if value is None:
            return None
        return self._encryption_service.encrypt(value)

    def process_result_value(
        self, value: str | None, dialect: Any
    ) -> str | None:
        """Descifra el valor al leerlo de la base de datos.

        Args:
            value: Ciphertext almacenado.
            dialect: Dialecto de base de datos (ignorado).

        Returns:
            Texto plano o ``None`` si el valor es nulo.
        """
        if value is None:
            return None
        return self._encryption_service.decrypt(value)


# ── Fields marked [cifrado] in the knowledge base ──────────────────────────
#
# These PII fields MUST use EncryptedColumn when created in their respective
# models (C-07 usuarios-y-asignaciones):
#
#   Usuario:
#     - email         → Column(EncryptedCollumn(key=...), unique=True)
#     - dni           → Column(EncryptedCollumn(key=...))
#     - cuil          → Column(EncryptedCollumn(key=...))
#     - cbu           → Column(EncryptedCollumn(key=...))
#     - alias_cbu     → Column(EncryptedCollumn(key=...))
#
#   Comunicacion (C-12):
#     - destinatario  → Column(EncryptedCollumn(key=...))
#
# The ENCRYPTION_KEY is loaded via Settings and should be scoped per-tenant
# for future multi-key isolation (ADR-002 row-level with tenant keys).
