## ADDED Requirements

### Requirement: El sistema SHALL mantener un padrón versionado de alumnos por materia×cohorte

Cada importación de padrón crea una nueva `VersionPadron`. Solo una versión puede estar activa por combinación (materia_id, cohorte_id). Al activar una nueva versión, la anterior se desactiva automáticamente en la misma transacción.

#### Scenario: Importación inicial crea versión activa
- **WHEN** se importa un padrón por primera vez para una materia×cohorte
- **THEN** el sistema crea una `VersionPadron` con `activa = true`
- **AND** las `EntradaPadron` se asocian a esa versión

#### Scenario: Nueva importación desactiva la versión anterior
- **WHEN** se importa un nuevo padrón para una materia×cohorte que ya tiene una versión activa
- **THEN** el sistema crea una nueva `VersionPadron` con `activa = true`
- **AND** desactiva la versión anterior (`activa = false`)
- **AND** la versión anterior permanece en la base de datos (histórico)

#### Scenario: Consulta de padrón activo retorna solo la versión vigente
- **WHEN** se consulta el padrón de una materia×cohorte
- **THEN** el sistema retorna las entradas de la `VersionPadron` con `activa = true`

### Requirement: Importación manual con vista previa obligatoria

El endpoint `POST /api/padron/importar` acepta archivos `.xlsx` y `.csv`. En el primer llamado (modo preview), parsea el archivo, detecta columnas y devuelve una vista previa. El usuario debe confirmar explícitamente para persistir.

#### Scenario: Preview de importación xlsx exitosa
- **WHEN** se envía un archivo `.xlsx` válido con columnas nombre, apellido, email, comisión
- **THEN** el sistema retorna una vista previa con: filas detectadas, columnas mapeadas, cantidad de registros, y un `preview_token`

#### Scenario: Preview de importación csv exitosa
- **WHEN** se envía un archivo `.csv` válido con delimitador coma y columnas esperadas
- **THEN** el sistema retorna una vista previa igual que con xlsx

#### Scenario: Confirmación de importación persiste los datos
- **WHEN** se envía el mismo `preview_token` que se devolvió en el preview
- **THEN** el sistema crea la nueva `VersionPadron` con sus `EntradaPadron`
- **AND** retorna la versión creada con su ID y cantidad de entradas

#### Scenario: Confirmación con preview_token inválido es rechazada
- **WHEN** se envía un `preview_token` que no coincide con ningún preview activo
- **THEN** el sistema retorna 400 Bad Request

#### Scenario: Archivo mal formado es rechazado en preview
- **WHEN** se envía un archivo con formato inválido o columnas irreconocibles
- **THEN** el sistema retorna 422 Unprocessable Entity con detalle del error

### Requirement: EntradaPadron puede existir sin usuario_id

Los alumnos importados pueden no tener aún cuenta en el sistema. El campo `usuario_id` es nullable.

#### Scenario: Entrada sin usuario_id se crea correctamente
- **WHEN** se importa un padrón con alumnos que no existen como Usuario en el sistema
- **THEN** las `EntradaPadron` se crean con `usuario_id = null`
- **AND** el resto de los campos (nombre, apellido, email) se almacenan desnormalizados

#### Scenario: Entrada con usuario_id existente se vincula correctamente
- **WHEN** se importa un padrón con alumnos cuyo email coincide con usuarios existentes en el tenant
- **THEN** el sistema vincula `usuario_id` al usuario correspondiente
- **AND** el match se hace por email (único por tenant)

### Requirement: Vaciar datos de materia (F1.5, RN-04)

Endpoint `DELETE /api/padron/{materia_id}/vaciar` que desactiva todas las versiones activas de la materia y limpia datos asociados, sin afectar otras materias.

#### Scenario: Vaciar datos de materia desactiva versiones activas
- **WHEN** un usuario con permiso `padron:importar` ejecuta vaciar sobre una materia
- **THEN** todas las `VersionPadron` activas de esa materia pasan a `activa = false`
- **AND** los datos de ingesta asociados se limpian
- **AND** se genera un registro de auditoría con código `PADRON_VACIAR`

#### Scenario: Usuario sin permiso no puede vaciar
- **WHEN** un usuario sin permiso `padron:importar` intenta vaciar una materia
- **THEN** el sistema retorna 403 Forbidden

### Requirement: Auditoría de operaciones de padrón

Toda importación o vaciado de padrón genera un registro en el log de auditoría.

#### Scenario: Importación genera audit PADRON_CARGAR
- **WHEN** se confirma una importación de padrón exitosamente
- **THEN** el sistema registra un `AuditLog` con código `PADRON_CARGAR`, actor, materia, cohorte, cantidad de entradas importadas

#### Scenario: Vaciar genera audit PADRON_VACIAR
- **WHEN** se ejecuta vaciar datos de materia exitosamente
- **THEN** el sistema registra un `AuditLog` con código `PADRON_VACIAR`, actor, materia, cohortes afectadas

### Requirement: Aislamiento multi-tenant

Todos los datos de padrón están scoped al tenant del usuario autenticado. Un tenant no puede ver ni modificar datos de otro.

#### Scenario: Un tenant no ve padrones de otro tenant
- **WHEN** el usuario del Tenant A consulta el padrón de una materia
- **THEN** solo ve entradas del Tenant A
- **AND** no puede acceder a datos del Tenant B aunque conozca el UUID
