# Design: c-04-rbac-permisos-finos

## Arquitectura

### Componentes Principales

| Componente | Responsabilidad |
|------------|----------------|
| `Rol` (modelo) | Entidad rol del dominio: nombre, descripción, tenant-scoped. Soft delete. |
| `Permiso` (modelo) | Catálogo de permisos atómicos `codigo = "modulo:accion"`. Global (no tenant-scoped — el catálogo es único). |
| `RolPermiso` (modelo) | Matriz N:N Rol → Permiso. Tenant-scoped. Cada fila otorga un permiso a un rol dentro de un tenant. |
| `RolRepository` | CRUD de roles scoped por tenant. |
| `PermisoRepository` | CRUD de permisos (global). Método `get_by_codigo(codigo)`. |
| `RolPermisoRepository` | Consulta de permisos por rol: `get_permisos_by_rol(rol_id)`, `get_permisos_by_roles(rol_ids)`. |
| `PermissionService` | Lógica de negocio: resuelve permisos efectivos de un usuario (unión de roles activos, acotados por vigencia). |
| `require_permission` (dependency) | FastAPI dependency que extrae el permiso requerido y verifica contra el servicio. |
| `core/permissions.py` | Catálogo de constantes `PERM_*` para cada permiso del dominio. |

### Patrones de Diseño

- **RBAC (Role-Based Access Control)**: Modelo NIST estándar. Roles agrupan permisos; usuarios tienen roles.
- **Repository**: Abstracción de persistencia con tenant scoping automático (`BaseRepository`).
- **Lazy resolution**: Los permisos se resuelven server-side en cada request, no se cachean en el JWT. Consistencia fuerte.
- **Fail-closed**: Sin permiso explícito → `403 Forbidden`. No existe "default allow".

### Flujo de Resolución de Permisos

```
REQUEST
  │
  ▼
Router: require_permission("comunicacion:enviar")
  │
  ▼
Dependencies: get_current_user() → UserContext(user_id, tenant_id, roles)
  │
  ▼
PermissionService.get_effective_permissions(user_id, tenant_id)
  ├── 1. Obtener roles activos del usuario (desde UserContext.roles)
  │       └── (Nota: en C-04 los roles vienen del JWT — claim `roles` seteado en login.
  │        En C-07 se migrará a resolución desde tabla Asignacion con vigencia.)
  ├── 2. RolRepository.get_roles_by_codigos(codigos, tenant_id)
  │       └── Resuelve IDs de roles desde códigos ("PROFESOR", "COORDINADOR", etc.)
  ├── 3. RolPermisoRepository.get_permisos_by_roles(rol_ids)
  │       └── JOIN rol_permiso + permiso → lista de códigos "modulo:accion"
  └── 4. Retorna Set[str] de permisos efectivos
  │
  ▼
require_permission: verifica si permiso_requerido ∈ permisos_efectivos
  │
  ▼
  ├── True  → next() — ejecuta el endpoint
  └── False → raise HTTPException(403)
```

### Modelo de Datos

#### Entidad: `Rol`

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | UUID | PK, default uuid4 |
| `tenant_id` | UUID | FK a tenant, NOT NULL |
| `codigo` | VARCHAR(50) | `"PROFESOR"`, `"COORDINADOR"`, etc. |
| `nombre` | VARCHAR(100) | Nombre legible |
| `descripcion` | TEXT | Nullable |
| `created_at` | DateTime(tz) | default now() |
| `updated_at` | DateTime(tz) | onupdate now() |
| `deleted_at` | DateTime(tz) | NULL = activo (soft delete) |

**Constraints**: `UNIQUE(tenant_id, codigo)`, `UNIQUE(tenant_id, nombre)`. Índice en `tenant_id`.

#### Entidad: `Permiso`

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | UUID | PK, default uuid4 |
| `codigo` | VARCHAR(100) | `"calificaciones:importar"`, `"comunicacion:enviar"`, etc. |
| `descripcion` | VARCHAR(255) | Explicación del permiso |
| `created_at` | DateTime(tz) | default now() |

**Nota**: `Permiso` NO tiene `tenant_id` porque el catálogo de permisos es global. Tampoco tiene soft delete porque los permisos son inmutables una vez creados. Sin `BaseMixin`.

**Constraints**: `UNIQUE(codigo)`.

