## ADDED Requirements

### Requirement: Gestión de equipos docentes — frontend
The frontend SHALL provide views for COORDINADOR/ADMIN to manage teaching teams: mis equipos (propia del docente), asignaciones del tenant, asignación masiva, clonar equipo entre períodos, modificar vigencia y exportar equipo.

#### Scenario: Docente ve sus equipos asignados
- **WHEN** un usuario con rol PROFESOR/TUTOR/NEXO/COORDINADOR accede a /equipos
- **THEN** el sistema muestra una tabla filtrable con las comisiones y materias donde está asignado, incluyendo rol, carrera, cohorte, vigencia y estado

#### Scenario: Coordinador ve todas las asignaciones del tenant
- **WHEN** un usuario con permiso `equipos:ver` accede a /equipos/asignaciones
- **THEN** el sistema muestra todas las asignaciones activas del tenant filtrables por materia, carrera, cohorte, docente y rol

#### Scenario: Asignación masiva de docentes
- **WHEN** un usuario con permiso `equipos:asignar` completa el formulario de asignación masiva seleccionando materia × carrera × cohorte × rol y múltiples docentes
- **THEN** el sistema envía la asignación al backend y muestra confirmación con el resultado

#### Scenario: Clonar equipo entre períodos
- **WHEN** un usuario con permiso `equipos:asignar` selecciona un equipo origen y un destino
- **THEN** el sistema ejecuta la clonación y muestra resumen de asignaciones duplicadas

#### Scenario: Modificar vigencia de equipo
- **WHEN** un usuario con permiso `equipos:asignar` actualiza las fechas de vigencia de un equipo
- **THEN** el sistema actualiza todas las asignaciones del equipo con las nuevas fechas

#### Scenario: Exportar equipo docente
- **WHEN** un usuario con permiso `equipos:ver` selecciona un equipo y solicita exportación
- **THEN** el sistema descarga un archivo con el detalle de asignaciones del equipo

### Requirement: Gestión de avisos — frontend
The frontend SHALL provide ABM completo de avisos del sistema con configuración de alcance, severidad, vigencia, roles destinatarios, requerimiento de acknowledgment y tracking de confirmaciones.

#### Scenario: Crear aviso con todos los campos
- **WHEN** un usuario con permiso `avisos:publicar` completa el formulario de aviso con alcance (global/materia/cohorte), severidad, roles destino, vigencia, contenido y require_ack
- **THEN** el sistema crea el aviso y lo muestra en el listado

#### Scenario: Editar aviso existente
- **WHEN** un usuario con permiso `avisos:gestionar` modifica los campos de un aviso existente
- **THEN** el sistema actualiza el aviso y refleja los cambios en el listado

#### Scenario: Eliminar aviso
- **WHEN** un usuario con permiso `avisos:gestionar` elimina un aviso
- **THEN** el sistema oculta el aviso del listado (soft delete)

#### Scenario: Ver timeline de avisos
- **WHEN** un usuario accede a /avisos
- **THEN** el sistema muestra el timeline de avisos activos ordenados por prioridad y fecha

#### Scenario: Tracking de acknowledgments
- **WHEN** un usuario con permiso `avisos:gestionar` accede al detalle de un aviso con require_ack=true
- **THEN** el sistema muestra qué destinatarios confirmaron lectura y quiénes no

### Requirement: Workflow de tareas internas — frontend
The frontend SHALL provide views for the task workflow: mis tareas (docente), asignar tarea, administración global (coordinación), y detalle con timeline de estados y comentarios.

#### Scenario: Docente ve sus tareas asignadas
- **WHEN** un usuario con rol TUTOR/PROFESOR/COORDINADOR accede a /tareas
- **THEN** el sistema muestra las tareas asignadas al usuario filtrables por estado y materia

#### Scenario: Asignar tarea a otro docente
- **WHEN** un usuario con permiso `tareas:asignar` completa el formulario de nueva tarea con materia, docente asignado, descripción y criterio de cierre
- **THEN** el sistema crea la tarea en estado Abierta y aparece en el panel del docente asignado

#### Scenario: Coordinador administra tareas globales
- **WHEN** un usuario con permiso `tareas:asignar` accede a la vista de administración
- **THEN** el sistema muestra todas las tareas del tenant filtrables por docente, materia y estado

#### Scenario: Cambiar estado de tarea y agregar comentario
- **WHEN** un usuario actualiza el estado de una tarea y agrega un comentario
- **THEN** el sistema registra el cambio de estado y agrega el comentario al hilo de la tarea

### Requirement: Encuentros — vista admin frontend
The frontend SHALL provide a transversal view of all encounters across the tenant for COORDINADOR/ADMIN.

