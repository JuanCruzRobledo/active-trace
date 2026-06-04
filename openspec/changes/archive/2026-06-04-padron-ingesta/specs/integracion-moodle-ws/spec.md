## ADDED Requirements

### Requirement: Cliente Moodle Web Services para sincronización de padrón

El sistema SHALL implementar un cliente dedicado en `integrations/moodle_ws.py` que se comunique con Moodle vía Web Services para obtener usuarios, actividades y calificaciones. La configuración (URL base + token) es por tenant.

#### Scenario: Sincronización on-demand exitosa retorna datos normalizados
- **WHEN** se invoca `MoodleWSClient.sync_padron(materia_id, cohorte_id)` con credenciales válidas
- **THEN** el cliente retorna una lista de alumnos con nombre, apellido, email, comisión en formato normalizado

#### Scenario: Error de conexión con Moodle retorna 502
- **WHEN** Moodle no responde o la URL es incorrecta
- **THEN** el cliente lanza una excepción mapeable a HTTP 502 Bad Gateway
- **AND** el sistema permite continuar con importación manual (fallback)

#### Scenario: Token inválido es detectado
- **WHEN** el token de Moodle WS es inválido o expiró
- **THEN** el cliente retorna error de autenticación
- **AND** el sistema registra el error para notificación al administrador del tenant

### Requirement: Sincronización con reintento y backoff

El cliente SHALL implementar reintentos con backoff exponencial para errores transitorios (timeout, 5xx).

#### Scenario: Reintento automático en error transitorio
- **WHEN** Moodle responde con 503 Service Unavailable
- **THEN** el cliente reintenta hasta 3 veces con backoff exponencial (1s, 2s, 4s)
- **AND** si todos los reintentos fallan, propaga el error como 502

#### Scenario: Error permanente no reintenta
- **WHEN** Moodle responde con 401 Unauthorized o 404 Not Found
- **THEN** el cliente NO reintenta y propaga el error inmediatamente

### Requirement: Configuración por tenant

La URL de Moodle WS y el token SHALL ser configurables por tenant, almacenados de forma segura (cifrados en reposo).

#### Scenario: Cada tenant tiene su propia configuración de Moodle
- **WHEN** se instancia `MoodleWSClient` para un tenant
- **THEN** usa la URL y token específicos de ese tenant
- **AND** un tenant no puede ver ni usar la configuración de Moodle de otro tenant
