"""Tests E2E de Tareas Internas — CRUD, estados, comentarios, multi-tenant (C-16).

Cubre:
  CRUD de tareas, cambios de estado (transiciones válidas e inválidas),
  comentarios asincrónicos, timeline personal, vista admin con filtros,
  búsqueda textual, aislamiento multi-tenant, permisos.

Requiere PostgreSQL real (DATABASE_URL_TEST en el entorno).
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from tests.conftest import db_available

pytestmark = [
    pytest.mark.skipif(
        not db_available(),
        reason="Requiere PostgreSQL: definir DATABASE_URL_TEST en el entorno",
    ),
]

_DEV_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
_DEV_TENANT_ID_2 = UUID("00000000-0000-0000-0000-000000000002")
_SECRET_KEY = "a" * 64

# ── Models ───────────────────────────────────────────────────────────────

from app.models.tenant import Tenant  # noqa: E402
from app.models.permiso import Permiso  # noqa: E402
from app.models.rol import Rol  # noqa: E402
from app.models.rol_permiso import RolPermiso  # noqa: E402
from app.models.materia import Materia  # noqa: E402
from app.models.usuario import Usuario  # noqa: E402
from app.models.tarea import Tarea, ComentarioTarea  # noqa: E402
from app.models.enums import EstadoTarea  # noqa: E402
from app.models.audit_log import AuditLog  # noqa: E402


# ── Token helpers ────────────────────────────────────────────────────────


def _make_token(user_id: UUID, tenant_id: UUID, roles: list[str] | None = None) -> str:
    return create_access_token(
        user_id=user_id,
        tenant_id=tenant_id or _DEV_TENANT_ID,
        secret_key=_SECRET_KEY,
        roles=roles or [],
    )


# ── Seed helpers ─────────────────────────────────────────────────────────


async def _seed_tenant(db_session: AsyncSession, tenant_id: UUID) -> None:
    exists = await db_session.get(Tenant, tenant_id)
    if exists is None:
        db_session.add(Tenant(id=tenant_id, tenant_id=tenant_id, nombre=f"Tenant {tenant_id}"))
        await db_session.flush()


async def _seed_permisos_tareas(db_session: AsyncSession, tenant_id: UUID | None = None) -> None:
    tid = tenant_id or _DEV_TENANT_ID
    from sqlalchemy import select as sa_select

    permiso_rows = {
        "tareas:gestionar": "Gestionar tareas internas",
    }
    permiso_ids = {}
    for codigo, desc in permiso_rows.items():
        result = await db_session.execute(sa_select(Permiso).where(Permiso.codigo == codigo))
        existing = result.scalar_one_or_none()
        if existing is not None:
            permiso_ids[codigo] = existing.id
        else:
            p = Permiso(id=uuid4(), codigo=codigo, descripcion=desc)
            db_session.add(p)
            permiso_ids[codigo] = p.id

    roles_data = [
        ("PROFESOR", "Profesor", "Profesor"),
        ("COORDINADOR", "Coordinador", "Coordinador"),
        ("ADMIN", "Administrador", "Administrador"),
        ("TUTOR", "Tutor", "Tutor"),
    ]
    rol_ids = {}
    for codigo, nombre, desc in roles_data:
        r = Rol(id=uuid4(), codigo=codigo, nombre=nombre, descripcion=desc, tenant_id=tid)
        db_session.add(r)
        rol_ids[codigo] = r.id

    role_perms = {
        "COORDINADOR": ["tareas:gestionar"],
        "PROFESOR": ["tareas:gestionar"],
        "ADMIN": ["tareas:gestionar"],
        "TUTOR": [],
    }
    for rol_codigo, perm_codigos in role_perms.items():
        rid = rol_ids.get(rol_codigo)
        if rid is None:
            continue
        for pc in perm_codigos:
            pid = permiso_ids.get(pc)
            if pid is None:
                continue
            db_session.add(RolPermiso(id=uuid4(), tenant_id=tid, rol_id=rid, permiso_id=pid))
    await db_session.flush()


async def _seed_estructura(
    db_session: AsyncSession,
    *,
    tenant_id: UUID | None = None,
    codigo_sufijo: str = "",
) -> dict:
    tid = tenant_id or _DEV_TENANT_ID
    suf = codigo_sufijo or ("-B" if tid != _DEV_TENANT_ID else "")

    materia = Materia(
        tenant_id=tid, codigo=f"TEST-MAT{suf}", nombre=f"Materia Test{suf}", estado="Activo",
    )
    db_session.add(materia)
    await db_session.flush()

    return {"materia_id": materia.id}


async def _seed_usuario(
    db_session: AsyncSession, tenant_id: UUID, rol: str, sufijo: str = ""
) -> dict:
    uid = uuid4()
    usuario = Usuario(
        id=uid, tenant_id=tenant_id, auth_user_id=None,
        nombre=f"User{sufijo}", apellidos=f"Test{sufijo}",
        email=f"user{sufijo}_{uid}@test.com", estado="Activo",
    )
    db_session.add(usuario)
    await db_session.flush()
    return {"usuario_id": uid, "usuario": usuario}


async def _build_full_seed(db_session: AsyncSession, tenant_id: UUID | None = None) -> dict:
    tid = tenant_id or _DEV_TENANT_ID
    await _seed_tenant(db_session, tid)
    await _seed_permisos_tareas(db_session, tid)
    struct = await _seed_estructura(db_session, tenant_id=tid)
    coord = await _seed_usuario(db_session, tid, "COORDINADOR", "_coord")
    profe = await _seed_usuario(db_session, tid, "PROFESOR", "_profe")
    tutor = await _seed_usuario(db_session, tid, "TUTOR", "_tutor")
    struct["coord_user_id"] = coord["usuario_id"]
    struct["profe_user_id"] = profe["usuario_id"]
    struct["tutor_user_id"] = tutor["usuario_id"]
    return struct


async def _crear_tarea_en_seed(
    db_session: AsyncSession,
    asignado_a: UUID,
    tenant_id: UUID | None = None,
    materia_id: UUID | None = None,
    estado: EstadoTarea = EstadoTarea.PENDIENTE,
    asignado_por: UUID | None = None,
) -> Tarea:
    tid = tenant_id or _DEV_TENANT_ID
    tarea = Tarea(
        tenant_id=tid,
        materia_id=materia_id,
        asignado_a=asignado_a,
        asignado_por=asignado_por or asignado_a,
        estado=estado,
        descripcion="Tarea de prueba para tests",
        contexto_id=None,
    )
    db_session.add(tarea)
    await db_session.flush()
    return tarea


# ══════════════════════════════════════════════════════════════════════════
# 6.1 Tests de Repositorio
# ══════════════════════════════════════════════════════════════════════════


class TestTareaRepository:
    """6.1: CRUD Tarea, filtros, tenant scope, busqueda textual."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        self.tarea = await _crear_tarea_en_seed(
            db_session, self.seed["profe_user_id"], _DEV_TENANT_ID,
            self.seed["materia_id"],
        )
        await db_session.commit()
        from app.repositories.tarea_repository import TareaRepository
        self.repo = TareaRepository(db_session, _DEV_TENANT_ID)

    async def test_6_1_1_get_by_id(self, db_session: AsyncSession):
        """Obtener tarea por ID."""
        tarea = await self.repo.get_by_id(self.tarea.id)
        assert tarea is not None
        assert tarea.id == self.tarea.id
        assert tarea.descripcion == "Tarea de prueba para tests"

    async def test_6_1_2_get_by_id_not_found(self, db_session: AsyncSession):
        """get_by_id con ID inexistente retorna None."""
        tarea = await self.repo.get_by_id(uuid4())
        assert tarea is None

    async def test_6_1_3_list_by_asignado(self, db_session: AsyncSession):
        """Listar tareas por asignado."""
        items = await self.repo.list_by_asignado(self.seed["profe_user_id"])
        assert len(items) >= 1
        assert items[0].asignado_a == self.seed["profe_user_id"]

    async def test_6_1_4_list_by_asignado_filtro_estado(self, db_session: AsyncSession):
        """Listar tareas por asignado filtrado por estado."""
        items = await self.repo.list_by_asignado(
            self.seed["profe_user_id"], estado="Pendiente",
        )
        assert len(items) >= 1
        assert items[0].estado.value == "Pendiente"

    async def test_6_1_5_list_by_asignado_filtro_materia(self, db_session: AsyncSession):
        """Listar tareas por asignado filtrado por materia."""
        other = await _seed_usuario(db_session, _DEV_TENANT_ID, "PROFESOR", "_other")
        tarea_otra = await _crear_tarea_en_seed(
            db_session, other["usuario_id"], _DEV_TENANT_ID,
            materia_id=self.seed["materia_id"],
        )
        await db_session.commit()
        items = await self.repo.list_by_asignado(
            other["usuario_id"], materia_id=self.seed["materia_id"],
        )
        assert len(items) >= 1
        assert items[0].asignado_a == other["usuario_id"]

    async def test_6_1_6_list_by_asignado_sin_resultados(self, db_session: AsyncSession):
        """Listar tareas de un usuario sin tareas retorna vacio."""
        otro = (await _seed_usuario(db_session, _DEV_TENANT_ID, "PROFESOR", "_sin"))["usuario_id"]
        items = await self.repo.list_by_asignado(otro)
        assert len(items) == 0

    async def test_6_1_7_list_by_tenant_sin_filtros(self, db_session: AsyncSession):
        """Listar todas las tareas del tenant."""
        items = await self.repo.list_by_tenant()
        assert len(items) >= 1

    async def test_6_1_8_list_by_tenant_filtro_estado(self, db_session: AsyncSession):
        """Listar tareas del tenant filtrado por estado."""
        items = await self.repo.list_by_tenant(estado="Pendiente")
        assert len(items) >= 1
        assert items[0].estado.value == "Pendiente"

    async def test_6_1_9_list_by_tenant_filtro_asignado(self, db_session: AsyncSession):
        """Listar tareas del tenant filtrado por asignado."""
        items = await self.repo.list_by_tenant(asignado_a=self.seed["profe_user_id"])
        assert len(items) >= 1
        assert items[0].asignado_a == self.seed["profe_user_id"]

    async def test_6_1_10_list_by_tenant_busqueda_textual(self, db_session: AsyncSession):
        """Busqueda textual ILIKE sobre descripcion."""
        items = await self.repo.list_by_tenant(busqueda="prueba")
        assert len(items) >= 1

    async def test_6_1_11_list_by_tenant_busqueda_sin_resultados(self, db_session: AsyncSession):
        """Busqueda textual sin resultados retorna vacio."""
        items = await self.repo.list_by_tenant(busqueda="texto_que_no_existe_xyz")
        assert len(items) == 0

    async def test_6_1_12_update_estado(self, db_session: AsyncSession):
        """Actualizar estado de una tarea."""
        actualizada = await self.repo.update_estado(self.tarea.id, EstadoTarea.EN_PROGRESO)
        assert actualizada is not None
        assert actualizada.estado.value == "En progreso"

    async def test_6_1_13_update_estado_not_found(self, db_session: AsyncSession):
        """Actualizar estado de tarea inexistente retorna None."""
        result = await self.repo.update_estado(uuid4(), EstadoTarea.EN_PROGRESO)
        assert result is None

    async def test_6_1_14_update(self, db_session: AsyncSession):
        """Actualizar campos de una tarea."""
        actualizada = await self.repo.update(
            self.tarea.id, {"descripcion": "Descripcion actualizada"},
        )
        assert actualizada is not None
        assert actualizada.descripcion == "Descripcion actualizada"

    async def test_6_1_15_update_not_found(self, db_session: AsyncSession):
        """Actualizar tarea inexistente retorna None."""
        result = await self.repo.update(uuid4(), {"descripcion": "Nope"})
        assert result is None

    async def test_6_1_16_tenant_scope(self, db_session: AsyncSession):
        """Repo filtra por tenant automaticamente."""
        otro_tenant = _DEV_TENANT_ID_2
        await _seed_tenant(db_session, otro_tenant)
        await db_session.commit()
        repo_otro = type(self.repo)(db_session, otro_tenant)
        items = await repo_otro.list_by_tenant()
        assert len(items) == 0


