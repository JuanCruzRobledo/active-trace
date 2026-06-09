# finanzas-admin Specification

## Purpose
TBD - created by archiving change c-24-frontend-finanzas-y-admin. Update Purpose after archive.
## Requirements
### Requirement: Vista de liquidaciones del período segmentada — frontend
The frontend SHALL provide a view for FINANZAS/ADMIN to see the liquidación of a selected period with three accounting segments (general / NEXO / docentes que facturan) and header KPIs.

#### Scenario: Visualizar liquidación segmentada del período
- **WHEN** un usuario con permiso `liquidaciones:ver` accede a /finanzas/liquidaciones y selecciona un período
- **THEN** el sistema muestra tres segmentos diferenciados (detalle general PROFESOR/TUTOR/COORDINADOR, segmento NEXO, y docentes que facturan) y los KPIs de cabecera "Total sin factura" y "Total con factura"

#### Scenario: Docentes que facturan excluidos del total
- **WHEN** se renderiza el segmento de docentes que facturan
- **THEN** el sistema los muestra de forma informativa pero NO los suma al total de la liquidación general

#### Scenario: Filtrar liquidación por cohorte, mes y docente
- **WHEN** el usuario aplica filtros de cohorte, mes o un docente específico
- **THEN** el sistema recalcula la vista mostrando solo las filas que coinciden con los filtros

#### Scenario: Vista previa del detalle individual de un docente
- **WHEN** el usuario selecciona un docente de la tabla
- **THEN** el sistema muestra el detalle individual con rol, comisiones a cargo, salario base, plus aplicables y total a cobrar

### Requirement: Cierre de liquidación — frontend
The frontend SHALL allow FINANZAS to close a liquidación, making it immutable, through an explicit confirmation step.

#### Scenario: Cerrar liquidación con confirmación
- **WHEN** un usuario con permiso `liquidaciones:cerrar` solicita cerrar una liquidación abierta y confirma la acción en el diálogo de confirmación
- **THEN** el sistema envía el cierre al backend, marca la liquidación como "Cerrada" y deshabilita las acciones de modificación

#### Scenario: Liquidación cerrada no editable
- **WHEN** una liquidación ya está cerrada
- **THEN** el sistema muestra el indicador de estado "Cerrada" y no ofrece acciones de modificación ni cierre

### Requirement: Historial de liquidaciones — frontend
The frontend SHALL provide access to closed liquidaciones from previous periods for consultation.

#### Scenario: Consultar historial de liquidaciones
- **WHEN** un usuario con permiso `liquidaciones:ver` accede a /finanzas/historial
- **THEN** el sistema muestra un listado filtrable de liquidaciones cerradas de períodos anteriores con acceso a su detalle

### Requirement: ABM de grilla salarial — frontend
The frontend SHALL provide management of the salary grid: salarios base por rol y plus por clave, ambos con vigencia temporal.

#### Scenario: Listar grilla salarial vigente
- **WHEN** un usuario con permiso `liquidaciones:configurar-salarios` accede a /finanzas/grilla-salarial
- **THEN** el sistema muestra los salarios base por rol y los plus, cada uno con sus fechas de vigencia

#### Scenario: Crear salario base con vigencia
- **WHEN** el usuario completa el formulario de salario base con rol, importe y vigencia desde/hasta y lo guarda
- **THEN** el sistema crea el registro y lo refleja en la tabla de salarios base

#### Scenario: Crear plus con vigencia
- **WHEN** el usuario completa el formulario de plus con clave, rol, descripción e importe con vigencia y lo guarda
- **THEN** el sistema crea el plus y lo refleja en la tabla de plus

### Requirement: Gestión de facturas de docentes que facturan — frontend
The frontend SHALL provide ABM de comprobantes de docentes que facturan, con filtros y cambio de estado entre pendiente y abonada.

#### Scenario: Listar facturas con filtros
- **WHEN** un usuario con permiso `liquidaciones:ver` accede a /finanzas/facturas
- **THEN** el sistema muestra un listado filtrable por docente, estado (pendiente/abonada), rango de fechas y búsqueda libre

#### Scenario: Marcar factura como abonada
- **WHEN** el usuario marca una factura pendiente como abonada y confirma
- **THEN** el sistema actualiza el estado del comprobante a "abonada" y refleja el cambio en el listado

### Requirement: Administración de estructura académica — frontend
The frontend SHALL provide ABM de carreras, cohortes y materias para el rol ADMIN.

#### Scenario: ABM de carreras
- **WHEN** un usuario con permiso `estructura:gestionar` accede a /admin/carreras
- **THEN** el sistema permite listar, crear, editar y cambiar el estado (activa/inactiva) de carreras con su código y nombre

#### Scenario: ABM de cohortes
- **WHEN** un usuario con permiso `estructura:gestionar` accede a /admin/cohortes
- **THEN** el sistema permite listar, crear, editar y cambiar el estado de cohortes con nombre, año de inicio y vigencia desde/hasta

#### Scenario: ABM de materias
- **WHEN** un usuario con permiso `estructura:gestionar` accede a /admin/materias
- **THEN** el sistema permite listar, crear y editar materias del tenant

### Requirement: Administración de usuarios del tenant — frontend
The frontend SHALL provide ABM de usuarios del tenant para el rol ADMIN, incluyendo rol, estado y datos fiscales/bancarios.

#### Scenario: Listar usuarios del tenant
- **WHEN** un usuario con permiso `usuarios:gestionar` accede a /admin/usuarios
- **THEN** el sistema muestra un listado filtrable de los usuarios del tenant con su rol y estado de actividad

#### Scenario: Alta de usuario
- **WHEN** el usuario completa el formulario de alta con nombre, identificación fiscal, datos bancarios, regional, rol y modalidad de facturación y lo guarda
- **THEN** el sistema crea el usuario y lo muestra en el listado

#### Scenario: Editar y activar/desactivar usuario
- **WHEN** el usuario edita los datos de un usuario existente o cambia su estado de actividad
- **THEN** el sistema actualiza el usuario y refleja los cambios en el listado

### Requirement: Panel de auditoría y métricas — frontend
The frontend SHALL provide an audit panel for ADMIN/COORDINADOR with usage metrics and filters.

#### Scenario: Ver panel de auditoría con sub-vistas
- **WHEN** un usuario con permiso `auditoria:ver` accede a /admin/auditoria
- **THEN** el sistema muestra el gráfico de acciones por día, el estado de comunicaciones por docente, las interacciones por docente×materia y el registro de últimas acciones

#### Scenario: Filtrar el panel de auditoría
- **WHEN** el usuario aplica filtros de rango de fechas, materia, usuario o estado de actividad
- **THEN** el sistema actualiza todas las sub-vistas del panel con los datos filtrados

### Requirement: Log completo de auditoría — frontend
The frontend SHALL provide a complete audit log view for ADMIN with all recorded fields.

#### Scenario: Ver log completo de auditoría
- **WHEN** un usuario con permiso `auditoria:ver` accede al log completo
- **THEN** el sistema muestra cada acción con fecha/hora, identificador de usuario, materia, tipo de acción, cantidad de registros afectados, dirección IP y agente de usuario

### Requirement: Navegación de finanzas y administración — frontend
The frontend SHALL expose navigation sections "Finanzas" and "Administración" gated by the authenticated user's permissions.

#### Scenario: Menú adaptado a permisos
- **WHEN** un usuario autenticado abre el menú de navegación
- **THEN** el sistema muestra solo las secciones de Finanzas y Administración para las que el usuario tiene permiso, y oculta las demás

