## ADDED Requirements

### Requirement: Crear fecha académica
El sistema SHALL permitir a usuarios con permiso `estructura:gestionar` crear una fecha académica asociada a una materia y cohorte, con tipo (Parcial | TP | Coloquio | Recuperatorio), número de instancia, período, fecha y título. La combinación `(tenant_id, materia_id, cohorte_id, tipo, numero)` SHALL ser única dentro del tenant.

#### Scenario: Crear fecha con todos los datos
- **WHEN** un COORDINADOR envía POST /api/fechas-academicas con materia_id, cohorte_id, tipo=Parcial, numero=1, periodo="2026-1", fecha y titulo
- **THEN** el sistema crea la fecha, retorna 201 y registra audit log "FECHA_ACADEMICA_CREAR"

#### Scenario: Crear fecha duplicada (mismo tipo y número)
- **WHEN** un COORDINADOR intenta crear una segunda fecha con el mismo materia_id, cohorte_id, tipo y numero
- **THEN** el sistema retorna 409 Conflict por violación de unicidad

#### Scenario: Crear fecha sin permiso
- **WHEN** un TUTOR sin permiso `estructura:gestionar` intenta crear una fecha
- **THEN** el sistema retorna 403 Forbidden

---

### Requirement: Listar fechas académicas con filtros
El sistema SHALL listar fechas académicas con filtros combinables por materia, cohorte, tipo y período. El listado SHALL retornar datos estructurados (sin paginación inicial) ordenados por fecha ascendente.

#### Scenario: Listar fechas sin filtros
- **WHEN** un COORDINADOR consulta GET /api/fechas-academicas
- **THEN** recibe todas las fechas del tenant ordenadas por fecha ASC

#### Scenario: Filtrar por materia y cohorte
- **WHEN** un COORDINADOR consulta GET /api/fechas-academicas?materia_id=X&cohorte_id=Y
- **THEN** recibe solo las fechas de esa materia y cohorte

#### Scenario: Filtrar por período
- **WHEN** un COORDINADOR consulta GET /api/fechas-academicas?periodo=2026-1
- **THEN** recibe solo las fechas del período 2026-1

#### Scenario: Lista vacía
- **WHEN** no existen fechas para los filtros aplicados
- **THEN** recibe una lista vacía

---

### Requirement: Obtener detalle de fecha académica
El sistema SHALL permitir obtener el detalle completo de una fecha académica por su UUID.

#### Scenario: Obtener fecha existente
- **WHEN** un usuario autorizado consulta GET /api/fechas-academicas/{id}
- **THEN** recibe el detalle completo de la fecha

#### Scenario: Fecha inexistente
- **WHEN** un usuario consulta una fecha con UUID inexistente
- **THEN** el sistema retorna 404 Not Found

---

### Requirement: Actualizar fecha académica
El sistema SHALL permitir a usuarios con permiso `estructura:gestionar` actualizar los campos editables de una fecha académica (tipo, numero, periodo, fecha, titulo). La operación SHALL generar un evento de auditoría "FECHA_ACADEMICA_MODIFICAR".

#### Scenario: Actualizar fecha existente
- **WHEN** un COORDINADOR actualiza la fecha de un parcial con PATCH /api/fechas-academicas/{id}
- **THEN** la fecha se actualiza y se registra audit log "FECHA_ACADEMICA_MODIFICAR"

#### Scenario: Actualizar a combinación duplicada
- **WHEN** un COORDINADOR actualiza tipo/numero de una fecha generando duplicado con otra existente
- **THEN** el sistema retorna 409 Conflict

#### Scenario: Actualizar fecha inexistente
- **WHEN** un COORDINADOR intenta actualizar una fecha con UUID inexistente
- **THEN** el sistema retorna 404 Not Found

---

### Requirement: Eliminar fecha académica (soft delete)
El sistema SHALL permitir a usuarios con permiso `estructura:gestionar` eliminar (soft delete) una fecha académica. La fecha eliminada NO SHALL aparecer en listados ni en exportaciones LMS. La operación SHALL generar un evento de auditoría "FECHA_ACADEMICA_ELIMINAR".

#### Scenario: Eliminar fecha existente
- **WHEN** un COORDINADOR elimina una fecha con DELETE /api/fechas-academicas/{id}
- **THEN** la fecha se marca como eliminada (soft delete), no aparece en GET /api/fechas-academicas y se registra audit log "FECHA_ACADEMICA_ELIMINAR"

#### Scenario: Eliminar fecha inexistente
- **WHEN** un COORDINADOR intenta eliminar una fecha con UUID inexistente
- **THEN** el sistema retorna 404 Not Found

---

### Requirement: Exportar fechas para LMS
El sistema SHALL generar un fragmento HTML con las fechas académicas de una materia×cohorte, listo para copiar y pegar en el aula virtual del LMS. El fragmento SHALL incluir una tabla con tipo, número, fecha y título.

#### Scenario: Exportar fechas de materia+cohorte
- **WHEN** un COORDINADOR consulta GET /api/fechas-academicas/lms-export?materia_id=X&cohorte_id=Y
- **THEN** recibe texto plano (Content-Type: text/plain) con una tabla HTML de las fechas registradas

#### Scenario: Exportar sin fechas registradas
- **WHEN** un COORDINADOR consulta el export para una materia+cohorte sin fechas
- **THEN** recibe un fragmento HTML con tabla vacía o mensaje "No hay fechas registradas"

#### Scenario: Exportar sin permiso
- **WHEN** un TUTOR sin permiso `estructura:gestionar` consulta el export
- **THEN** el sistema retorna 403 Forbidden

---

### Requirement: Aislamiento multi-tenant en fechas académicas
Toda operación sobre fechas académicas SHALL respetar el tenant_id del usuario autenticado. Un usuario del tenant A NO SHALL poder ver, modificar ni eliminar fechas del tenant B.

#### Scenario: Fechas aisladas por tenant
- **WHEN** el tenant A y el tenant B tienen fechas registradas
- **THEN** cada usuario ve solo las fechas de su tenant

#### Scenario: Acceso cross-tenant denegado
- **WHEN** un usuario del tenant A intenta acceder a una fecha del tenant B
- **THEN** el sistema retorna 404 (recurso inexistente)