class TestComentarioRepository:
    """6.1: CRUD ComentarioTarea."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        self.tarea = await _crear_tarea_en_seed(
            db_session, self.seed["profe_user_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        from app.repositories.tarea_repository import ComentarioRepository
        self.repo = ComentarioRepository(db_session, _DEV_TENANT_ID)

    async def test_6_1_17_crear_comentario(self, db_session: AsyncSession):
        """Crear comentario exitosamente."""
        comentario = ComentarioTarea(
            tenant_id=_DEV_TENANT_ID,
            tarea_id=self.tarea.id,
            autor_id=self.seed["coord_user_id"],
            texto="Comentario de prueba",
        )
        creado = await self.repo.create(comentario)
        assert creado is not None
        assert creado.texto == "Comentario de prueba"
        assert creado.tarea_id == self.tarea.id

    async def test_6_1_18_list_by_tarea_orden_asc(self, db_session: AsyncSession):
        """Listar comentarios ordenados por creado_at ASC."""
        c1 = ComentarioTarea(
            tenant_id=_DEV_TENANT_ID, tarea_id=self.tarea.id,
            autor_id=self.seed["coord_user_id"], texto="Primero",
        )
        c2 = ComentarioTarea(
            tenant_id=_DEV_TENANT_ID, tarea_id=self.tarea.id,
            autor_id=self.seed["profe_user_id"], texto="Segundo",
        )
        await self.repo.create(c1)
        await self.repo.create(c2)
        comentarios = await self.repo.list_by_tarea(self.tarea.id)
        assert len(comentarios) >= 2
        assert comentarios[0].texto == "Primero"
        assert comentarios[1].texto == "Segundo"

    async def test_6_1_19_list_by_tarea_vacio(self, db_session: AsyncSession):
        """Listar comentarios de tarea sin comentarios retorna vacio."""
        comentarios = await self.repo.list_by_tarea(self.tarea.id)
        assert len(comentarios) == 0

    async def test_6_1_20_list_by_tarea_tenant_scope(self, db_session: AsyncSession):
        """Comentarios filtran por tenant."""
        otro_tenant = _DEV_TENANT_ID_2
        await _seed_tenant(db_session, otro_tenant)
        await db_session.commit()
        repo_otro = type(self.repo)(db_session, otro_tenant)
        comentarios = await repo_otro.list_by_tarea(self.tarea.id)
        assert len(comentarios) == 0


# ══════════════════════════════════════════════════════════════════════════
# 6.2 Tests de Servicio
# ══════════════════════════════════════════════════════════════════════════


class TestTareaService:
    """6.2: Logica de negocio de tareas."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        await db_session.commit()
        from app.services.tarea_service import TareaService, PERMISO_GESTIONAR
        self.svc = TareaService(
            session=db_session,
            tenant_id=_DEV_TENANT_ID,
            actor_id=self.seed["coord_user_id"],
            roles=[PERMISO_GESTIONAR],
        )

    async def test_6_2_1_crear_tarea(self, db_session: AsyncSession):
        """Crear tarea exitosamente."""
        from app.schemas.tareas import TareaCreate
        datos = TareaCreate(
            asignado_a=self.seed["profe_user_id"],
            descripcion="Tarea de prueba",
            materia_id=self.seed["materia_id"],
        )
        resultado = await self.svc.crear_tarea(datos)
        assert resultado["descripcion"] == "Tarea de prueba"
        assert resultado["estado"] == "Pendiente"
        assert resultado["asignado_a"] == self.seed["profe_user_id"]

    async def test_6_2_2_crear_tarea_sin_materia(self, db_session: AsyncSession):
        """Crear tarea sin materia_id."""
        from app.schemas.tareas import TareaCreate
        datos = TareaCreate(
            asignado_a=self.seed["profe_user_id"],
            descripcion="Tarea institucional",
        )
        resultado = await self.svc.crear_tarea(datos)
        assert resultado["materia_id"] is None
        assert resultado["estado"] == "Pendiente"

    async def test_6_2_3_crear_tarea_asignado_inexistente(self, db_session: AsyncSession):
        """Crear tarea con asignado inexistente lanza BusinessError."""
        from app.core.exceptions import BusinessError
        from app.schemas.tareas import TareaCreate
        datos = TareaCreate(
            asignado_a=uuid4(),
            descripcion="Tarea a nadie",
        )
        with pytest.raises(BusinessError, match="no encontrado en el tenant"):
            await self.svc.crear_tarea(datos)

    async def test_6_2_4_cambiar_estado_pendiente_a_progreso(self, db_session: AsyncSession):
        """Transicion valida: Pendiente → En progreso."""
        tarea = await _crear_tarea_en_seed(
            db_session, self.seed["profe_user_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        resultado = await self.svc.cambiar_estado(tarea.id, "En progreso")
        assert resultado["estado"] == "En progreso"

    async def test_6_2_5_cambiar_estado_progreso_a_resuelta(self, db_session: AsyncSession):
        """Transicion valida: En progreso → Resuelta."""
        tarea = await _crear_tarea_en_seed(
            db_session, self.seed["profe_user_id"], _DEV_TENANT_ID,
            estado=EstadoTarea.EN_PROGRESO,
        )
        await db_session.commit()
        resultado = await self.svc.cambiar_estado(tarea.id, "Resuelta")
        assert resultado["estado"] == "Resuelta"

    async def test_6_2_6_cambiar_estado_invalido_resuelta_a_pendiente(self, db_session: AsyncSession):
        """Transicion invalida: Resuelta → Pendiente lanza BusinessError."""
        from app.core.exceptions import BusinessError
        tarea = await _crear_tarea_en_seed(
            db_session, self.seed["profe_user_id"], _DEV_TENANT_ID,
            estado=EstadoTarea.RESUELTA,
        )
        await db_session.commit()
        with pytest.raises(BusinessError, match="Transicion invalida"):
            await self.svc.cambiar_estado(tarea.id, "Pendiente")

    async def test_6_2_7_cambiar_estado_pendiente_a_cancelada(self, db_session: AsyncSession):
        """Transicion valida: Pendiente → Cancelada."""
        tarea = await _crear_tarea_en_seed(
            db_session, self.seed["profe_user_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        resultado = await self.svc.cambiar_estado(tarea.id, "Cancelada")
        assert resultado["estado"] == "Cancelada"

    async def test_6_2_8_cambiar_estado_inexistente_raise(self, db_session: AsyncSession):
        """Cambiar estado de tarea inexistente lanza BusinessError."""
        from app.core.exceptions import BusinessError
        with pytest.raises(BusinessError, match="no encontrada"):
            await self.svc.cambiar_estado(uuid4(), "En progreso")

    async def test_6_2_9_agregar_comentario(self, db_session: AsyncSession):
        """Agregar comentario a tarea existente."""
        from app.schemas.tareas import ComentarioCreate
        tarea = await _crear_tarea_en_seed(
            db_session, self.seed["profe_user_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        datos = ComentarioCreate(texto="Comentario de prueba")
        resultado = await self.svc.agregar_comentario(tarea.id, datos)
        assert resultado["texto"] == "Comentario de prueba"
        assert resultado["tarea_id"] == tarea.id

    async def test_6_2_10_agregar_comentario_tarea_inexistente(self, db_session: AsyncSession):
        """Agregar comentario a tarea inexistente lanza BusinessError."""
        from app.core.exceptions import BusinessError
        from app.schemas.tareas import ComentarioCreate
        datos = ComentarioCreate(texto="Comentario")
        with pytest.raises(BusinessError, match="no encontrada"):
            await self.svc.agregar_comentario(uuid4(), datos)

    async def test_6_2_11_agregar_comentario_sin_acceso(self, db_session: AsyncSession):
        """Usuario sin acceso no puede comentar."""
        from app.core.exceptions import BusinessError
        from app.schemas.tareas import ComentarioCreate
        from app.services.tarea_service import TareaService

        # Crear tarea asignada a otro usuario
        otro = (await _seed_usuario(db_session, _DEV_TENANT_ID, "PROFESOR", "_otro"))["usuario_id"]
        tarea = await _crear_tarea_en_seed(db_session, otro, _DEV_TENANT_ID)
        await db_session.commit()

        # El svc usa coord_user_id que NO es el asignado y NO tiene tareas:gestionar
        svc_sin_permiso = TareaService(
            session=db_session,
            tenant_id=_DEV_TENANT_ID,
            actor_id=self.seed["tutor_user_id"],
            roles=["TUTOR"],
        )
        datos = ComentarioCreate(texto="Comentario sin acceso")
        with pytest.raises(BusinessError, match="No tienes permiso"):
            await svc_sin_permiso.agregar_comentario(tarea.id, datos)

    async def test_6_2_12_obtener_tarea(self, db_session: AsyncSession):
        """Obtener tarea con comentarios."""
        tarea = await _crear_tarea_en_seed(
            db_session, self.seed["coord_user_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        resultado = await self.svc.obtener_tarea(tarea.id)
        assert resultado["id"] == tarea.id
        assert "comentarios" in resultado

    async def test_6_2_13_obtener_tarea_inexistente(self, db_session: AsyncSession):
        """Obtener tarea inexistente lanza BusinessError."""
        from app.core.exceptions import BusinessError
        with pytest.raises(BusinessError, match="no encontrada"):
            await self.svc.obtener_tarea(uuid4())

    async def test_6_2_14_obtener_tarea_sin_acceso(self, db_session: AsyncSession):
        """Usuario sin acceso no puede ver tarea."""
        from app.core.exceptions import BusinessError
        from app.services.tarea_service import TareaService

        otro = (await _seed_usuario(db_session, _DEV_TENANT_ID, "PROFESOR", "_otro2"))["usuario_id"]
        tarea = await _crear_tarea_en_seed(db_session, otro, _DEV_TENANT_ID)
        await db_session.commit()

        svc_sin_permiso = TareaService(
            session=db_session,
            tenant_id=_DEV_TENANT_ID,
            actor_id=self.seed["tutor_user_id"],
            roles=["TUTOR"],
        )
        with pytest.raises(BusinessError, match="No tienes permiso"):
            await svc_sin_permiso.obtener_tarea(tarea.id)

    async def test_6_2_15_listar_mias(self, db_session: AsyncSession):
        """Listar tareas asignadas al usuario."""
        tarea = await _crear_tarea_en_seed(
            db_session, self.seed["coord_user_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        resultado = await self.svc.listar_mias()
        assert resultado["total"] >= 1

    async def test_6_2_16_listar_mias_sin_resultados(self, db_session: AsyncSession):
        """Listar mis tareas cuando no hay retorna vacio."""
        from app.services.tarea_service import TareaService
        # Crear svc para un usuario sin tareas
        svc_vacio = TareaService(
            session=db_session,
            tenant_id=_DEV_TENANT_ID,
            actor_id=uuid4(),
            roles=["PROFESOR"],
        )
        resultado = await svc_vacio.listar_mias()
        assert resultado["total"] == 0

    async def test_6_2_17_listar_mias_filtro_estado(self, db_session: AsyncSession):
        """Listar mis tareas con filtro de estado."""
        tarea = await _crear_tarea_en_seed(
            db_session, self.seed["coord_user_id"], _DEV_TENANT_ID,
            estado=EstadoTarea.EN_PROGRESO,
        )
        await db_session.commit()
        resultado = await self.svc.listar_mias(estado="En progreso")
        assert resultado["total"] >= 1
        assert resultado["items"][0]["estado"] == "En progreso"

    async def test_6_2_18_listar_todas(self, db_session: AsyncSession):
        """Listar todas las tareas del tenant."""
        await _crear_tarea_en_seed(
            db_session, self.seed["profe_user_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        resultado = await self.svc.listar_todas()
        assert resultado["total"] >= 1

    async def test_6_2_19_listar_todas_filtros_combinados(self, db_session: AsyncSession):
        """Listar todas con filtros combinados."""
        await _crear_tarea_en_seed(
            db_session, self.seed["profe_user_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        resultado = await self.svc.listar_todas(
            estado="Pendiente",
            asignado_a=self.seed["profe_user_id"],
        )
        assert resultado["total"] >= 1
        assert resultado["items"][0]["asignado_a"] == self.seed["profe_user_id"]

    async def test_6_2_20_listar_todas_busqueda(self, db_session: AsyncSession):
        """Listar todas con busqueda textual."""
        await _crear_tarea_en_seed(
            db_session, self.seed["profe_user_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        resultado = await self.svc.listar_todas(busqueda="prueba")
        assert resultado["total"] >= 1

    async def test_6_2_21_audit_log_crear(self, db_session: AsyncSession):
        """Crear tarea genera audit log TAREA_CREAR."""
        from sqlalchemy import select as sa_select
        from app.schemas.tareas import TareaCreate
        datos = TareaCreate(
            asignado_a=self.seed["profe_user_id"],
            descripcion="Tarea auditada",
        )
        await self.svc.crear_tarea(datos)

        stmt = sa_select(AuditLog).where(AuditLog.accion == "TAREA_CREAR")
        logs = (await db_session.scalars(stmt)).all()
        assert len(logs) >= 1

    async def test_6_2_22_audit_log_cambio_estado(self, db_session: AsyncSession):
        """Cambiar estado genera audit log TAREA_ESTADO_CAMBIAR."""
        from sqlalchemy import select as sa_select
        tarea = await _crear_tarea_en_seed(
            db_session, self.seed["profe_user_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        await self.svc.cambiar_estado(tarea.id, "En progreso")

        stmt = sa_select(AuditLog).where(AuditLog.accion == "TAREA_ESTADO_CAMBIAR")
        logs = (await db_session.scalars(stmt)).all()
        assert len(logs) >= 1

    async def test_6_2_23_audit_log_comentario(self, db_session: AsyncSession):
        """Agregar comentario genera audit log TAREA_COMENTARIO."""
        from sqlalchemy import select as sa_select
        from app.schemas.tareas import ComentarioCreate
        tarea = await _crear_tarea_en_seed(
            db_session, self.seed["profe_user_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        datos = ComentarioCreate(texto="Comentario auditado")
        await self.svc.agregar_comentario(tarea.id, datos)

        stmt = sa_select(AuditLog).where(AuditLog.accion == "TAREA_COMENTARIO")
        logs = (await db_session.scalars(stmt)).all()
        assert len(logs) >= 1


# ══════════════════════════════════════════════════════════════════════════
# 6.3 Tests de Router
# ══════════════════════════════════════════════════════════════════════════


class TestTareaRouter:
    """6.3: Endpoints REST con auth, permisos, flujos felices y errores."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        await db_session.commit()

    # ── POST /api/tareas ──────────────────────────────────────────────

    async def test_6_3_1_crear_tarea_201(self, client: AsyncClient):
        """POST /api/tareas -> 201 Created."""
        token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        body = {
            "asignado_a": str(self.seed["profe_user_id"]),
            "descripcion": "Tarea HTTP test",
            "materia_id": str(self.seed["materia_id"]),
        }
        resp = await client.post(
            "/api/tareas", json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["descripcion"] == "Tarea HTTP test"
        assert data["estado"] == "Pendiente"

    async def test_6_3_2_crear_tarea_403_sin_permiso(self, client: AsyncClient):
        """POST sin tareas:gestionar -> 403."""
        token = _make_token(self.seed["tutor_user_id"], _DEV_TENANT_ID, ["TUTOR"])
        body = {
            "asignado_a": str(self.seed["profe_user_id"]),
            "descripcion": "Sin permiso",
        }
        resp = await client.post(
            "/api/tareas", json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403, resp.text

    # ── GET /api/tareas/mias ──────────────────────────────────────────

    async def test_6_3_3_listar_mias(self, client: AsyncClient):
        """GET /api/tareas/mias -> timeline del usuario."""
        token = _make_token(self.seed["profe_user_id"], _DEV_TENANT_ID, ["PROFESOR"])
        # Crear tarea asignada al profesor via HTTP
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        await client.post(
            "/api/tareas",
            json={
                "asignado_a": str(self.seed["profe_user_id"]),
                "descripcion": "Tarea para mi timeline",
            },
            headers={"Authorization": f"Bearer {coord_token}"},
        )
        resp = await client.get(
            "/api/tareas/mias",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] >= 1
        assert "items" in data

    async def test_6_3_4_listar_mias_sin_auth(self, client: AsyncClient):
        """GET /api/tareas/mias sin auth -> 401."""
        resp = await client.get("/api/tareas/mias")
        assert resp.status_code == 401, resp.text

    async def test_6_3_5_listar_mias_filtro_estado(self, client: AsyncClient):
        """GET /api/tareas/mias?estado=Pendiente -> filtrado."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        profe_token = _make_token(self.seed["profe_user_id"], _DEV_TENANT_ID, ["PROFESOR"])
        await client.post(
            "/api/tareas",
            json={
                "asignado_a": str(self.seed["profe_user_id"]),
                "descripcion": "Tarea pendiente",
            },
            headers={"Authorization": f"Bearer {coord_token}"},
        )
        resp = await client.get(
            "/api/tareas/mias?estado=Pendiente",
            headers={"Authorization": f"Bearer {profe_token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["estado"] == "Pendiente"

    # ── GET /api/tareas (admin) ───────────────────────────────────────

    async def test_6_3_6_listar_todas(self, client: AsyncClient):
        """GET /api/tareas -> lista admin."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.get(
            "/api/tareas",
            headers={"Authorization": f"Bearer {coord_token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_6_3_7_listar_todas_403_sin_permiso(self, client: AsyncClient):
        """GET /api/tareas sin tareas:gestionar -> 403."""
        token = _make_token(self.seed["tutor_user_id"], _DEV_TENANT_ID, ["TUTOR"])
        resp = await client.get(
            "/api/tareas",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403, resp.text

    async def test_6_3_8_listar_todas_filtro_busqueda(self, client: AsyncClient):
        """GET /api/tareas?busqueda=... -> filtrado."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        await client.post(
            "/api/tareas",
            json={
                "asignado_a": str(self.seed["profe_user_id"]),
                "descripcion": "Tarea urgente",
            },
            headers={"Authorization": f"Bearer {coord_token}"},
        )
        resp = await client.get(
            "/api/tareas?busqueda=urgente",
            headers={"Authorization": f"Bearer {coord_token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] >= 1

    # ── GET /api/tareas/{id} ──────────────────────────────────────────

    async def test_6_3_9_obtener_tarea(self, client: AsyncClient):
        """GET /api/tareas/{id} -> detalle."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        created = (await client.post(
            "/api/tareas",
            json={
                "asignado_a": str(self.seed["profe_user_id"]),
                "descripcion": "Tarea detalle",
            },
            headers={"Authorization": f"Bearer {coord_token}"},
        )).json()

        profe_token = _make_token(self.seed["profe_user_id"], _DEV_TENANT_ID, ["PROFESOR"])
        resp = await client.get(
            f"/api/tareas/{created['id']}",
            headers={"Authorization": f"Bearer {profe_token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["id"] == created["id"]
        assert "comentarios" in resp.json()

    async def test_6_3_10_obtener_tarea_404(self, client: AsyncClient):
        """GET /api/tareas/{id} inexistente -> 404."""
        token = _make_token(self.seed["profe_user_id"], _DEV_TENANT_ID, ["PROFESOR"])
        resp = await client.get(
            f"/api/tareas/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404, resp.text

    # ── PATCH /api/tareas/{id}/estado ─────────────────────────────────

    async def test_6_3_11_cambiar_estado(self, client: AsyncClient):
        """PATCH /api/tareas/{id}/estado -> 200."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        created = (await client.post(
            "/api/tareas",
            json={
                "asignado_a": str(self.seed["profe_user_id"]),
                "descripcion": "Tarea cambio estado",
            },
            headers={"Authorization": f"Bearer {coord_token}"},
        )).json()

        profe_token = _make_token(self.seed["profe_user_id"], _DEV_TENANT_ID, ["PROFESOR"])
        resp = await client.patch(
            f"/api/tareas/{created['id']}/estado",
            json={"nuevo_estado": "En progreso"},
            headers={"Authorization": f"Bearer {profe_token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["estado"] == "En progreso"

    async def test_6_3_12_cambiar_estado_invalido_422(self, client: AsyncClient):
        """PATCH estado con transicion invalida -> 422."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        created = (await client.post(
            "/api/tareas",
            json={
                "asignado_a": str(self.seed["profe_user_id"]),
                "descripcion": "Tarea estado invalido",
            },
            headers={"Authorization": f"Bearer {coord_token}"},
        )).json()

        profe_token = _make_token(self.seed["profe_user_id"], _DEV_TENANT_ID, ["PROFESOR"])
        # Primero cambiar a En progreso
        await client.patch(
            f"/api/tareas/{created['id']}/estado",
            json={"nuevo_estado": "En progreso"},
            headers={"Authorization": f"Bearer {profe_token}"},
        )
        # Cambiar a Resuelta
        resp = await client.patch(
            f"/api/tareas/{created['id']}/estado",
            json={"nuevo_estado": "Resuelta"},
            headers={"Authorization": f"Bearer {profe_token}"},
        )
        assert resp.status_code == 200, resp.text
        # Ahora intentar Resuelta -> Pendiente (invalido)
        resp2 = await client.patch(
            f"/api/tareas/{created['id']}/estado",
            json={"nuevo_estado": "Pendiente"},
            headers={"Authorization": f"Bearer {profe_token}"},
        )
        assert resp2.status_code == 422, resp2.text

    async def test_6_3_13_cambiar_estado_404(self, client: AsyncClient):
        """PATCH estado de tarea inexistente -> 404."""
        token = _make_token(self.seed["profe_user_id"], _DEV_TENANT_ID, ["PROFESOR"])
        resp = await client.patch(
            f"/api/tareas/{uuid4()}/estado",
            json={"nuevo_estado": "En progreso"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404, resp.text

    # ── POST /api/tareas/{id}/comentarios ─────────────────────────────

    async def test_6_3_14_agregar_comentario_201(self, client: AsyncClient):
        """POST /api/tareas/{id}/comentarios -> 201."""
        coord_token = _make_token(self.seed["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        created = (await client.post(
            "/api/tareas",
            json={
                "asignado_a": str(self.seed["profe_user_id"]),
                "descripcion": "Tarea con comentario",
            },
            headers={"Authorization": f"Bearer {coord_token}"},
        )).json()

        profe_token = _make_token(self.seed["profe_user_id"], _DEV_TENANT_ID, ["PROFESOR"])
        resp = await client.post(
            f"/api/tareas/{created['id']}/comentarios",
            json={"texto": "Comentario HTTP test"},
            headers={"Authorization": f"Bearer {profe_token}"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["texto"] == "Comentario HTTP test"

    async def test_6_3_15_agregar_comentario_404(self, client: AsyncClient):
        """POST comentario a tarea inexistente -> 404."""
        token = _make_token(self.seed["profe_user_id"], _DEV_TENANT_ID, ["PROFESOR"])
        resp = await client.post(
            f"/api/tareas/{uuid4()}/comentarios",
            json={"texto": "Comentario a nadie"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404, resp.text


# ══════════════════════════════════════════════════════════════════════════
# 6.4 Timeline personal
# ══════════════════════════════════════════════════════════════════════════


class TestTimelineTareas:
    """6.4: Timeline personal filtra correctamente."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        self.seed = await _build_full_seed(db_session)
        # Crear tarea para coord
        tarea_coord = await _crear_tarea_en_seed(
            db_session, self.seed["coord_user_id"], _DEV_TENANT_ID,
        )
        # Crear tarea para profe
        tarea_profe = await _crear_tarea_en_seed(
            db_session, self.seed["profe_user_id"], _DEV_TENANT_ID,
        )
        await db_session.commit()
        self.tarea_coord_id = tarea_coord.id
        self.tarea_profe_id = tarea_profe.id

    async def test_6_4_1_usuario_ve_solo_sus_tareas(self, db_session: AsyncSession):
        """Usuario ve solo tareas asignadas a el."""
        from app.services.tarea_service import TareaService
        svc = TareaService(
            session=db_session,
            tenant_id=_DEV_TENANT_ID,
            actor_id=self.seed["coord_user_id"],
            roles=["COORDINADOR"],
        )
        resultado = await svc.listar_mias()
        assert resultado["total"] >= 1
        for item in resultado["items"]:
            assert item["asignado_a"] == self.seed["coord_user_id"]

    async def test_6_4_2_otro_usuario_no_ve_tareas_ajenas(self, db_session: AsyncSession):
        """Otro usuario no ve tareas de otro."""
        from app.services.tarea_service import TareaService
        svc = TareaService(
            session=db_session,
            tenant_id=_DEV_TENANT_ID,
            actor_id=self.seed["coord_user_id"],
            roles=["COORDINADOR"],
        )
        resultado = await svc.listar_mias()
        tarea_ids = {item["id"] for item in resultado["items"]}
        assert self.tarea_profe_id not in tarea_ids

    async def test_6_4_3_timeline_vacia(self, db_session: AsyncSession):
        """Usuario sin tareas recibe lista vacia."""
        from app.services.tarea_service import TareaService
        svc = TareaService(
            session=db_session,
            tenant_id=_DEV_TENANT_ID,
            actor_id=uuid4(),
            roles=["PROFESOR"],
        )
        resultado = await svc.listar_mias()
        assert resultado["total"] == 0

    async def test_6_4_4_filtro_por_estado_en_timeline(self, db_session: AsyncSession):
        """Filtrar timeline por estado."""
        from app.services.tarea_service import TareaService
        svc = TareaService(
            session=db_session,
            tenant_id=_DEV_TENANT_ID,
            actor_id=self.seed["coord_user_id"],
            roles=["COORDINADOR"],
        )
        resultado = await svc.listar_mias(estado="Pendiente")
        for item in resultado["items"]:
            assert item["estado"] == "Pendiente"


# ══════════════════════════════════════════════════════════════════════════
# 6.5 Multi-tenant isolation
# ══════════════════════════════════════════════════════════════════════════


class TestMultiTenantTareas:
    """6.5: Aislamiento multi-tenant en tareas."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, db_session: AsyncSession):
        # Tenant 1
        await _seed_tenant(db_session, _DEV_TENANT_ID)
        await _seed_permisos_tareas(db_session, _DEV_TENANT_ID)
        struct1 = await _seed_estructura(db_session, tenant_id=_DEV_TENANT_ID)
        coord1 = await _seed_usuario(db_session, _DEV_TENANT_ID, "COORDINADOR", "_t1")
        profe1 = await _seed_usuario(db_session, _DEV_TENANT_ID, "PROFESOR", "_t1p")
        tarea1 = await _crear_tarea_en_seed(
            db_session, profe1["usuario_id"], _DEV_TENANT_ID, struct1["materia_id"],
        )
        # Tenant 2
        await _seed_tenant(db_session, _DEV_TENANT_ID_2)
        await _seed_permisos_tareas(db_session, _DEV_TENANT_ID_2)
        struct2 = await _seed_estructura(db_session, tenant_id=_DEV_TENANT_ID_2, codigo_sufijo="B")
        coord2 = await _seed_usuario(db_session, _DEV_TENANT_ID_2, "COORDINADOR", "_t2")
        profe2 = await _seed_usuario(db_session, _DEV_TENANT_ID_2, "PROFESOR", "_t2p")
        tarea2 = await _crear_tarea_en_seed(
            db_session, profe2["usuario_id"], _DEV_TENANT_ID_2, struct2["materia_id"],
        )
        await db_session.commit()
        self.tenant1 = {"coord_user_id": coord1["usuario_id"], "tarea_id": tarea1.id}
        self.tenant2 = {"coord_user_id": coord2["usuario_id"], "tarea_id": tarea2.id}

    async def test_6_5_1_tenant1_no_ve_tenant2(self, client: AsyncClient):
        """Tenant 1 no ve tareas del Tenant 2."""
        token = _make_token(self.tenant1["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.get(
            "/api/tareas",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        ids = {item["id"] for item in data["items"]}
        assert str(self.tenant1["tarea_id"]) in ids
        assert str(self.tenant2["tarea_id"]) not in ids

    async def test_6_5_2_tenant2_no_ve_tenant1(self, client: AsyncClient):
        """Tenant 2 no ve tareas del Tenant 1."""
        token = _make_token(self.tenant2["coord_user_id"], _DEV_TENANT_ID_2, ["COORDINADOR"])
        resp = await client.get(
            "/api/tareas",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        ids = {item["id"] for item in data["items"]}
        assert str(self.tenant2["tarea_id"]) in ids
        assert str(self.tenant1["tarea_id"]) not in ids

    async def test_6_5_3_accesso_cross_tenant_404(self, client: AsyncClient):
        """Acceder a tarea de otro tenant retorna 404."""
        token = _make_token(self.tenant1["coord_user_id"], _DEV_TENANT_ID, ["COORDINADOR"])
        resp = await client.get(
            f"/api/tareas/{self.tenant2['tarea_id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404, resp.text
