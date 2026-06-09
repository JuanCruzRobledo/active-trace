## Why

Se requiere implementar el catálogo base de la estructura académica (Carreras, Cohortes, Materias) para que la plataforma pueda organizar y agrupar la información educativa por tenant. Este catálogo es la base sobre la cual se vincularán los alumnos, dictados y las calificaciones posteriormente (épica 5, Funcionalidades F5.1 y F5.2).

## What Changes

- Creación de los modelos `Carrera`, `Cohorte`, y `Materia` en la base de datos (PostgreSQL vía Alembic Migración 004).
- Implementación de ABMs (Alta, Baja lógica/edición, lectura) para Carreras, Cohortes y Materias en el área de administración.
- Exposición de endpoints `/api/admin/carreras`, `/api/admin/cohortes` y `/api/admin/materias`.
- Protección de todos estos endpoints con RBAC `require_permission("estructura:gestionar")` que será exclusivo para el rol ADMIN.
- Implementación estricta de aislamiento multi-tenant por fila (`tenant_id`) y validación de unicidad de códigos por tenant.
- Se implementan reglas de negocio como "Carrera inactiva no admite cohortes abiertas".

## Capabilities

### New Capabilities
- `estructura-academica`: Gestión de catálogos de la estructura académica de la institución, incluyendo el mantenimiento (ABM) de Carreras, Cohortes (asociadas a Carreras) y Materias (catálogo único de tenant). No incluye instancias de dictado.

### Modified Capabilities
- Ninguna.

## Impact

- **Base de Datos**: Se agrega la migración 004 con tres tablas nuevas (`carreras`, `cohortes`, `materias`).
- **APIs**: Nuevos routers en `/api/admin/*` para estos recursos.
- **Seguridad / Permisos**: Utilización del framework RBAC existente (C-04) aplicando `"estructura:gestionar"`.
- **Testing**: Se incrementará la cobertura de pruebas de integración y unitarias enfocándose fuertemente en el aislamiento del tenant y validación de unicidad.
