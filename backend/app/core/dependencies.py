"""FastAPI dependencies (inyección de dependencias).

Implementado en C-01
    - ``get_db``: sesión async por request.

Reservados para C-02/C-03/C-04
    - ``get_current_user``: extrae usuario autenticado del JWT → C-03.
    - ``get_tenant``: resuelve el tenant activo → C-02.
    - ``require_permission``: verifica permiso ``modulo:accion`` → C-04.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency que provee una sesión async por request.

    Garantiza que la sesión se cierre al finalizar la request, incluso si
    el handler lanza una excepción (``finally``).
    """
    maker = get_session_maker()
    async with maker() as session:
        yield session
