# Tasks: c-04-rbac-permisos-finos

## Governance
- **Nivel**: CRITICO (auth/RBAC)
- **Antes de escribir código**: leer `03_actores_y_roles.md` §3 (matriz de permisos) y `docs/ARQUITECTURA.md` §5.2

## Implementation Checklist

### Fase 1: Modelos
- [ ] 1.1 Crear modelo `Rol` en `backend/app/models/rol.py`
  - Hereda `BaseMixin` (id, tenant_id, created_at, updated_at, deleted_at)
  - Campos: `codigo: VARCHAR(50)`, `nombre: VARCHAR(100)`, `descripcion: TEXT(nullable)`
  - Constraints: `UNIQUE(tenant_id, codigo)`, `UNIQUE(tenant_id, nombre)`
  - `__table_args__` con índices propios (pisa los del mixin si necesario)
  - Soft delete heredado de BaseMixin

- [ ] 1.2 Crear modelo `Permiso` en `backend/app/models/permiso.py`
  - NO hereda BaseMixin (es global, no tiene tenant_id ni soft delete)
  - Campos: `id: UUID(pk)`, `codigo: VARCHAR(100)`, `descripcion: VARCHAR(255)`, `created_at: DateTime(tz)`
  - Constraints: `UNIQUE(codigo)`

- [ ] 1.3 Crear modelo `RolPermiso` en `backend/app/models/rol_permiso.py`
  - NO hereda BaseMixin (no tiene updated_at ni deleted_at)
  - Campos: `id: UUID(pk)`, `tenant_id: UUID(fk, not null)`, `rol_id: UUID(fk, not null)`, `permiso_id: UUID(fk, not null)`, `created_at: DateTime(tz)`
  - Constraints: `UNIQUE(tenant_id, rol_id, permiso_id)`
  - FK: `rol_id → rol.id ON DELETE CASCADE`, `permiso_id → permiso.id ON DELETE CASCADE`

### Fase 2: Catálogo de Permisos
- [ ] 2.1 Completar `backend/app/core/permissions.py` con constantes de permisos del dominio
  - Estructura: `PERM_VER_ESTADO_ACADEMICO = "ver_estado_academico"`, etc.
  - Cada permiso del catálogo de `03_actores_y_roles.md` §3.3
  - También definir `PERMISOS_CATALOGO: list[dict]` para usar en seed (código + descripción)

### Fase 3: Repositorios
- [ ] 3.1 Crear `RolRepository` en `backend/app/repositories/rol_repository.py`
  - Hereda `BaseRepository[Rol]`
  - Métodos:
    - `get_by_codigo(codigo: str) -> Rol | None` (scoped)
    - `get_by_codigos(codigos: list[str]) -> list[Rol]` (scoped, bulk)

- [ ] 3.2 Crear `PermisoRepository` en `backend/app/repositories/permiso_repository.py`
  - Hereda `BaseRepository[Permiso]`
  - Métodos:
    - `get_by_codigo(codigo: str) -> Permiso | None`
    - `get_all() -> list[Permiso]`

- [ ] 3.3 Crear `RolPermisoRepository` en `backend/app/repositories/rol_permiso_repository.py`
  - Hereda `BaseRepository[RolPermiso]`
  - Métodos:
    - `get_permisos_by_rol(rol_id: UUID) -> list[RolPermiso]`
    - `get_codigos_by_roles(rol_ids: list[UUID]) -> list[str]` — JOIN con permiso, retorna lista de códigos
    - `get_roles_by_permiso(permiso_id: UUID) -> list[RolPermiso]`

### Fase 4: PermissionService
- [ ] 4.1 Crear `PermissionService` en `backend/app/services/permission_service.py`
  - Constructor: `(rol_repo: RolRepository, permiso_repo: PermisoRepository, rol_permiso_repo: RolPermisoRepository, tenant_id: UUID)`
  - Método `get_effective_permissions(roles: list[str]) -> set[str]`:
    1. Busca roles por código (get_by_codigos)
    2. Obtiene permisos de esos roles (get_codigos_by_roles)
    3. Retorna `set[str]` de códigos de permiso
  - Método `has_permission(roles: list[str], permiso_requerido: str) -> bool`:
    - LLama a `get_effective_permissions` y verifica membresía
  - Método `get_effective_permissions_with_names(roles: list[str]) -> list[dict]`:
    - Para response de `GET /me` — retorna lista de códigos y descripciones

