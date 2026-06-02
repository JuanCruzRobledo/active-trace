"""FastAPI dependencies (inyección de dependencias).

Implementado en C-01
    - ``get_db``: sesión async por request.

Implementado en C-03
    - ``get_current_user``: extrae usuario autenticado del JWT.
    - ``UserContext``: modelo de datos del usuario autenticado.

Reservado para C-04
    - ``require_permission``: verifica permiso ``modulo:accion``.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_maker
from app.core.security import (
    InvalidTokenError,
    TokenExpiredError,
    decode_access_token,
)

# ── Bearer token extractor ─────────────────────────────────────────────

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class UserContext:
    """Contexto del usuario autenticado derivado del JWT.

    Attributes:
        user_id: UUID del usuario (claim ``sub``).
        tenant_id: UUID del tenant (claim ``tenant_id``).
        roles: Lista de roles (claim ``roles``; vacío en C-03, poblado en C-04).
    """

    user_id: UUID
    tenant_id: UUID
    roles: list[str] = field(default_factory=list)


# ── DB session ─────────────────────────────────────────────────────────


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency que provee una sesión async por request.

    Garantiza que la sesión se cierre al finalizar la request, incluso si
    el handler lanza una excepción (``finally``).
    """
    maker = get_session_maker()
    async with maker() as session:
        yield session


# ── Authenticated user ─────────────────────────────────────────────────


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> UserContext:
    """Extrae el usuario autenticado del JWT Bearer token.

    La identidad SIEMPRE se deriva del JWT verificado. Ningún parámetro
    de URL, body o header puede overridear la identidad (REGLA DURA #8).

    Returns:
        UserContext con user_id, tenant_id y roles.

    Raises:
        HTTPException 401: Si el token falta, expiró o es inválido.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Cargar settings inline para evitar dependencia circular
    from app.core.config import Settings  # noqa: PLC0415

    secret_key = Settings().SECRET_KEY  # type: ignore[call-arg]

    try:
        payload = decode_access_token(token, secret_key)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extraer claims
    from app.core.security import (  # noqa: PLC0415
        JWT_CLAIM_TENANT_ID,
        JWT_CLAIM_USER_ID,
        JWT_CLAIM_ROLES,
    )

    user_id_str = payload.get(JWT_CLAIM_USER_ID)
    tenant_id_str = payload.get(JWT_CLAIM_TENANT_ID)
    roles: list[str] = payload.get(JWT_CLAIM_ROLES, [])

    if not user_id_str or not tenant_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
        )

    return UserContext(
        user_id=UUID(user_id_str),
        tenant_id=UUID(tenant_id_str),
        roles=roles,
    )
