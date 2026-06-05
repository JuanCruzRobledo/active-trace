# comunicaciones-worker Specification

## Purpose
TBD - created by archiving change c-12-comunicaciones-cola-worker. Update Purpose after archive.
## Requirements
### Requirement: Worker asíncrono de comunicaciones
El sistema SHALL implementar un worker asíncrono que procese las comunicaciones en estado `Pendiente`. El worker SHALL ejecutarse en un loop periódico, consultar las comunicaciones Pendientes (excluyendo las que requieren aprobación no concedida), ejecutar el envío y actualizar el estado según el resultado.

#### Scenario: Worker procesa comunicación Pendiente exitosamente
- **WHEN** el worker encuentra una comunicación en estado `Pendiente` que no requiere aprobación
- **THEN** intenta el envío, y si es exitoso cambia el estado a `Enviado` y registra `enviado_at`.

#### Scenario: Worker procesa comunicación Pendiente y falla
- **WHEN** el worker encuentra una comunicación en estado `Pendiente` y el envío falla
- **THEN** cambia el estado a `Error`.

#### Scenario: Worker salta comunicación con aprobación pendiente
- **WHEN** el worker encuentra una comunicación en estado `Pendiente` que pertenece a un lote que requiere aprobación no concedida
- **THEN** el worker NO procesa esa comunicación y continúa con la siguiente.

#### Scenario: Worker procesa comunicación después de aprobación
- **WHEN** el worker encuentra una comunicación en estado `Pendiente` cuyo lote fue aprobado
- **THEN** el worker procesa la comunicación normalmente.

### Requirement: Concurrencia con SKIP LOCKED
El worker SHALL usar `FOR UPDATE SKIP LOCKED` al seleccionar comunicaciones para evitar contención entre múltiples instancias del worker.

#### Scenario: Dos workers no procesan la misma comunicación
- **WHEN** dos instancias del worker ejecutan simultáneamente
- **THEN** cada comunicación Pendiente es procesada por exactamente un worker.

### Requirement: Provider de envío desacoplado
El sistema SHALL definir una interfaz `ComunicacionProvider` que abstraiga el envío real. El worker SHALL recibir el provider por inyección de dependencias. La implementación concreta (stub/logging inicial) SHALL ser reemplazable sin modificar el worker.

#### Scenario: Worker usa provider inyectado
- **WHEN** el worker inicia su ciclo
- **THEN** utiliza el `ComunicacionProvider` inyectado para ejecutar cada envío.

#### Scenario: Provider stub registra intento de envío
- **WHEN** el worker invoca al provider stub
- **THEN** el stub registra en log el intento con destinatario, asunto y resultado simulado.

### Requirement: Intervalo de polling configurable
El worker SHALL leer el intervalo de polling desde configuración (variable de entorno o archivo de configuración) con un valor por defecto de 5 segundos.

#### Scenario: Worker usa intervalo por defecto
- **WHEN** el worker inicia sin configuración de intervalo
- **THEN** consulta la BD cada 5 segundos.

#### Scenario: Worker usa intervalo configurado
- **WHEN** el worker inicia con una variable de entorno `COMUNICACIONES_POLL_INTERVAL=10`
- **THEN** consulta la BD cada 10 segundos.

### Requirement: Graceful shutdown del worker
El worker SHALL soportar apagado graceful: al recibir señal de terminación, termina el ciclo actual y no inicia uno nuevo.

#### Scenario: Worker recibe SIGTERM durante ciclo
- **WHEN** el worker está procesando comunicaciones y recibe SIGTERM
- **THEN** termina el envío en curso y finaliza sin iniciar un nuevo ciclo.

### Requirement: Worker inicia con la aplicación
El worker SHALL iniciarse como parte del stack de aplicaciones, ya sea como proceso separado (recomendado) o como background task dentro de la app FastAPI.

#### Scenario: Worker se inicia como proceso independiente
- **WHEN** se ejecuta `python -m workers.comunicaciones_worker`
- **THEN** el worker inicia su loop de polling y comienza a procesar comunicaciones Pendientes.

