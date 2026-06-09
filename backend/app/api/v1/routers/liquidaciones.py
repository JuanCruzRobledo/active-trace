"""Router de Liquidaciones y Honorarios (C-18).

Endpoints agrupados por recurso:
  - /api/liquidaciones/grilla/claves-plus — CRUD ClavePlus
  - /api/liquidaciones/grilla/salarios-base — CRUD SalarioBase
  - /api/liquidaciones/grilla/salarios-plus — CRUD SalarioPlus
  - /api/liquidaciones — cálculo, cierre, consulta
  - /api/liquidaciones/facturas — CRUD Factura
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    UserContext,
    get_current_user,
    get_db,
    require_permission,
)
from app.core.exceptions import BusinessError
from app.models.clave_plus import ClavePlus
from app.models.factura import Factura
from app.models.liquidacion import Liquidacion
from app.models.salario_base import SalarioBase
from app.models.salario_plus import SalarioPlus
from app.repositories.clave_plus_repository import ClavePlusRepository
from app.repositories.factura_repository import FacturaRepository
from app.repositories.liquidacion_repository import LiquidacionRepository
from app.repositories.salario_base_repository import SalarioBaseRepository
from app.repositories.salario_plus_repository import SalarioPlusRepository
from app.schemas.liquidaciones import (
    ClavePlusCreate,
    ClavePlusResponse,
    ClavePlusUpdate,
    FacturaAbonarRequest,
    FacturaCreate,
    FacturaResponse,
    FacturaUpdate,
    LiquidacionCalcularRequest,
    LiquidacionCerrarRequest,
    LiquidacionListResponse,
    LiquidacionResponse,
    SalarioBaseCreate,
    SalarioBaseResponse,
    SalarioBaseUpdate,
    SalarioPlusCreate,
    SalarioPlusResponse,
    SalarioPlusUpdate,
)
from app.services.factura_service import FacturaService
from app.services.liquidacion_service import LiquidacionService

router = APIRouter(
    prefix="/api/liquidaciones",
    tags=["liquidaciones"],
)


# ═══════════════════════════════════════════════════════════════════════════
# Builders de repos y servicios
# ═══════════════════════════════════════════════════════════════════════════


def _cp_repo(db: AsyncSession, ctx: UserContext) -> ClavePlusRepository:
    return ClavePlusRepository(db, ClavePlus, ctx.tenant_id)


def _sb_repo(db: AsyncSession, ctx: UserContext) -> SalarioBaseRepository:
    return SalarioBaseRepository(db, SalarioBase, ctx.tenant_id)


def _sp_repo(db: AsyncSession, ctx: UserContext) -> SalarioPlusRepository:
    return SalarioPlusRepository(db, SalarioPlus, ctx.tenant_id)


def _liq_svc(db: AsyncSession, ctx: UserContext) -> LiquidacionService:
    return LiquidacionService(session=db, tenant_id=ctx.tenant_id)


def _fact_svc(db: AsyncSession, ctx: UserContext) -> FacturaService:
    return FacturaService(session=db, tenant_id=ctx.tenant_id)


# ═══════════════════════════════════════════════════════════════════════════
# Grilla Salarial — ClavePlus
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/grilla/claves-plus",
    status_code=status.HTTP_201_CREATED,
    response_model=ClavePlusResponse,
)
async def crear_clave_plus(
    body: ClavePlusCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("liquidaciones:configurar-salarios")),
) -> dict:
    """Crea una nueva clave de plus salarial."""
    repo = _cp_repo(db, ctx)
    # Verificar código duplicado antes de insertar
    existente = await repo.find_by_codigo(body.codigo)
    if existente is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una clave con ese código")
    clave = ClavePlus(
        tenant_id=ctx.tenant_id,
        codigo=body.codigo,
        nombre=body.nombre,
        activa=body.activa,
    )
    db.add(clave)
    await db.flush()
    return {"id": str(clave.id), "tenant_id": str(clave.tenant_id), "codigo": clave.codigo, "nombre": clave.nombre, "activa": clave.activa, "created_at": clave.created_at, "updated_at": clave.updated_at}


@router.get(
    "/grilla/claves-plus",
    response_model=list[ClavePlusResponse],
)
async def listar_claves_plus(
    activas: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("liquidaciones:configurar-salarios")),
) -> list[dict]:
    """Lista claves de plus salarial."""
    repo = _cp_repo(db, ctx)
    if activas:
        claves = await repo.list_activas()
    else:
        from sqlalchemy import select
        stmt = repo._scope_query(select(repo.model))
        result = await db.scalars(stmt)
        claves = list(result.all())
    return [{"id": str(c.id), "tenant_id": str(c.tenant_id), "codigo": c.codigo, "nombre": c.nombre, "activa": c.activa, "created_at": c.created_at, "updated_at": c.updated_at} for c in claves]


@router.get(
    "/grilla/claves-plus/{clave_id}",
    response_model=ClavePlusResponse,
)
async def obtener_clave_plus(
    clave_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("liquidaciones:configurar-salarios")),
) -> dict:
    """Obtiene una clave de plus por ID."""
    repo = _cp_repo(db, ctx)
    clave = await repo.get_by_id(clave_id)
    if clave is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clave no encontrada")
    return {"id": str(clave.id), "tenant_id": str(clave.tenant_id), "codigo": clave.codigo, "nombre": clave.nombre, "activa": clave.activa, "created_at": clave.created_at, "updated_at": clave.updated_at}


@router.patch("/grilla/claves-plus/{clave_id}")
async def actualizar_clave_plus(
    clave_id: UUID,
    body: ClavePlusUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("liquidaciones:configurar-salarios")),
) -> dict:
    """Actualiza una clave de plus."""
    repo = _cp_repo(db, ctx)
    clave = await repo.get_by_id(clave_id)
    if clave is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clave no encontrada")
    if body.codigo is not None:
        clave.codigo = body.codigo
    if body.nombre is not None:
        clave.nombre = body.nombre
    if body.activa is not None:
        clave.activa = body.activa
    await db.flush()
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════════
# Grilla Salarial — SalarioBase
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/grilla/salarios-base",
    status_code=status.HTTP_201_CREATED,
    response_model=SalarioBaseResponse,
)
async def crear_salario_base(
    body: SalarioBaseCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("liquidaciones:configurar-salarios")),
) -> dict:
    """Crea un salario base."""
    sb = SalarioBase(
        tenant_id=ctx.tenant_id,
        rol=body.rol,
        monto=body.monto,
        desde=body.desde,
        hasta=body.hasta,
    )
    db.add(sb)
    await db.flush()
    return {"id": str(sb.id), "tenant_id": str(sb.tenant_id), "rol": sb.rol, "monto": sb.monto, "desde": sb.desde, "hasta": sb.hasta, "created_at": sb.created_at, "updated_at": sb.updated_at}


@router.get(
    "/grilla/salarios-base",
    response_model=list[SalarioBaseResponse],
)
async def listar_salarios_base(
    rol: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("liquidaciones:configurar-salarios")),
) -> list[dict]:
    """Lista salarios base."""
    repo = _sb_repo(db, ctx)
    if rol:
        items = await repo.list_by_rol(rol)
    else:
        from sqlalchemy import select
        stmt = repo._scope_query(select(repo.model))
        result = await db.scalars(stmt)
        items = list(result.all())
    return [{"id": str(s.id), "tenant_id": str(s.tenant_id), "rol": s.rol, "monto": s.monto, "desde": s.desde, "hasta": s.hasta, "created_at": s.created_at, "updated_at": s.updated_at} for s in items]


# ═══════════════════════════════════════════════════════════════════════════
# Grilla Salarial — SalarioPlus
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/grilla/salarios-plus",
    status_code=status.HTTP_201_CREATED,
    response_model=SalarioPlusResponse,
)
async def crear_salario_plus(
    body: SalarioPlusCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("liquidaciones:configurar-salarios")),
) -> dict:
    """Crea un plus salarial."""
    sp = SalarioPlus(
        tenant_id=ctx.tenant_id,
        grupo=body.grupo,
        rol=body.rol,
        descripcion=body.descripcion,
        monto=body.monto,
        desde=body.desde,
        hasta=body.hasta,
    )
    db.add(sp)
    await db.flush()
    return {"id": str(sp.id), "tenant_id": str(sp.tenant_id), "grupo": sp.grupo, "rol": sp.rol, "descripcion": sp.descripcion, "monto": sp.monto, "desde": sp.desde, "hasta": sp.hasta, "created_at": sp.created_at, "updated_at": sp.updated_at}


@router.get(
    "/grilla/salarios-plus",
    response_model=list[SalarioPlusResponse],
)
async def listar_salarios_plus(
    grupo: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("liquidaciones:configurar-salarios")),
) -> list[dict]:
    """Lista plus salariales."""
    repo = _sp_repo(db, ctx)
    if grupo:
        items = await repo.list_by_grupo(grupo)
    else:
        from sqlalchemy import select
        stmt = repo._scope_query(select(repo.model))
        result = await db.scalars(stmt)
        items = list(result.all())
    return [{"id": str(s.id), "tenant_id": str(s.tenant_id), "grupo": s.grupo, "rol": s.rol, "descripcion": s.descripcion, "monto": s.monto, "desde": s.desde, "hasta": s.hasta, "created_at": s.created_at, "updated_at": s.updated_at} for s in items]


# ═══════════════════════════════════════════════════════════════════════════
# Liquidaciones
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/calcular",
    status_code=status.HTTP_201_CREATED,
    response_model=LiquidacionResponse,
)
async def calcular_liquidacion(
    body: LiquidacionCalcularRequest,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("liquidaciones:calcular")),
) -> dict:
    """Calcula una liquidación mensual."""
    svc = _liq_svc(db, ctx)
    try:
        liq = await svc.calcular(
            cohorte_id=UUID(body.cohorte_id),
            periodo=body.periodo,
            usuario_id=UUID(body.usuario_id),
            rol=body.rol,
            comisiones=body.comisiones,
        )
    except BusinessError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _liq_to_dict(liq)


@router.post(
    "/{liquidacion_id}/cerrar",
)
async def cerrar_liquidacion(
    liquidacion_id: UUID,
    body: LiquidacionCerrarRequest | None = None,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("liquidaciones:cerrar")),
) -> dict:
    """Cierra una liquidación (inmutable tras cierre)."""
    svc = _liq_svc(db, ctx)
    try:
        await svc.cerrar(liquidacion_id, actor_id=ctx.user_id)
    except BusinessError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"ok": True}


@router.get(
    "",
    response_model=LiquidacionListResponse,
)
async def listar_liquidaciones(
    periodo: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("liquidaciones:ver")),
) -> dict:
    """Lista liquidaciones del tenant."""
    svc = _liq_svc(db, ctx)
    if periodo:
        items = await svc.listar_por_periodo(periodo)
    else:
        items = await svc.listar_abiertas()
    return {
        "items": [_liq_to_dict(liq) for liq in items],
        "total": len(items),
    }


def _liq_to_dict(liq: Liquidacion) -> dict:
    return {
        "id": str(liq.id),
        "tenant_id": str(liq.tenant_id),
        "cohorte_id": str(liq.cohorte_id),
        "periodo": liq.periodo,
        "usuario_id": str(liq.usuario_id),
        "rol": liq.rol,
        "comisiones": liq.comisiones,
        "monto_base": str(liq.monto_base),
        "monto_plus": str(liq.monto_plus),
        "total": str(liq.total),
        "es_nexo": liq.es_nexo,
        "excluido_por_factura": liq.excluido_por_factura,
        "estado": liq.estado,
        "cerrada_at": liq.cerrada_at.isoformat() if liq.cerrada_at else None,
        "created_at": liq.created_at.isoformat(),
        "updated_at": liq.updated_at.isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Facturas — DEFINIDAS ANTES de /{liquidacion_id} para evitar route conflict
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/facturas",
    status_code=status.HTTP_201_CREATED,
    response_model=FacturaResponse,
)
async def crear_factura(
    body: FacturaCreate,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("facturas:gestionar")),
) -> dict:
    """Crea una factura para un docente facturador."""
    svc = _fact_svc(db, ctx)
    try:
        factura = await svc.crear(
            usuario_id=UUID(body.usuario_id),
            periodo=body.periodo,
            detalle=body.detalle,
            referencia_archivo=body.referencia_archivo,
            tamano_kb=body.tamano_kb,
        )
    except BusinessError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _fact_to_dict(factura)


@router.get(
    "/facturas",
    response_model=list[FacturaResponse],
)
async def listar_facturas(
    pendientes: bool | None = Query(None),
    usuario_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("facturas:gestionar")),
) -> list[dict]:
    """Lista facturas."""
    svc = _fact_svc(db, ctx)
    if pendientes:
        items = await svc.listar_pendientes()
    elif usuario_id:
        items = await svc.listar_por_usuario(usuario_id)
    else:
        repo = FacturaRepository(db, Factura, ctx.tenant_id)
        from sqlalchemy import select
        stmt = repo._scope_query(select(repo.model))
        result = await db.scalars(stmt)
        items = list(result.all())
    return [_fact_to_dict(f) for f in items]


@router.get(
    "/{liquidacion_id}",
    response_model=LiquidacionResponse,
)
async def obtener_liquidacion(
    liquidacion_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("liquidaciones:ver")),
) -> dict:
    """Obtiene detalle de una liquidación."""
    svc = _liq_svc(db, ctx)
    liq = await svc.obtener(liquidacion_id)
    if liq is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liquidación no encontrada")
    return _liq_to_dict(liq)


@router.post(
    "/facturas/{factura_id}/abonar",
)
async def abonar_factura(
    factura_id: UUID,
    body: FacturaAbonarRequest | None = None,
    db: AsyncSession = Depends(get_db),
    ctx: UserContext = Depends(require_permission("facturas:gestionar")),
) -> dict:
    """Marca una factura como abonada."""
    svc = _fact_svc(db, ctx)
    try:
        await svc.abonar(factura_id, actor_id=ctx.user_id)
    except BusinessError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"ok": True}


def _fact_to_dict(factura: Factura) -> dict:
    return {
        "id": str(factura.id),
        "tenant_id": str(factura.tenant_id),
        "usuario_id": str(factura.usuario_id),
        "periodo": factura.periodo,
        "detalle": factura.detalle,
        "referencia_archivo": factura.referencia_archivo,
        "tamano_kb": factura.tamano_kb,
        "estado": factura.estado,
        "cargada_at": factura.cargada_at,
        "abonada_at": factura.abonada_at,
        "created_at": factura.created_at,
        "updated_at": factura.updated_at,
    }
