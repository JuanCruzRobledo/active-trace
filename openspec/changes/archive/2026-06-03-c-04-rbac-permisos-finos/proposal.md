# Proposal: c-04-rbac-permisos-finos

## Problema / Oportunidad

El sistema actual no tiene control de autorización: cualquier usuario autenticado tiene acceso completo a todos los endpoints. Sin un sistema de permisos finos, no es posible escalar a multi-rol (ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS) ni garantizar que un docente solo vea sus propias comisiones, que un administrador pueda gestionar la estructura académica, o que finanzas opere liquidaciones sin acceso a datos de alumnos.

## Solución Propuesta

Implementar un sistema RBAC con permisos finos `modulo:accion` como catálogo administrable (datos, no hardcode):

1. Modelos `Rol`, `Permiso`, `RolPermiso` con herencia de `BaseMixin` (tenant-scoped).
2. Seed de los 7 roles del dominio con su matriz de permisos base (según `03_actores_y_roles.md` §3.3).
3. Dependencia `require_permission("modulo:accion")` que verifica permisos efectivos server-side por request.
4. Resolución lazy de permisos por request (no en el JWT) — unión de roles activos del usuario, acotados por tenant y vigencia de asignación.
5. Migración `003_rol_permiso.py` con datos semilla.

## Alcance

- [x] **Incluir**:
  - Modelos `Rol`, `Permiso`, `RolPermiso` (tenant-scoped, soft delete en Rol)
  - Repositorios `RolRepository`, `PermisoRepository`, `RolPermisoRepository`
  - `PermissionService` para resolución de permisos efectivos por request
  - Dependencia `require_permission(permiso: str)` en `core/dependencies.py`
  - `core/permissions.py` con el catálogo de constantes de permisos
  - Migración `003_rol_permiso.py` con seed de roles + matriz base
  - Tests: usuario sin permiso → 403, unión de roles, permiso `(propio)` vs global
  - Seed data de los 7 roles (ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS) y su matriz de permisos base

- [ ] **Excluir**:
  - Vigencia temporal de asignaciones (se implementa en C-07 usuarios-y-asignaciones)
  - Impersonación (se implementa en C-05 audit-log o posterior)
  - Catálogo administrable vía API (los roles/permisos se seedan; la UI de administración va en C-21+)
  - Cache de permisos (resolución lazy por request es suficiente para MVP)

## Impacto

- **Backend**: Nuevos modelos + repositorios + servicio + dependency + migración
- **DB**: 3 nuevas tablas (`rol`, `permiso`, `rol_permiso`) + datos semilla
- **Docs**: `core/permissions.py` se completa con constantes de permisos del dominio
- **Riesgo**: Rendimiento de resolución de permisos en cada request. Mitigación: la query es simple (3 JOINs con índices), y el set de permisos por usuario es pequeño (<50).
- **Dependencia**: C-03 auth-jwt-2fa (ya completado) — necesita `get_current_user` y `UserContext.roles`