### Fase 5: Dependencia require_permission
- [ ] 5.1 Agregar `require_permission(permiso: str)` dependency en `backend/app/core/dependencies.py`
  - Factory function que retorna una dependencia FastAPI
  - Internamente:
    1. Obtiene `current_user: UserContext = Depends(get_current_user)`
    2. Obtiene `db: AsyncSession = Depends(get_db)`
    3. Construye PermissionService con repositorios
    4. Verifica `has_permission(current_user.roles, permiso)`
    5. Si False → `HTTPException(403, "Permission denied")`
  - Firma de uso: `require_permission("calificaciones:importar")`

- [ ] 5.2 Extender `GET /api/auth/me` para incluir permisos efectivos
  - Modificar `UserMeResponse` schema → agregar campo `permisos: list[str]`
  - Modificar handler de `/me` → inyectar `PermissionService` y llamar `get_effective_permissions(current_user.roles)`

### Fase 6: Migración
- [ ] 6.1 Crear migración `backend/alembic/versions/003_rol_permiso.py`
  - `upgrade()`:
    - Crear tabla `permiso` (global, sin tenant_id)
    - Crear tabla `rol` (con tenant_id, soft delete)
    - Crear tabla `rol_permiso` (con tenant_id, FK a rol y permiso)
    - Insertar catálogo de permisos (~27)
    - Insertar 7 roles para tenant dev
    - Insertar matriz rol × permiso (~80+ filas)
  - `downgrade()`:
    - Drop tabla `rol_permiso`
    - Drop tabla `rol`
    - Drop tabla `permiso`
  - Usar `sa.func.now()` para timestamps en seed
  - Usar `sa.text("gen_random_uuid()")` para UUIDs en seed

### Fase 7: Tests
- [ ] 7.1 Test: PermisoResolvedor — rol único obtiene sus permisos (unit)
  - Crear rol X con 3 permisos → `get_effective_permissions(["X"])` retorna set con esos 3

- [ ] 7.2 Test: PermisoResolvedor — unión de múltiples roles (unit)
  - Crear rol X con permisos [A, B], rol Y con permisos [B, C]
  - `get_effective_permissions(["X", "Y"])` retorna {A, B, C}

- [ ] 7.3 Test: PermisoResolvedor — rol sin permisos retorna vacío (unit)
  - `get_effective_permissions([])` → set() vacío

- [ ] 7.4 Test: require_permission — usuario con permiso → 200 (integration)
  - Endpoint protegido con permiso que el usuario tiene → pasa

- [ ] 7.5 Test: require_permission — usuario sin permiso → 403 (integration)
  - Endpoint protegido con permiso que el usuario NO tiene → 403

- [ ] 7.6 Test: require_permission — usuario autenticado sin roles → 403 (integration)
  - Usuario con `roles=[]` → 403

- [ ] 7.7 Test: require_permission — usuario no autenticado → 401 (integration)
  - Endpoint protegido sin token → 401 (primero pasa por get_current_user)

- [ ] 7.8 Test: GET /me incluye permisos efectivos (integration)
  - Login como PROFESOR → `/me` incluye `permisos` con todos los del rol

- [ ] 7.9 Test: Aislamiento de tenant — tenant A y B no comparten roles (integration)
  - Crear rol "CUSTOM" en tenant A, NO en tenant B
  - Usuario de tenant B no ve ese rol

## Dependencias
- spec: `auth-jwt` (especificación de autenticación — define `get_current_user`, JWT claims, `UserContext.roles`)
- spec: `database-connection` (especificación de conexión a BD)
- design: `c-04-rbac-permisos-finos` (este documento)

## Notas de Implementación
- `require_permission` DEBE ser una factory que retorna una dependencia, NO una dependencia directa
  - Patrón: `def require_permission(permiso: str) -> Callable: ...`
  - Uso: `Depends(require_permission("modulo:accion"))`
- `Permiso` NO tiene `tenant_id` — el catálogo es único para todo el sistema
- `RolPermiso` NO tiene soft delete — la matriz se administra como datos de configuración
- La resolución de permisos usa `UserContext.roles` (del JWT claim `roles`, seteado en login de C-03)
- @TODO (C-07): cuando exista `Asignacion` con vigencia, migrar la resolución de roles desde tabla en vez de JWT
- El seed de migración inserta datos para el tenant dev (`00000000-0000-0000-0000-000000000001`)
- No olvidar importar los modelos en `app/models/__init__.py` para que Alembic los detecte