#### Scenario: Coordinador ve todos los encuentros del tenant
- **WHEN** un usuario con permiso `encuentros:ver` accede a /encuentros
- **THEN** el sistema muestra una tabla filtrable de todos los encuentros con indicadores de estado (realizado/pendiente/cancelado)

### Requirement: Coloquios — frontend
The frontend SHALL provide panels for coloquio management: métricas, convocatorias CRUD, importar alumnos, listado de convocatorias y administración global.

#### Scenario: Ver panel de métricas de coloquios
- **WHEN** un usuario con permiso `coloquios:gestionar` accede a /coloquios
- **THEN** el sistema muestra total de alumnos cargados, instancias activas, reservas activas y notas registradas

#### Scenario: Crear convocatoria de coloquio
- **WHEN** un usuario completa el formulario de nueva convocatoria con materia, instancia, días disponibles y cupos
- **THEN** el sistema crea la convocatoria y los turnos reservables

#### Scenario: Importar alumnos a convocatoria
- **WHEN** un usuario sube el padrón de alumnos habilitados para una convocatoria
- **THEN** el sistema actualiza el padrón de la convocatoria

#### Scenario: Ver listado de convocatorias activas
- **WHEN** un usuario accede al listado de convocatorias
- **THEN** el sistema muestra materia, instancia, días disponibles, convocados, reservas activas y cupos libres

### Requirement: Guardias — frontend
The frontend SHALL provide registro y consulta de guardias cubiertas por tutores.

#### Scenario: Registrar guardia
- **WHEN** un tutor completa el formulario de guardia con materia, carrera/cohorte, día, horario y comentarios
- **THEN** el sistema registra la guardia y la muestra en el listado

#### Scenario: Consultar guardias con filtros
- **WHEN** un coordinador accede a /guardias
- **THEN** el sistema muestra una tabla filtrable de todas las guardias del tenant con opción de exportar

### Requirement: Programas — frontend
The frontend SHALL permitir subir y asociar programas oficiales por materia × carrera × cohorte.

#### Scenario: Subir programa de materia
- **WHEN** un usuario con permiso `estructura:gestionar` selecciona materia × carrera × cohorte y sube un archivo de programa
- **THEN** el sistema asocia el programa al contexto académico seleccionado

#### Scenario: Listar y eliminar programas
- **WHEN** un usuario accede a /programas
- **THEN** el sistema muestra los programas asociados filtrables por materia/carrera/cohorte con opción de eliminar

### Requirement: Fechas académicas — frontend
The frontend SHALL permitir gestionar fechas de evaluaciones (parciales, TP, coloquios) por materia × cohorte.

#### Scenario: Crear fecha de evaluación
- **WHEN** un usuario con permiso `estructura:gestionar` completa el formulario con materia, tipo, número de instancia, fecha y título
- **THEN** el sistema registra la fecha y la muestra en el listado y calendario

#### Scenario: Exportar fechas para LMS
- **WHEN** un usuario solicita exportar las fechas de una materia
- **THEN** el sistema genera un fragmento de contenido listo para publicar en el aula virtual

### Requirement: Setup de cuatrimestre — flujo guiado
The frontend SHALL provide a multi-step wizard for the FL-03 flow (start of academic period).

#### Scenario: Completar setup de cuatrimestre completo
- **WHEN** un coordinador completa los 7 pasos del wizard (crear cohorte, clonar equipo, ajustar asignaciones, cargar programas, cargar fechas, publicar aviso)
- **THEN** el sistema ejecuta cada paso y muestra un resumen final con el resultado de cada operación

#### Scenario: Saltar pasos opcionales en el wizard
- **WHEN** un coordinador omite pasos no obligatorios (clonar equipo, aviso de bienvenida)
- **THEN** el wizard continúa al siguiente paso sin ejecutar el omitido

### Requirement: Monitor general y de coordinación — frontend
The frontend SHALL provide a transversal view of all students' activity status (F2.7) and extend the seguimiento view with date range filter for COORDINADOR/ADMIN (F2.9).

#### Scenario: Coordinador ve monitor general de actividades
- **WHEN** un usuario con permiso `atrasados:ver` accede a /monitores/general
- **THEN** el sistema muestra una vista transversal de todos los alumnos del tenant con filtros por materia, regional, comisión, búsqueda libre, estado de actividad y criterio de clasificación

#### Scenario: Coordinador filtra monitor de seguimiento por rango de fechas
- **WHEN** un usuario con permiso adecuado accede a la vista de seguimiento con rol COORDINADOR/ADMIN
- **THEN** el sistema muestra filtros adicionales de rango de fechas ademś de los filtros estándar (alumno, correo, comisión, actividad, mínimo actividad)
