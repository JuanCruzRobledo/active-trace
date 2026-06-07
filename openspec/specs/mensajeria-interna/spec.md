# mensajeria-interna Specification

## Purpose
TBD - created by archiving change c-20-perfil-y-mensajeria-interna. Update Purpose after archive.
## Requirements
### Requirement: Hilo de mensajes entre usuarios registrados
El sistema SHALL modelar hilos de mensajería interna entre dos usuarios registrados del tenant. Un hilo SHALL tener un asunto y dos participantes (`usuario_a`, `usuario_b`). Cada hilo SHALL contener uno o más mensajes ordenados cronológicamente. Esta mensajería SHALL ser independiente y paralela a las comunicaciones a alumnos (entidad `Comunicacion`).

#### Scenario: Crear hilo con primer mensaje
- **WHEN** un usuario inicia un hilo hacia otro usuario del tenant con asunto y cuerpo
- **THEN** se crea el hilo con ambos participantes y el primer mensaje queda registrado con autor, cuerpo y timestamp

#### Scenario: Hilo separado de comunicaciones a alumnos
- **WHEN** existen comunicaciones a alumnos y hilos internos en el tenant
- **THEN** ambos canales no se mezclan: el inbox interno solo expone hilos de mensajería entre usuarios registrados

---

### Requirement: Bandeja de hilos recibidos
Todo usuario autenticado SHALL poder listar los hilos en los que es participante vía `GET /api/inbox`. La lista SHALL incluir solo hilos donde el usuario es `usuario_a` o `usuario_b`, ordenados por la fecha del último mensaje (más recientes primero).

#### Scenario: Usuario ve solo sus hilos
- **WHEN** un usuario autenticado consulta `GET /api/inbox`
- **THEN** recibe solo los hilos donde él/ella es participante, no los hilos ajenos

#### Scenario: Inbox vacío
- **WHEN** un usuario sin hilos consulta su inbox
- **THEN** recibe una lista vacía con total = 0

#### Scenario: Orden por último mensaje
- **WHEN** un usuario tiene varios hilos con distinta actividad reciente
- **THEN** los hilos se ordenan por la fecha de su último mensaje, más recientes primero

---

### Requirement: Lectura de un hilo
Todo participante de un hilo SHALL poder leer el hilo completo con todos sus mensajes vía `GET /api/inbox/{hilo_id}`. Los mensajes SHALL retornarse en orden cronológico ascendente. Un usuario que no es participante NO SHALL poder acceder al hilo.

#### Scenario: Participante lee el hilo
- **WHEN** un participante consulta `GET /api/inbox/{hilo_id}` de su hilo
- **THEN** recibe el asunto y la lista de mensajes ordenados por `creado_at` ascendente

#### Scenario: No participante denegado
- **WHEN** un usuario que no participa en un hilo consulta `GET /api/inbox/{hilo_id}`
- **THEN** el sistema retorna 404 (como si el hilo no existiera para ese usuario)

#### Scenario: Hilo inexistente
- **WHEN** un usuario consulta un hilo con UUID inexistente
- **THEN** el sistema retorna 404 Not Found

---

### Requirement: Responder dentro del hilo
Todo participante de un hilo SHALL poder responder agregando un mensaje vía `POST /api/inbox/{hilo_id}/mensajes`. El mensaje SHALL registrar `autor_id`, cuerpo y timestamp, y SHALL agregarse al hilo existente. Cada envío SHALL generar un evento de auditoría `MENSAJE_ENVIAR`. Un usuario que no participa en el hilo NO SHALL poder responder.

#### Scenario: Participante responde
- **WHEN** un participante envía `POST /api/inbox/{hilo_id}/mensajes` con un cuerpo
- **THEN** el mensaje se agrega al hilo con su autor y timestamp, y se registra audit log `MENSAJE_ENVIAR`

#### Scenario: Respuesta aparece en el hilo
- **WHEN** un participante responde a un hilo y luego lo relee
- **THEN** su respuesta aparece como el último mensaje del hilo

#### Scenario: No participante no puede responder
- **WHEN** un usuario que no participa en el hilo intenta responder
- **THEN** el sistema retorna 404 y no se crea ningún mensaje

---

### Requirement: Marca de lectura de mensajes
Un mensaje recibido SHALL poder marcarse como leído por su destinatario. El inbox SHALL poder derivar qué hilos tienen mensajes no leídos para el usuario autenticado, sin almacenar contadores denormalizados.

#### Scenario: Hilo con mensajes no leídos
- **WHEN** un usuario tiene un hilo con un mensaje no leído de su contraparte
- **THEN** el inbox indica que ese hilo tiene mensajes no leídos para el usuario

#### Scenario: Mensajes propios no cuentan como no leídos
- **WHEN** un usuario envía un mensaje en un hilo
- **THEN** ese mensaje no se contabiliza como no leído para el propio autor

---

### Requirement: Aislamiento multi-tenant de la mensajería
Toda operación sobre hilos y mensajes SHALL respetar el `tenant_id` del usuario autenticado. Un usuario del tenant A NO SHALL poder ver ni responder hilos del tenant B.

#### Scenario: Hilos aislados por tenant
- **WHEN** existen hilos en el tenant A y en el tenant B
- **THEN** cada usuario ve solo los hilos de su propio tenant donde es participante

#### Scenario: Acceso cross-tenant denegado
- **WHEN** un usuario del tenant A intenta acceder a un hilo del tenant B
- **THEN** el sistema retorna 404 (no existe para ese usuario)