#### Entidad: `RolPermiso`

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | UUID | PK, default uuid4 |
| `tenant_id` | UUID | FK a tenant, NOT NULL |
| `rol_id` | UUID | FK a Rol, NOT NULL |
| `permiso_id` | UUID | FK a Permiso, NOT NULL |
| `created_at` | DateTime(tz) | default now() |

**Nota**: `RolPermiso` usa `tenant_id` porque un tenant puede personalizar qué permisos tiene cada rol. NO tiene soft delete (la matriz se administra como datos).

**Constraints**: `UNIQUE(tenant_id, rol_id, permiso_id)`. FK con ON DELETE CASCADE.

#### Seed Data

Los roles y permisos base se insertan en la migración `003_rol_permiso.py`:

**Roles** (7): ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS — insertados para el tenant dev (`tenant.id = "00000000-0000-0000-0000-000000000001"`).

**Permisos** (~27 del catálogo completo, ver `03_actores_y_roles.md` §3.3):

```
ver_estado_academico, reservar_evaluacion, confirmar_avisos,
calificaciones_importar, atrasados_ver, entregas_sin_corregir,
comunicacion_enviar, comunicacion_aprobar, encuentros_gestionar,
guardias_registrar, tareas_gestionar, avisos_publicar,
equipos_asignar, estructura_gestionar, usuarios_gestionar,
auditoria_ver, grilla_salarial_operar, liquidaciones_calcular,
liquidaciones_cerrar, liquidaciones_exportar, liquidaciones_ver,
facturas_gestionar, tenant_configurar, impersonacion_usar
```

**Matriz Rol × Permiso**: según la tabla en `03_actores_y_roles.md` §3.3 — aproximadamente 80+ filas `rol_permiso` cruzando los 7 roles contra los permisos que les corresponden.

### APIs

| Endpoint | Método | Auth | Permiso | Propósito |
|----------|--------|------|---------|-----------|
| `GET /api/auth/me` | GET | Access token | (ninguno — propio perfil) | Retorna `UserMeResponse` con datos del usuario + roles + permisos efectivos |

**Nota**: En C-04 NO se exponen endpoints CRUD para roles/permisos. Eso va en C-21+ (UI de administración) o en changes posteriores. La matriz se administra como seed data y, más adelante, vía API protegida con `tenant_configurar`.

#### Extensión de `GET /api/auth/me`

**Cambio**: El response `UserMeResponse` existente se extiende para incluir `permisos: list[str]` — la lista de permisos efectivos del usuario autenticado.

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "email": "user@example.com",
  "is_active": true,
  "totp_enabled": false,
  "roles": ["PROFESOR"],
  "permisos": ["calificaciones:importar", "atrasados:ver", "comunicacion:enviar", "encuentros:gestionar"]
}
```

### Seguridad

- **Fail-closed**: `require_permission` sin permiso → `403`. No hay "default allow" para ningún endpoint que declare el permiso.
- **Resolución lazy por request**: los permisos no se cachean en el JWT. Si se revoca un permiso, el cambio es inmediato (próximo request).
- **Eficiencia**: la query de resolución son 3 JOINs (user → user_roles → rol_permiso → permiso). Se ejecuta en <5ms con índices.
- **Tenant isolation**: `Rol` y `RolPermiso` tienen `tenant_id`; `Permiso` es global (no hay permisos distintos por tenant, solo la matriz de qué rol tiene qué permiso).

### Consideraciones

| Trade-off | Decisión | Alternativa considerada |
|-----------|----------|------------------------|
| Permisos en JWT vs lazy | **Lazy (server-side)** | JWT con permisos: más rápido pero stale. Descartado porque la regla de negocio dice "nada de permisos en el token" (ARQUITECTURA.md §5.1). |
| Catálogo hardcodeado vs datos | **Datos (seed en migración)** | Hardcode: más simple pero no administrable. Datos permite modificaciones futuras vía API. |
| `Permiso` global vs por tenant | **Global** | No tendría sentido que "calificaciones:importar" sea un permiso en un tenant y otro no. La personalización va en la matriz RolPermiso. |
| Soft delete en RolPermiso | **No** | La matriz es datos de configuración; si se remueve un permiso se borra la fila. No tiene sentido mantener históricos de asignaciones permiso→rol. |

### Estrategia de Cache (futuro)

Si la query de permisos se vuelve un bottleneck (>10ms por request), se puede agregar una cache en memoria (TTL corto, ~30s) invalidada por evento de auditoría. No se implementa en C-04 porque es premature optimization.
