## ADDED Requirements

### Requirement: Página de comunicación a atrasados
El sistema SHALL proveer una página donde el PROFESOR pueda enviar comunicaciones masivas a alumnos atrasados con preview y tracking.

#### Scenario: Vista de comunicaciones con tracking
- **WHEN** el usuario navega a `/comision/:materiaId/comunicaciones`
- **THEN** el sistema muestra el historial de comunicaciones enviadas para esa materia con su estado (Pendiente/En envío/Enviado/Fallido/Cancelado) y fecha

#### Scenario: Crear nueva comunicación
- **WHEN** el usuario hace clic en "Nueva comunicación"
- **THEN** el sistema muestra un editor con campos: asunto, cuerpo del mensaje, y lista de destinatarios (alumnos atrasados preseleccionados con opción de deseleccionar)

#### Scenario: Preview antes de enviar
- **WHEN** el usuario completa el mensaje y hace clic en "Previsualizar"
- **THEN** el sistema muestra una vista previa del asunto y cuerpo tal como lo recibirá el destinatario, con botones "Enviar" y "Editar"

#### Scenario: Envío con confirmación
- **WHEN** el usuario hace clic en "Enviar" desde el preview
- **THEN** el sistema envía POST a `/api/v1/comunicaciones` y redirige al tracking de la comunicación

#### Scenario: Tracking en tiempo real
- **WHEN** la comunicación tiene estado `Pendiente` o `En envío`
- **THEN** el sistema hace polling cada 5s del estado hasta que cambie a `Enviado`, `Fallido` o `Cancelado`
- **THEN** el sistema muestra el progreso (X de Y enviados) durante el envío

#### Scenario: Error en envío
- **WHEN** la comunicación queda en estado `Fallido`
- **THEN** el sistema muestra el error y permite reintentar o editar
