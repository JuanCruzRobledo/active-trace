# rbac-finos Specification

## Purpose
Define el sistema de autorización basado en Roles (RBAC) con permisos finos `modulo:accion`, implementado como catálogo administrable en datos (no hardcode). Los permisos se resuelven server-side por request, no se cachean en el JWT. Cada endpoint protegido declara el permiso requerido vía dependency `require_permission`; sin permiso explícito → `403 Forbidden`.

## Requirements

### Requirement: Catálogo de Roles (Rol)

El sistema SHALL exponer un catálogo de roles almacenado en la tabla `rol`. Cada rol SHALL pertenecer a un tenant (`tenant_id`) y SHALL tener un código único por tenant (`codigo`), un nombre legible (`nombre`) y una descripción opcional (`descripcion`). Los roles SHALL soportar soft delete (`deleted_at`). El catálogo SHALL contener los 7 roles del dominio como seed data para el tenant dev: `ALUMNO`, `TUTOR`, `PROFESOR`, `COORDINADOR`, `NEXO`, `ADMIN`, `FINANZAS`.

#### Scenario: Crear rol dentro de un tenant
- **WHEN** el sistema inserta un rol con `tenant_id`, `codigo`, `nombre`
- **THEN** el rol queda registrado y accesible por `codigo` dentro de ese tenant

#### Scenario: Dos tenants tienen roles independientes
- **WHEN** el tenant A crea un rol con `codigo = "CUSTOM"` y el tenant B no
- **THEN** el tenant B NO puede ver ni usar el rol `CUSTOM` del tenant A

#### Scenario: Soft delete de rol no afecta a otros tenants
- **WHEN** un rol se elimina (soft delete) en un tenant
- **THEN** el rol deja de estar activo solo en ese tenant; su `deleted_at` se setea, pero no se afectan registros de otros tenants

### Requirement: Catálogo de Permisos (Permiso)

El sistema SHALL exponer un catálogo global de permisos almacenado en la tabla `permiso`. Cada permiso SHALL tener un código único (`codigo`) con formato `"modulo:accion"` y una descripción. NO SHALL tener `tenant_id` (el catálogo es único para todo el sistema). Los permisos SHALL ser inmutables una vez creados (sin soft delete).

#### Scenario: Crear permiso global
- **WHEN** el sistema inserta un permiso con `codigo = "calificaciones:importar"`
- **THEN** el permiso queda disponible para todos los tenants

#### Scenario: Código de permiso duplicado es rechazado
- **WHEN** se intenta insertar un permiso con un `codigo` que ya existe
- **THEN** la operación falla por violación de `UNIQUE(codigo)`

### Requirement: Matriz Rol → Permiso (RolPermiso)

El sistema SHALL exponer una tabla `rol_permiso` que asigna permisos a roles dentro de un tenant. Cada fila SHALL asociar un `rol_id`, un `permiso_id` y un `tenant_id` con `UNIQUE(tenant_id, rol_id, permiso_id)`. NO SHALL tener soft delete. El sistema SHALL incluir seed data con la matriz de permisos base según `03_actores_y_roles.md` §3.3 para el tenant dev.

#### Scenario: Asignar permiso a rol
- **WHEN** se inserta una fila en `rol_permiso` con `rol_id = X`, `permiso_id = Y`, `tenant_id = T`
- **THEN** el rol X en el tenant T obtiene el permiso Y

#### Scenario: Un mismo permiso en múltiples roles
- **WHEN** el permiso `comunicacion:enviar` se asigna a PROFESOR y COORDINADOR
- **THEN** ambos roles tienen ese permiso; un usuario con ambos roles NO lo duplica

### Requirement: Resolución de permisos efectivos

El sistema SHALL exponer un servicio `PermissionService` que resuelve los permisos efectivos de un usuario a partir de sus códigos de rol (`list[str]`). El servicio SHALL:
1. Buscar los roles por código en el tenant del usuario
2. Obtener los códigos de permiso asociados a esos roles vía `rol_permiso` → `permiso`
3. Retornar la unión como `set[str]`

#### Scenario: Rol único con 3 permisos
- **WHEN** el usuario tiene el rol `PROFESOR` con permisos `[calificaciones:importar, atrasados:ver, comunicacion:enviar]`
- **THEN** `get_effective_permissions(["PROFESOR"])` retorna `{"calificaciones:importar", "atrasados:ver", "comunicacion:enviar"}`

#### Scenario: Unión de múltiples roles
- **WHEN** el usuario tiene los roles `PROFESOR` y `COORDINADOR`
- **THEN** el resultado es la unión de permisos de ambos roles (sin duplicados)

#### Scenario: Rol sin permisos retorna vacío
- **WHEN** el usuario tiene un rol que no tiene ningún permiso asignado
- **THEN** `get_effective_permissions` retorna `set()` vacío

#### Scenario: Roles vacíos retorna vacío
- **WHEN** el usuario no tiene roles (`roles = []`)
- **THEN** `get_effective_permissions([])` retorna `set()` vacío

### Requirement: Dependencia require_permission

El sistema SHALL exponer una dependencia FastAPI `require_permission(permiso: str)` que verifica que el usuario autenticado tenga el permiso requerido. La dependencia SHALL:
1. Resolver `get_current_user` para obtener identidad + roles
2. Resolver `get_db` para obtener sesión de BD
3. Construir `PermissionService` con los repositorios correspondientes
4. Llamar `has_permission(current_user.roles, permiso)` 
5. Si el usuario no tiene el permiso → `HTTPException(403, "Permission denied")`
6. Si el usuario no está autenticado → la pasa a `get_current_user` que responde 401

#### Scenario: Usuario con permiso pasa
- **WHEN** un usuario autenticado con permiso `comunicacion:enviar` accede a un endpoint con `require_permission("comunicacion:enviar")`
- **THEN** la dependencia retorna exitosamente y el endpoint se ejecuta

#### Scenario: Usuario sin permiso recibe 403
- **WHEN** un usuario autenticado SIN permiso `comunicacion:aprobar` accede a un endpoint con `require_permission("comunicacion:aprobar")`
- **THEN** el sistema responde `403 Forbidden` con `{ "detail": "Permission denied" }`

#### Scenario: Usuario no autenticado recibe 401
- **WHEN** un cliente no autenticado accede a un endpoint protegido con `require_permission`
- **THEN** el sistema responde `401 Unauthorized` (primero pasa por `get_current_user`)

#### Scenario: Endpoint sin require_permission es accesible
- **WHEN** un usuario accede a un endpoint que NO declara `require_permission`
- **THEN** el endpoint se ejecuta sin verificación de permisos (el permiso se verifica solo donde se declara)

### Requirement: Permisos en respuesta de GET /me

El sistema SHALL extender el endpoint `GET /api/auth/me` para incluir la lista de permisos efectivos del usuario autenticado en el campo `permisos: list[str]`. Los permisos SHALL resolverse server-side llamando a `PermissionService.get_effective_permissions(current_user.roles)`.

#### Scenario: /me incluye permisos
- **WHEN** el usuario autenticado hace `GET /api/auth/me`
- **THEN** la respuesta incluye `"permisos": ["calificaciones:importar", "atrasados:ver", ...]` con todos los permisos efectivos de sus roles
