# comunicaciones-envio Specification

## Purpose
TBD - created by archiving change c-12-comunicaciones-cola-worker. Update Purpose after archive.
## Requirements
### Requirement: Modelo Comunicacion
El sistema SHALL persistir comunicaciones con soporte para destinatario cifrado (AES-256), lote_id para agrupación de envíos masivos, y ciclo de estados Pendiente → Enviando → Enviado / Error / Cancelado (RN-15). Cada comunicación SHALL estar vinculada a un usuario emisor (`enviado_por`), una materia, y el contenido del mensaje (asunto + cuerpo).

#### Scenario: Creación de comunicación individual
- **WHEN** un usuario envía una comunicación a un destinatario único
- **THEN** el sistema persiste la comunicación con estado `Pendiente`, `destinatario` cifrado, y un `lote_id` único generado automáticamente.

#### Scenario: Creación de comunicación masiva
- **WHEN** un usuario envía una comunicación a múltiples destinatarios
- **THEN** el sistema persiste N registros de comunicación, todos con el mismo `lote_id`, cada uno con su `destinatario` cifrado y estado `Pendiente`.

#### Scenario: Transición a Enviado
- **WHEN** el worker procesa una comunicación Pendiente y el envío es exitoso
- **THEN** el estado cambia a `Enviado` y se registra `enviado_at`.

#### Scenario: Transición a Error
- **WHEN** el worker procesa una comunicación Pendiente y el envío falla
- **THEN** el estado cambia a `Error`.

#### Scenario: Cancelación antes del despacho
- **WHEN** un usuario cancela una comunicación en estado `Pendiente`
- **THEN** el estado cambia a `Cancelado`.

### Requirement: Destinatario cifrado en reposo
El sistema SHALL cifrar la columna `destinatario` de la tabla `comunicaciones` usando AES-256. El cifrado SHALL ser transparente para el resto del sistema: el service recibe el email en texto plano, el repository lo cifra al persistir y lo descifra al leer.

#### Scenario: Destinatario cifrado al persistir
- **WHEN** se crea una comunicación con un email de destinatario
- **THEN** el valor almacenado en la columna `destinatario` NO es el email en texto plano.

#### Scenario: Destinatario legible al consultar
- **WHEN** se consulta una comunicación existente
- **THEN** el campo `destinatario` se devuelve descifrado en la respuesta de la API.

### Requirement: Preview obligatoria antes del envío (RN-16)
El sistema SHALL exigir una vista previa antes de encolar cualquier comunicación. El endpoint `POST /api/comunicaciones/preview` SHALL recibir `asunto`, `cuerpo` y `destinatarios`, devolver el contenido renderizado y un `preview_token`. El endpoint `POST /api/comunicaciones/enviar` SHALL rechazar la operación si el `preview_token` no coincide con el hash del contenido actual.

#### Scenario: Preview exitosa
- **WHEN** un usuario envía asunto y cuerpo al endpoint de preview
- **THEN** el sistema devuelve el contenido renderizado y un `preview_token` de un solo uso.

#### Scenario: Envío con preview_token válido
- **WHEN** un usuario envía una comunicación con un `preview_token` que coincide con el hash del contenido
- **THEN** el sistema encola los mensajes en estado `Pendiente`.

#### Scenario: Envío con preview_token inválido
- **WHEN** un usuario envía una comunicación cuyo contenido no coincide con el `preview_token`
- **THEN** el sistema rechaza la operación con error 400.

#### Scenario: Envío sin preview_token
- **WHEN** un usuario intenta enviar una comunicación sin incluir `preview_token`
- **THEN** el sistema rechaza la operación con error 422.

### Requirement: Consulta de estado de lote
El sistema SHALL exponer un endpoint `GET /api/comunicaciones/{lote_id}` que devuelva el estado agregado de todas las comunicaciones de un lote: total, enviados, fallidos, cancelados, pendientes.

#### Scenario: Consulta de lote con todos exitosos
- **WHEN** un usuario consulta un lote_id cuyas comunicaciones están todas en estado `Enviado`
- **THEN** el sistema devuelve `total=N`, `enviados=N`, `fallidos=0`, `cancelados=0`, `pendientes=0`.

#### Scenario: Consulta de lote mixto
- **WHEN** un usuario consulta un lote_id con comunicaciones en múltiples estados
- **THEN** el sistema devuelve los contadores agregados correctos para cada estado.

### Requirement: Alcance de envío según rol
El sistema SHALL restringir el envío de comunicaciones según el rol del usuario: PROFESOR solo a alumnos de sus propias comisiones; COORDINADOR y ADMIN a cualquier alumno del tenant.

#### Scenario: Profesor envía a alumno de su comisión
- **WHEN** un PROFESOR envía una comunicación a un alumno de su comisión
- **THEN** el sistema encola la comunicación correctamente.

#### Scenario: Profesor intenta enviar a alumno de otra comisión
- **WHEN** un PROFESOR intenta enviar una comunicación a un alumno que NO pertenece a ninguna de sus comisiones
- **THEN** el sistema rechaza la operación con error 403.

### Requirement: Historial de envíos propios
El sistema SHALL exponer un endpoint `GET /api/comunicaciones/mis-envios` con paginación que liste los lotes enviados por el usuario autenticado, ordenados por fecha descendente.

#### Scenario: Listar envíos propios
- **WHEN** un usuario consulta sus envíos
- **THEN** el sistema devuelve los lotes creados por ese usuario, ordenados del más reciente al más antiguo.

### Requirement: Cancelación individual de comunicación pendiente
El sistema SHALL permitir cancelar una comunicación individual en estado `Pendiente` siempre que pertenezca al usuario que la creó.

#### Scenario: Cancelación exitosa
- **WHEN** un usuario cancela una comunicación Pendiente que le pertenece
- **THEN** el estado cambia a `Cancelado`.

#### Scenario: Cancelación de comunicación de otro usuario
- **WHEN** un usuario intenta cancelar una comunicación Pendiente que NO le pertenece
- **THEN** el sistema rechaza la operación con error 403.

#### Scenario: Cancelación de comunicación ya enviada
- **WHEN** un usuario intenta cancelar una comunicación en estado `Enviado` o `Error`
- **THEN** el sistema rechaza la operación con error 400.

### Requirement: Página de comunicación a atrasados (frontend)
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

