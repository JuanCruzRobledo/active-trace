"""Router de administracion de estructura academica (C-06).

Endpoints protegidos con require_permission("estructura:gestionar"):
- ``/api/admin/carreras`` — CRUD de carreras.
- ``/api/admin/materias`` — CRUD de materias.
- ``/api/admin/cohortes`` — CRUD de cohortes.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    UserContext,
    get_current_user,
    get_db,
    require_permission,
)
from app.core.exceptions import BusinessError
from app.schemas.carrera import CarreraCreate, CarreraResponse, CarreraUpdate
from app.schemas.cohorte import CohorteCreate, CohorteResponse, CohorteUpdate
from app.schemas.materia import MateriaCreate, MateriaResponse, MateriaUpdate
from app.services.carrera_service import CarreraService
from app.services.cohorte_service import CohorteService
from app.services.materia_service import MateriaService

router = APIRouter(
    prefix="/api/admin",
    tags=["admin", "estructura"],
)


# ── Helpers ──────────────────────────────────────────────────────────


def _build_carrera_service(
    db: AsyncSession, tenant_id: UUID
) -> CarreraService:
    return CarreraService(session=db, tenant_id=tenant_id)


def _build_materia_service(
    db: AsyncSession, tenant_id: UUID
) -> MateriaService:
    return MateriaService(session=db, tenant_id=tenant_id)


def _build_cohorte_service(
    db: AsyncSession, tenant_id: UUID
) -> CohorteService:
    return CohorteService(session=db, tenant_id=tenant_id)


def _carrera_to_response(c: object) -> CarreraResponse:
    return CarreraResponse(
        id=str(c.id),
        tenant_id=str(c.tenant_id),
        codigo=c.codigo,
        nombre=c.nombre,
        estado=c.estado,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _materia_to_response(m: object) -> MateriaResponse:
    return MateriaResponse(
        id=str(m.id),
        tenant_id=str(m.tenant_id),
        codigo=m.codigo,
        nombre=m.nombre,
        estado=m.estado,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _cohorte_to_response(c: object) -> CohorteResponse:
    return CohorteResponse(
        id=str(c.id),
        tenant_id=str(c.tenant_id),
        carrera_id=str(c.carrera_id),
        nombre=c.nombre,
        anio=c.anio,
        vig_desde=c.vig_desde,
        vig_hasta=c.vig_hasta,
        estado=c.estado,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


# ═══════════════════════════════════════════════════════════════════════
# Carreras
# ═══════════════════════════════════════════════════════════════════════


@router.post(
    "/carreras",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("estructura:gestionar"))],
)
async def crear_carrera(
    body: CarreraCreate,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CarreraResponse:
    """Crea una nueva carrera."""
    svc = _build_carrera_service(db, current_user.tenant_id)
    try:
        carrera = await svc.crear(body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return _carrera_to_response(carrera)


@router.get(
    "/carreras",
    dependencies=[Depends(require_permission("estructura:gestionar"))],
)
async def listar_carreras(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CarreraResponse]:
    """Lista todas las carreras del tenant."""
    svc = _build_carrera_service(db, current_user.tenant_id)
    carreras = await svc.listar()
    return [_carrera_to_response(c) for c in carreras]


@router.get(
    "/carreras/{carrera_id}",
    dependencies=[Depends(require_permission("estructura:gestionar"))],
)
async def obtener_carrera(
    carrera_id: UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CarreraResponse:
    """Obtiene una carrera por ID."""
    svc = _build_carrera_service(db, current_user.tenant_id)
    carrera = await svc.obtener(carrera_id)
    if carrera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrera no encontrada",
        )
    return _carrera_to_response(carrera)


@router.patch(
    "/carreras/{carrera_id}",
    dependencies=[Depends(require_permission("estructura:gestionar"))],
)
async def actualizar_carrera(
    carrera_id: UUID,
    body: CarreraUpdate,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CarreraResponse:
    """Actualiza parcialmente una carrera."""
    svc = _build_carrera_service(db, current_user.tenant_id)
    try:
        carrera = await svc.actualizar(carrera_id, body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    if carrera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carrera no encontrada",
        )
    return _carrera_to_response(carrera)


# ═══════════════════════════════════════════════════════════════════════
# Materias
# ═══════════════════════════════════════════════════════════════════════


@router.post(
    "/materias",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("estructura:gestionar"))],
)
async def crear_materia(
    body: MateriaCreate,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MateriaResponse:
    """Crea una nueva materia."""
    svc = _build_materia_service(db, current_user.tenant_id)
    try:
        materia = await svc.crear(body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return _materia_to_response(materia)


@router.get(
    "/materias",
    dependencies=[Depends(require_permission("estructura:gestionar"))],
)
async def listar_materias(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MateriaResponse]:
    """Lista todas las materias del tenant."""
    svc = _build_materia_service(db, current_user.tenant_id)
    materias = await svc.listar()
    return [_materia_to_response(m) for m in materias]


@router.get(
    "/materias/{materia_id}",
    dependencies=[Depends(require_permission("estructura:gestionar"))],
)
async def obtener_materia(
    materia_id: UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MateriaResponse:
    """Obtiene una materia por ID."""
    svc = _build_materia_service(db, current_user.tenant_id)
    materia = await svc.obtener(materia_id)
    if materia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Materia no encontrada",
        )
    return _materia_to_response(materia)


@router.patch(
    "/materias/{materia_id}",
    dependencies=[Depends(require_permission("estructura:gestionar"))],
)
async def actualizar_materia(
    materia_id: UUID,
    body: MateriaUpdate,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MateriaResponse:
    """Actualiza parcialmente una materia."""
    svc = _build_materia_service(db, current_user.tenant_id)
    try:
        materia = await svc.actualizar(materia_id, body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    if materia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Materia no encontrada",
        )
    return _materia_to_response(materia)


# ═══════════════════════════════════════════════════════════════════════
# Cohortes
# ═══════════════════════════════════════════════════════════════════════


@router.post(
    "/cohortes",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("estructura:gestionar"))],
)
async def crear_cohorte(
    body: CohorteCreate,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CohorteResponse:
    """Crea una nueva cohorte."""
    svc = _build_cohorte_service(db, current_user.tenant_id)
    try:
        cohorte = await svc.crear(body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return _cohorte_to_response(cohorte)


@router.get(
    "/cohortes",
    dependencies=[Depends(require_permission("estructura:gestionar"))],
)
async def listar_cohortes(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CohorteResponse]:
    """Lista todas las cohortes del tenant."""
    svc = _build_cohorte_service(db, current_user.tenant_id)
    cohortes = await svc.listar()
    return [_cohorte_to_response(c) for c in cohortes]


@router.get(
    "/cohortes/{cohorte_id}",
    dependencies=[Depends(require_permission("estructura:gestionar"))],
)
async def obtener_cohorte(
    cohorte_id: UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CohorteResponse:
    """Obtiene una cohorte por ID."""
    svc = _build_cohorte_service(db, current_user.tenant_id)
    cohorte = await svc.obtener(cohorte_id)
    if cohorte is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cohorte no encontrada",
        )
    return _cohorte_to_response(cohorte)


@router.patch(
    "/cohortes/{cohorte_id}",
    dependencies=[Depends(require_permission("estructura:gestionar"))],
)
async def actualizar_cohorte(
    cohorte_id: UUID,
    body: CohorteUpdate,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CohorteResponse:
    """Actualiza parcialmente una cohorte."""
    svc = _build_cohorte_service(db, current_user.tenant_id)
    try:
        cohorte = await svc.actualizar(cohorte_id, body)
    except BusinessError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    if cohorte is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cohorte no encontrada",
        )
    return _cohorte_to_response(cohorte)
