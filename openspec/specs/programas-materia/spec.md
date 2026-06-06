## ADDED Requirements

### Requirement: Subir y asociar programa de materia
El sistema SHALL permitir a usuarios con permiso `estructura:gestionar` subir un programa de materia, asociándolo a una combinación específica de materia × carrera × cohorte. El programa SHALL incluir un título descriptivo y una referencia de archivo (UUID opaco). La combinación `(tenant_id, materia_id, carrera_id, cohorte_id)` SHALL ser única — no pueden existir dos programas activos para la misma materia×carrera×cohorte.

#### Scenario: Subir programa con todos los datos
- **WHEN** un COORDINADOR envía POST /api/programas con materia_id, carrera_id, cohorte_id, titulo y referencia_archivo
- **THEN** el sistema crea el programa, retorna 201 con los datos y registra audit log "PROGRAMA_SUBIR"

#### Scenario: Subir programa duplicado para misma materia×carrera×cohorte
- **WHEN** un COORDINADOR intenta subir un segundo programa para la misma materia×carrera×cohorte
- **THEN** el sistema retorna 409 Conflict por violación de unicidad

#### Scenario: Subir programa sin permiso
- **WHEN** un TUTOR sin permiso `estructura:gestionar` intenta subir un programa
- **THEN** el sistema retorna 403 Forbidden

---

### Requirement: Listar programas de materia
El sistema SHALL listar programas con filtros combinables por materia, carrera y cohorte. La lista SHALL retornar todos los campos del programa excepto la referencia_archivo (que se obtiene por detalle individual).

#### Scenario: Listar programas sin filtros
- **WHEN** un COORDINADOR consulta GET /api/programas
- **THEN** recibe todos los programas del tenant

#### Scenario: Filtrar programas por materia
- **WHEN** un COORDINADOR consulta GET /api/programas?materia_id=X
- **THEN** recibe solo los programas de esa materia

#### Scenario: Lista vacía
- **WHEN** no existen programas para los filtros aplicados
- **THEN** recibe una lista vacía con total = 0

---

### Requirement: Obtener detalle de programa
El sistema SHALL permitir obtener el detalle completo de un programa por su UUID, incluyendo la referencia_archivo.

#### Scenario: Obtener programa existente
- **WHEN** un usuario autorizado consulta GET /api/programas/{id}
- **THEN** recibe el detalle completo incluyendo referencia_archivo

#### Scenario: Programa inexistente
- **WHEN** un usuario consulta un programa con UUID inexistente
- **THEN** el sistema retorna 404 Not Found

---

### Requirement: Eliminar programa
El sistema SHALL permitir a usuarios con permiso `estructura:gestionar` eliminar un programa de materia (hard delete). La operación SHALL generar un evento de auditoría "PROGRAMA_ELIMINAR".

#### Scenario: Eliminar programa existente
- **WHEN** un COORDINADOR elimina un programa con DELETE /api/programas/{id}
- **THEN** el programa se elimina físicamente y se registra audit log "PROGRAMA_ELIMINAR"

#### Scenario: Eliminar programa inexistente
- **WHEN** un COORDINADOR intenta eliminar un programa con UUID inexistente
- **THEN** el sistema retorna 404 Not Found

---

### Requirement: Aislamiento multi-tenant en programas
Toda operación sobre programas SHALL respetar el tenant_id del usuario autenticado. Un usuario del tenant A NO SHALL poder ver, modificar ni eliminar programas del tenant B.

#### Scenario: Programas aislados por tenant
- **WHEN** el tenant A y el tenant B tienen programas registrados
- **THEN** cada usuario ve solo los programas de su tenant

#### Scenario: Acceso cross-tenant denegado
- **WHEN** un usuario del tenant A intenta acceder a un programa del tenant B
- **THEN** el sistema retorna 404 (recurso inexistente)
