## Context

El proyecto ya cuenta con:
- **C-05 audit-log**: modelo `AuditLog` con repositorio (registro, listado, conteo), append-only enforcement, whitelist de códigos de acción, y filtros por actor/acción/materia/rango de fechas.
- **C-04 rbac**: permisos finos con guard `require_permission(...)`. El permiso `auditoria:ver` ya existe en la matriz pero no tiene endpoints asignados.
- **C-07 usuarios**: modelos de usuario con asignaciones a materias (necesario para scope `(propio)` de COORDINADOR).
- **C-12 comunicaciones**: modelo `Comunicacion` con estados (Pendiente/Enviando/OK/Fallido/Cancelado).

No se requieren nuevos modelos ni migraciones. Todo el change es de solo lectura sobre datos existentes.

## Goals / Non-Goals

**Goals:**
- Exponer 4-5 endpoints GET de solo lectura para el panel de interacciones (F9.1).
- Exponer 1 endpoint GET paginado para el log completo de auditoría (F9.2).
- Implementar scope `(propio)` para COORDINADOR: filtro automático por materias donde tiene asignaciones activas.
- Un nuevo `AuditoriaService` con lógica de agregaciones y consultas.
- Tests de integración con cobertura de filtros, agregaciones, paginación y permisos.

**Non-Goals:**
- No se crean nuevos modelos ni tablas.
- No se modifican los modelos `AuditLog` ni `Comunicacion` existentes.
- No se implementan dashboards frontend (es solo API).
- No se agregan nuevos códigos de acción a la whitelist de auditoría (se reusan los existentes).

## Decisions

### 1. Arquitectura: nuevo servicio AuditoriaService + router independiente

- **Decisión**: Crear `backend/app/services/auditoria_service.py` y `backend/app/api/v1/routers/auditoria.py`.
- **Rationale**: El panel de auditoría cruza dos fuentes de datos (`AuditLog` y `Comunicacion`) con lógica de agregación que no pertenece a ningún repositorio existente. Un servicio dedicado mantiene la separación de responsabilidades.
- **Alternativa considerada**: Extender `AuditLogRepository` con métodos de agregación. Se descartó porque mezcla responsabilidades (CRUD vs reporting) y porque necesitamos consultar `Comunicacion`.

### 2. Agregaciones en SQL (no en Python)

- **Decisión**: Las agregaciones (acciones por día, interacciones por docente×materia, estado de comunicaciones) se realizan con consultas SQLAlchemy `func.count()`, `func.date_trunc()`, y `GROUP BY`.
- **Rationale**: Las agregaciones en SQL son órdenes de magnitud más eficientes que traer todos los registros y agrupar en Python. PostgreSQL maneja agrupaciones de millones de registros sin problema.
- **Alternativa considerada**: Agregar en Python post-query. Se descartó por performance con volúmenes reales.

### 3. Límite configurable con techo duro

- **Decisión**: El endpoint de últimas acciones acepta `limit` (query param, defecto 200, máximo 1000).
- **Rationale**: El usuario necesita control sobre cuántos registros ver, pero un máximo evita consultas accidentalmente masivas.
- **Alternativa considerada**: Límite fijo de 200. Se descartó porque F9.1 explícitamente pide "máximo configurable".

### 4. Scope propio vía subquery de asignaciones

- **Decisión**: Para el scope `(propio)` del COORDINADOR, se obtienen los `materia_id` donde el usuario tiene asignación activa como COORDINADOR y se inyecta como filtro adicional en las queries.
- **Rationale**: Es consistente con el patrón usado en otros módulos (C-08 equipos docentes). No requiere un repositorio especial — se consulta `AsignacionRepository` directamente.
- **Alternativa considerada**: Filtro en código post-query. Se descartó porque filtra en SQL es más eficiente y evita traer datos no autorizados.

### 5. Endpoints específicos vs un solo endpoint genérico

- **Decisión**: Endpoints separados por cada sub-vista de F9.1.
- **Rationale**: Cada sub-vista tiene una estructura de respuesta diferente y filtros específicos. Unificarlas en un solo endpoint genérico complejizaría el contrato API sin beneficio real.
- **Alternativa considerada**: Un solo `GET /api/auditoria/panel` con query param `vista=acciones-por-dia|comunicaciones|interacciones|ultimas`. Se descartó por tener diferentes schemas de respuesta y filtros.

## Endpoints API

```
GET  /api/auditoria/acciones-por-dia
     Query: ?fecha_desde=2026-01-01&fecha_hasta=2026-06-30&materia_id=uuid
     Response: [{fecha: "2026-06-01", total: 42}, ...]

GET  /api/auditoria/comunicaciones-por-docente
     Query: ?materia_id=uuid&fecha_desde=2026-01-01&fecha_hasta=2026-06-30
     Response: [{usuario_id: uuid, nombre: string, Pendiente: int, Enviando: int, OK: int, Fallido: int, Cancelado: int}, ...]

GET  /api/auditoria/interacciones-por-docente-materia
     Query: ?fecha_desde=2026-01-01&fecha_hasta=2026-06-30
     Response: [{usuario_id: uuid, nombre: string, materia_id: uuid, materia_nombre: string, acciones: {CODIGO: int}, total: int}, ...]

GET  /api/auditoria/ultimas-acciones
     Query: ?limit=200 (default: 200, max: 1000)
     Response: [{id: uuid, fecha_hora: datetime, actor_nombre: string, accion: string, materia_nombre: string|null, detalle: json, ip: string}, ...]

GET  /api/auditoria/log
     Query: ?fecha_desde=&fecha_hasta=&materia_id=&usuario_id=&accion=&offset=0&limit=50
     Response: {items: [...], total: int, offset: int, limit: int}
     Guard: solo ADMIN
```

## Riesgos / Trade-offs

- **[Rendimiento]** Las agregaciones sobre `AuditLog` pueden ser lentas con millones de registros.
  - **Mitigación**: Los filtros por rango de fechas son obligatorios para el log completo (F9.2). Para las agregaciones, se recomienda indexar `(tenant_id, fecha_hora)` y `(tenant_id, actor_id)`.
- **[Scope propio]** La subquery de asignaciones agrega complejidad a cada consulta para COORDINADOR.
  - **Mitigación**: Es un filtro adicional en el WHERE, no un join costoso. El índice en `asignacion(tenant_id, usuario_id, materia_id)` lo cubre.
- **[Datos sensibles]** El log completo expone IPs y user-agents de todos los usuarios.
  - **Mitigación**: Solo ADMIN puede acceder a F9.2. F9.1 (panel de interacciones) no expone IP ni user-agent.
