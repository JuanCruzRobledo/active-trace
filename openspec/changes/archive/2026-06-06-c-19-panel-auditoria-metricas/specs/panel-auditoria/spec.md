## ADDED Requirements

### Requirement: Acciones por día (F9.1)

El sistema SHALL exponer un endpoint GET que retorne la cantidad de acciones registradas en `AuditLog`, agregadas por día, para un rango de fechas opcional.

#### Scenario: Acciones por día sin filtros
- **WHEN** se consulta acciones por día sin filtros
- **THEN** retorna la serie temporal completa del tenant actual, ordenada por fecha ascendente, con `{fecha: string, total: int}` por cada día con al menos un registro

#### Scenario: Acciones por día con filtro de fechas
- **WHEN** se consulta acciones por día con `fecha_desde` y `fecha_hasta`
- **THEN** retorna solo los registros dentro del rango especificado

#### Scenario: Acciones por día con filtro de materia
- **WHEN** se consulta acciones por día con `materia_id`
- **THEN** retorna solo los registros de esa materia

### Requirement: Estado de comunicaciones por docente (F9.1)

El sistema SHALL exponer un endpoint GET que retorne la distribución de estados de `Comunicacion` agrupada por docente, con opción de filtrar por materia y rango de fechas.

#### Scenario: Comunicaciones por docente sin filtros
- **WHEN** se consulta estado de comunicaciones por docente sin filtros
- **THEN** retorna una lista de docentes con `{usuario_id, nombre, Pendiente: N, Enviando: N, OK: N, Fallido: N, Cancelado: N}` para todo el tenant

#### Scenario: Comunicaciones por docente filtrado por materia
- **WHEN** se consulta comunicaciones por docente con `materia_id`
- **THEN** retorna solo las comunicaciones de esa materia

#### Scenario: Comunicaciones por docente filtrado por fechas
- **WHEN** se consulta comunicaciones por docente con `fecha_desde` y `fecha_hasta`
- **THEN** retorna solo las comunicaciones dentro del rango

### Requirement: Interacciones por docente y materia (F9.1)

El sistema SHALL exponer un endpoint GET que retorne métricas de uso (`AuditLog`) agrupadas por docente y materia, detallando cantidad de acciones por tipo.

#### Scenario: Interacciones sin filtros
- **WHEN** se consulta interacciones por docente y materia sin filtros
- **THEN** retorna `{usuario_id, nombre, materia_id, materia_nombre, acciones: {CALIFICACIONES_IMPORTAR: N, COMUNICACION_ENVIAR: N, ...}, total: int}` para el tenant actual

#### Scenario: Interacciones filtrado por fechas
- **WHEN** se consulta interacciones con rango de fechas
- **THEN** retorna solo las interacciones dentro del rango

### Requirement: Log de últimas acciones configurable (F9.1)

El sistema SHALL exponer un endpoint GET que retorne los N registros más recientes del `AuditLog`, con N configurable por query param (defecto 200, máximo 1000).

#### Scenario: Últimas acciones con límite por defecto
- **WHEN** se consulta últimas acciones sin especificar `limit`
- **THEN** retorna los 200 registros más recientes del tenant

#### Scenario: Últimas acciones con límite explícito
- **WHEN** se consulta últimas acciones con `limit=50`
- **THEN** retorna los 50 registros más recientes

#### Scenario: Límite máximo respetado
- **WHEN** se consulta últimas acciones con `limit=2000`
- **THEN** retorna como máximo 1000 registros (techo duro)

### Requirement: Log completo de auditoría con filtros (F9.2)

El sistema SHALL exponer un endpoint GET para consultar el log completo de auditoría con filtros combinables y paginación. Solo accesible por ADMIN.

#### Scenario: Log completo sin filtros
- **WHEN** ADMIN consulta el log sin filtros
- **THEN** retorna los registros paginados (defecto 50 por página), ordenados por `fecha_hora DESC`, con `{id, fecha_hora, actor_id, actor_nombre, materia_id, materia_nombre, accion, detalle, filas_afectadas, ip, user_agent}` y metadatos de paginación `{total, offset, limit}`

#### Scenario: Log filtrado por rango de fechas
- **WHEN** ADMIN consulta el log con `fecha_desde` y `fecha_hasta`
- **THEN** retorna solo registros dentro del rango

#### Scenario: Log filtrado por usuario
- **WHEN** ADMIN consulta el log con `usuario_id`
- **THEN** retorna solo registros de ese actor

#### Scenario: Log filtrado por materia
- **WHEN** ADMIN consulta el log con `materia_id`
- **THEN** retorna solo registros de esa materia

#### Scenario: Log filtrado por código de acción
- **WHEN** ADMIN consulta el log con `accion=CALIFICACIONES_IMPORTAR`
- **THEN** retorna solo registros con ese código de acción

#### Scenario: Filtros combinados
- **WHEN** ADMIN consulta el log con múltiples filtros simultáneos (fechas + materia + usuario)
- **THEN** retorna solo registros que cumplen TODAS las condiciones

#### Scenario: Paginación explícita
- **WHEN** ADMIN consulta el log con `offset=100&limit=25`
- **THEN** retorna los registros 101-125

#### Scenario: Acceso denegado a COORDINADOR
- **WHEN** COORDINADOR intenta acceder al log completo de auditoría (F9.2)
- **THEN** retorna 403 Forbidden

### Requirement: Scope propio para COORDINADOR

El sistema SHALL restringir las consultas del panel de interacciones (F9.1) según el rol: ADMIN ve todo el tenant, COORDINADOR ve solo datos de materias donde tiene asignaciones activas.

#### Scenario: ADMIN ve todo el tenant
- **WHEN** ADMIN consulta cualquier endpoint de F9.1
- **THEN** los resultados incluyen datos de todas las materias del tenant

#### Scenario: COORDINADOR ve solo sus materias
- **WHEN** COORDINADOR consulta acciones por día
- **THEN** los resultados incluyen solo acciones de materias donde el coordinador tiene asignación activa con rol COORDINADOR

#### Scenario: FINANZAS accede al panel
- **WHEN** FINANZAS consulta cualquier endpoint de F9.1
- **THEN** retorna 403 Forbidden (FINANZAS no tiene permiso `auditoria:ver`)
