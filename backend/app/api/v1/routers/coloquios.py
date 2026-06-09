"""Router de Coloquios — convocatorias, reservas, resultados y metricas (C-14).

Endpoints:
- POST /api/coloquios/convocatorias — crear convocatoria.
- GET /api/coloquios/convocatorias — listar convocatorias.
- PATCH /api/coloquios/convocatorias/{id} — editar convocatoria.
- POST /api/coloquios/convocatorias/{id}/importar-alumnos — importar alumnos.
- POST /api/coloquios/convocatorias/{id}/reservar — reservar turno.
- POST /api/coloquios/convocatorias/{id}/resultados — registrar resultado.
- POST /api/coloquios/convocatorias/{id}/cerrar — cerrar convocatoria.
- POST /api/coloquios/reservas/{id}/cancelar — cancelar reserva.
- GET /api/coloquios/metricas — panel de metricas.
- GET /api/coloquios/agenda — agenda consolidada.
- GET /api/coloquios/mis-reservas — reservas del alumno autenticado.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    UserContext,
    get_db,
    require_permission,
)
from app.core.exceptions import BusinessError
from app.models.usuario import Usuario
from app.schemas.coloquios import (
    EvaluacionCreate,
    EvaluacionUpdate,
    EvaluacionResponse,
    ReservaCreate,
    ResultadoCreate,
    ImportarAlumnosRequest,
)
from app.services.coloquio_service import ColoquioService

router = APIRouter(
    prefix="/api/coloquios",
    tags=["coloquios"],
)


def _build_service(
    db: AsyncSession, ctx: UserContext, alumno_id: UUID | None = None
) -> ColoquioService:
    """Construye ColoquioService.

    Args:
        db: Sesion de base de datos.
        ctx: Contexto de usuario (JWT → auth_user_id).
        alumno_id: Si se provee, se usa como actor_id (para operaciones
            que involucran FKs a usuario.id). Si es None, se usa ctx.user_id.
    """
    return ColoquioService(
        session=db,
        tenant_id=ctx.tenant_id,
        actor_id=alumno_id or ctx.user_id,
        roles=ctx.roles,
    )


async def _resolve_usuario_id(
    db: AsyncSession, user_id: UUID
) -> UUID:
    """Resuelve un user_id a ``usuario.id``.

    El JWT puede contener ``users.id`` (auth) o directamente ``usuario.id``
    (tests). Probamos ambas vías:
    1. Si ``user_id`` ya es un ``usuario.id`` → lo retorna directo.
    2. Si no, busca por ``usuario.auth_user_id == user_id``.
    """
    # 1. Probar si ya es usuario.id
    row = await db.get(Usuario, user_id)
    if row is not None:
        return row.id

    # 2. Probar por auth_user_id (FK → users.id)
    result = await db.execute(
        select(Usuario.id).where(Usuario.auth_user_id == user_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de usuario no encontrado",
        )
    return row


# ── Convocatorias ──────────────────────────────────────────────────────


@router.post("/convocatorias", status_code=status.HTTP_201_CREATED)
async def crear_convocatoria(
    body: EvaluacionCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("coloquios:gestionar")),
) -> dict:
    """Crea una nueva convocatoria de evaluacion (coloquio)."""
    service = _build_service(db, ctx)
    try:
        return await service.crear_convocatoria(body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/convocatorias")
async def listar_convocatorias(
    materia_id: UUID | None = Query(None),
    cohorte_id: UUID | None = Query(None),
    estado: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("coloquios:gestionar")),
) -> dict:
    """Lista convocatorias con filtros opcionales."""
    service = _build_service(db, ctx)
    return await service.listar_convocatorias(
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        estado=estado,
    )


@router.patch("/convocatorias/{evaluacion_id}")
async def editar_convocatoria(
    evaluacion_id: UUID,
    body: EvaluacionUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("coloquios:gestionar")),
) -> dict:
    """Edita una convocatoria existente."""
    service = _build_service(db, ctx)
    try:
        return await service.actualizar_convocatoria(evaluacion_id, body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Importar alumnos ───────────────────────────────────────────────────


@router.post("/convocatorias/{evaluacion_id}/importar-alumnos")
async def importar_alumnos(
    evaluacion_id: UUID,
    body: ImportarAlumnosRequest,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("coloquios:gestionar")),
) -> dict:
    """Importa alumnos a una convocatoria."""
    service = _build_service(db, ctx)
    try:
        result = await service.importar_alumnos(evaluacion_id, body)
        return {"importados": result.importados, "omitidos": result.omitidos}
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Reservas ───────────────────────────────────────────────────────────


@router.post("/convocatorias/{evaluacion_id}/reservar", status_code=status.HTTP_201_CREATED)
async def reservar_turno(
    evaluacion_id: UUID,
    body: ReservaCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("coloquios:reservar")),
) -> dict:
    """Reserva un turno de coloquio (ALUMNO)."""
    # Forzar evaluacion_id del path
    body.evaluacion_id = evaluacion_id
    # Resolver auth_user_id → usuario.id (FK de reserva_evaluacion)
    usuario_id = await _resolve_usuario_id(db, ctx.user_id)
    service = _build_service(db, ctx)
    try:
        return await service.reservar_turno(body, alumno_id=usuario_id)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post("/reservas/{reserva_id}/cancelar")
async def cancelar_reserva(
    reserva_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("coloquios:reservar")),
) -> dict:
    """Cancela una reserva propia (ALUMNO)."""
    usuario_id = await _resolve_usuario_id(db, ctx.user_id)
    service = _build_service(db, ctx, alumno_id=usuario_id)
    try:
        return await service.cancelar_reserva(reserva_id)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/mis-reservas")
async def mis_reservas(
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("coloquios:reservar")),
) -> dict:
    """Lista las reservas del alumno autenticado."""
    usuario_id = await _resolve_usuario_id(db, ctx.user_id)
    service = _build_service(db, ctx, alumno_id=usuario_id)
    return await service.listar_mis_reservas()


# ── Resultados ─────────────────────────────────────────────────────────


@router.post("/convocatorias/{evaluacion_id}/resultados")
async def registrar_resultado(
    evaluacion_id: UUID,
    body: ResultadoCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("coloquios:gestionar")),
) -> dict:
    """Registra el resultado de un alumno en una convocatoria."""
    body.evaluacion_id = evaluacion_id
    service = _build_service(db, ctx)
    try:
        return await service.registrar_resultado(body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── Cierre ─────────────────────────────────────────────────────────────


@router.post("/convocatorias/{evaluacion_id}/cerrar")
async def cerrar_convocatoria(
    evaluacion_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("coloquios:gestionar")),
) -> dict:
    """Cierra una convocatoria activa."""
    service = _build_service(db, ctx)
    try:
        return await service.cerrar_convocatoria(evaluacion_id)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


# ── Metricas ───────────────────────────────────────────────────────────


@router.get("/metricas")
async def obtener_metricas(
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("coloquios:ver")),
) -> dict:
    """Panel de metricas globales del modulo de coloquios."""
    service = _build_service(db, ctx)
    m = await service.obtener_metricas()
    return {
        "total_convocatorias": m.total_convocatorias,
        "total_alumnos_importados": m.total_alumnos_importados,
        "reservas_activas": m.reservas_activas,
        "resultados_registrados": m.resultados_registrados,
    }


# ── Agenda ─────────────────────────────────────────────────────────────


@router.get("/agenda")
async def obtener_agenda(
    evaluacion_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("coloquios:ver")),
) -> dict:
    """Agenda consolidada de reservas activas."""
    service = _build_service(db, ctx)
    result = await service.obtener_agenda(evaluacion_id=evaluacion_id)
    return {"items": [item.model_dump() for item in result.items], "total": result.total}
