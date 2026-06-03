## Why

El sistema ya cuenta con autenticación (C-03), RBAC (C-04) y estructura académica (C-06), pero no existe una entidad `Usuario` ni un mecanismo para vincular personas a roles dentro de contextos académicos. Sin este cambio no se pueden gestionar docentes, asignar equipos ni operar ningún módulo de negocio que requiera identificar actores del dominio (calificaciones, comunicaciones, encuentros, liquidaciones).

Este change agrega la identidad base del sistema —el `Usuario`— y las `Asignaciones` que vinculan usuarios con roles y contextos académicos (materia, carrera, cohorte), estableciendo el modelo de autorización granular con vigencia temporal y jerarquía.

## What Changes

- **Modelo `Usuario`**: entidad base con PII cifrada (email, dni, cuil, cbu, alias_cbu); legajo como atributo de negocio opcional (no PK, no credencial); soft-delete; partial unique index `(tenant_id, email)`.
- **Modelo `Asignacion`**: vincula Usuario ↔ Rol ↔ contexto académico (materia/carrera/cohorte/comisiones); `responsable_id` para jerarquía; vigencia `desde/hasta`; `estado_vigencia` derivado por fechas.
- **Endpoint ABM de usuarios**: `POST/PUT /api/admin/usuarios`, `GET /api/admin/usuarios`, `DELETE (soft) /api/admin/usuarios` — solo ADMIN.
- **Endpoint CRUD de asignaciones**: `POST/PUT/GET/DELETE /api/asignaciones` — permiso `equipos:asignar` (COORDINADOR, ADMIN).
- **Migración Alembic 005**: tablas `usuario` y `asignacion`.
- **Tests**: PII cifrada no expuesta en logs/respuestas, unicidad email por tenant, vigencia (asignación vencida no autoriza), multi-rol, jerarquía responsable.

## Capabilities

### New Capabilities
- `user-management`: ABM de usuarios con PII cifrada en reposo (AES-256), unicidad de email por tenant con partial unique index para soft-delete, soft-delete, legajo como atributo de negocio opcional.
- `asignaciones`: CRUD de asignaciones vinculando usuario ↔ rol ↔ contexto académico, con vigencia temporal (desde/hasta), estado_vigencia derivado, jerarquía via responsable_id, y partial unique index para soft-delete.

### Modified Capabilities
- `estructura-academica`: la entidad existente `Materia` ahora se referencia desde `Asignacion` como contexto académico opcional.
- `rbac-finos`: se utiliza el permiso `equipos:asignar` (ya definido en la matriz RBAC de C-04) en los endpoints de asignaciones; el permiso `Gestionar usuarios del tenant` (ADMIN) se materializa en los endpoints de usuarios.

## Impact

- **Backend**: nuevos módulos `app/models/usuario.py`, `app/models/asignacion.py`, `app/schemas/usuario.py`, `app/schemas/asignacion.py`, `app/repositories/usuario.py`, `app/repositories/asignacion.py`, `app/services/usuario.py`, `app/services/asignacion.py`, `app/api/v1/routers/usuarios.py`, `app/api/v1/routers/asignaciones.py`.
- **Migraciones**: `alembic/versions/005_usuarios_asignaciones.py`.
- **Seguridad**: EncryptionService (C-02) aplicado a campos PII de Usuario; require_permission en endpoints de asignaciones.
- **Dependencias**: requiere C-06 (estructura académica para FK a Materia/Carrera/Cohorte), C-04 (RBAC para permisos), C-02 (EncryptionService para PII).
