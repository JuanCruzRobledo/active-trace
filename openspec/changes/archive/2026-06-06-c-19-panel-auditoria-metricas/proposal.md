## Why

El sistema ya registra cada acción significativa en `AuditLog` (C-05) y genera comunicaciones trazables (C-12), pero no existe una vista unificada que permita a coordinación y administración supervisar la actividad del equipo docente. Sin métricas de uso ni un panel de auditoría, es imposible detectar docentes inactivos, comunicaciones fallidas o patrones anómalos — lo que reduce el valor de la trazabilidad ya implementada.

## What Changes

- Nuevo **panel de auditoría y métricas** con dos sub-vistas: F9.1 (panel de interacciones) y F9.2 (log completo de auditoría).
- Endpoints de solo lectura bajo `/api/auditoria/*` que consultan `AuditLog` y `Comunicacion` con agregaciones y filtros.
- Nuevo permiso `auditoria:ver` (ya referenciado en C-04 pero sin implementación concreta de endpoints).
- Filtros: rango de fechas, materia, usuario, estado de actividad, código de acción.
- Scope `(propio)` para COORDINADOR: ve solo datos de docentes de sus materias; ADMIN ve todo el tenant.

## Capabilities

### New Capabilities
- `panel-auditoria`: Endpoints de solo lectura para el panel de interacciones del sistema (F9.1) y log completo de auditoría (F9.2) — agregaciones por día/docente/materia, estado de comunicaciones, últimas acciones con límite configurable, log filtrable con paginación.

### Modified Capabilities
- *(ninguna — este change introduce una nueva feature de solo lectura, no modifica requirements existentes)*

## Impact

- **Backend**: nuevo router `api/v1/routers/auditoria.py` con 4-5 endpoints GET de solo lectura. Nuevo servicio `AuditoriaService` con lógica de agregaciones y filtros. No requiere nuevos modelos ni migraciones — todo sobre `AuditLog` (existente) y `Comunicacion` (existente).
- **Permisos**: endpoint guard `auditoria:ver` (ADMIN, COORDINADOR con scope propio, FINANZAS). Sin cambios en el modelo RBAC existente.
- **Tests**: tests de integración para cada endpoint (agregaciones, filtros, scope propio, paginación, límite configurable).
- **Dependencias**: C-05 (audit-log) y C-07 (usuarios) ya completados — el modelo de datos está listo.
