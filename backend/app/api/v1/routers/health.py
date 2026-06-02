"""Health-check endpoint (liveness + readiness de DB)."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """GET /health — estado de la aplicación y readiness de base de datos.

    Returns:
        Diccionario con ``status`` (siempre ``"ok"``) y ``database``
        (``"up"`` o ``"down"``).  Nunca crashea: si la DB no responde,
        reporta ``database: "down"`` y responde igual.
    """
    db_status = "up"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 — captura genérica intencional
        db_status = "down"

    return {"status": "ok", "database": db_status}
