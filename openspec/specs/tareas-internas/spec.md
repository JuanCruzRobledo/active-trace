## ADDED Requirements

### Requirement: Tarea tiene asignador, asignado, estado y descripción
Toda tarea SHALL tener un usuario que asigna (`asignado_por`), un usuario asignado (`asignado_a`), un estado (`Pendiente | En progreso | Resuelta | Cancelada`) y una descripción textual. Opcionalmente SHALL poder asociarse a una materia (`materia_id`) y a un contexto (`contexto_id`) que referencia otra entidad del dominio sin FK foráneo.

#### Scenario: Crear tarea con todos los campos
- **WHEN** un COORDINADOR crea una tarea con materia_id, asignado_a, descripción y estado Pendiente
- **THEN** la tarea se guarda con esos valores y aparece en el panel del asignado

#### Scenario: Crear tarea sin materia
- **WHEN** un COORDINADOR crea una tarea sin materia_id
- **THEN** la tarea se guarda con materia_id = NULL y aparece en el panel del asignado como tarea institucional

---

### Requirement: Workflow de estados con transiciones válidas
El estado de una tarea SHALL transicionar únicamente en este orden: Pendiente → En progreso → Resuelta; Pendiente → Cancelada; En progreso → Cancelada. Una tarea en estado Resuelta NO SHALL poder cambiar a otro estado. Cada cambio de estado SHALL generar un evento de auditoría `TAREA_ESTADO_CAMBIAR`.

#### Scenario: Transición válida Pendiente → En progreso
- **WHEN** el asignado cambia el estado de su tarea de Pendiente a En progreso
- **THEN** el estado se actualiza y se registra un audit log con accion = "TAREA_ESTADO_CAMBIAR"

#### Scenario: Transición válida En progreso → Resuelta
- **WHEN** el asignado cambia el estado de su tarea de En progreso a Resuelta
- **THEN** el estado se actualiza y la tarea se considera completada

#### Scenario: Transición inválida Resuelta → Pendiente
- **WHEN** un usuario intenta cambiar una tarea de Resuelta a Pendiente
- **THEN** el sistema retorna 422 con error de transición inválida

#### Scenario: Cancelación desde Pendiente
- **WHEN** el asignado o un COORDINADOR cancela una tarea en estado Pendiente
- **THEN** el estado cambia a Cancelada

---

### Requirement: Timeline de mis tareas
Todo usuario autenticado SHALL poder ver las tareas asignadas a él/ella. La lista SHALL ordenarse por `created_at` descendente (más recientes primero) y SHALL soportar filtros por estado y materia.

#### Scenario: Docente ve solo sus tareas
- **WHEN** un PROFESOR autenticado consulta GET /api/tareas/mias
- **THEN** recibe solo las tareas donde `asignado_a` = su UUID

#### Scenario: Filtrar por estado
- **WHEN** un PROFESOR consulta GET /api/tareas/mias?estado=Pendiente
- **THEN** recibe solo las tareas pendientes asignadas a él/ella

#### Scenario: Timeline vacía
- **WHEN** un usuario sin tareas asignadas consulta su timeline
- **THEN** recibe una lista vacía con total = 0

---

### Requirement: Vista de administración con filtros
Los usuarios con permiso `tareas:gestionar` SHALL poder ver todas las tareas del tenant con filtros combinables por: materia, asignado_a (docente), asignado_por, estado y búsqueda textual en descripción.

#### Scenario: Admin ve todas las tareas
- **WHEN** un COORDINADOR consulta GET /api/tareas sin filtros
- **THEN** recibe todas las tareas del tenant ordenadas por created_at DESC

#### Scenario: Filtrar por múltiples criterios
- **WHEN** un COORDINADOR consulta GET /api/tareas?estado=Pendiente&materia_id=X
- **THEN** recibe solo las tareas pendientes de la materia X

#### Scenario: Búsqueda textual
- **WHEN** un COORDINADOR consulta GET /api/tareas?busqueda=urgente
- **THEN** recibe las tareas cuya descripción contiene "urgente" (ILIKE)

#### Scenario: Sin permiso retorna 403
- **WHEN** un TUTOR sin permiso `tareas:gestionar` consulta GET /api/tareas (sin filtro de asignado_a)
- **THEN** el sistema retorna 403 Forbidden

---

### Requirement: Comentarios asincrónicos por tarea
Todo usuario que pueda ver una tarea SHALL poder agregar comentarios. El comentario SHALL registrar autor_id, texto y timestamp. Los comentarios SHALL listarse en orden cronológico ascendente.

#### Scenario: Agregar comentario a tarea
- **WHEN** el asignado agrega un comentario a su tarea
- **THEN** el comentario se guarda con su UUID, autor_id y timestamp, y se genera un audit log "TAREA_COMENTARIO"

#### Scenario: Comentario de asignador
- **WHEN** el COORDINADOR que asignó la tarea agrega un comentario
- **THEN** el comentario se guarda correctamente y aparece en la conversación

#### Scenario: Listar comentarios ordenados
- **WHEN** un usuario abre una tarea con comentarios
- **THEN** los comentarios se retornan ordenados por creado_at ASC

---

### Requirement: Creación de tarea con auditoría
Toda creación de tarea SHALL generar un evento de auditoría `TAREA_CREAR`. Solo usuarios con permiso `tareas:gestionar` SHALL poder crear tareas.

#### Scenario: Crear tarea con permiso
- **WHEN** un COORDINADOR con permiso `tareas:gestionar` crea una tarea
- **THEN** la tarea se crea y se registra audit log con accion = "TAREA_CREAR"

#### Scenario: Crear tarea sin permiso
- **WHEN** un TUTOR sin permiso `tareas:gestionar` intenta crear una tarea
- **THEN** el sistema retorna 403 Forbidden

---

### Requirement: Acceso a detalle de tarea
Todo usuario SHALL poder ver el detalle de una tarea si es el asignado o tiene permiso `tareas:gestionar`.

#### Scenario: Asignado ve detalle
- **WHEN** el asignado consulta GET /api/tareas/{id} de su tarea
- **THEN** recibe el detalle con comentarios incluidos

#### Scenario: Usuario no autorizado ve detalle
- **WHEN** un usuario que no es el asignado ni tiene `tareas:gestionar` consulta GET /api/tareas/{id}
- **THEN** el sistema retorna 403 Forbidden

#### Scenario: Tarea inexistente
- **WHEN** cualquier usuario consulta una tarea con UUID inexistente
- **THEN** el sistema retorna 404 Not Found

---

### Requirement: Aislamiento multi-tenant
Toda operación sobre tareas y comentarios SHALL respetar el tenant_id del usuario autenticado. Un usuario del tenant A NO SHALL poder ver tareas del tenant B.

#### Scenario: Tareas aisladas por tenant
- **WHEN** el usuario del tenant A y el usuario del tenant B tienen tareas
- **THEN** cada uno ve solo las tareas de su tenant

#### Scenario: Acceso cross-tenant denegado
- **WHEN** un usuario del tenant A intenta acceder a una tarea del tenant B
- **THEN** el sistema retorna 404 (no existe, como si la tarea no estuviera)
