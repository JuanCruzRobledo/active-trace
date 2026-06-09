# Spec: facturas-docentes

## ADDED Requirements

### Requirement: Registro de factura
El sistema SHALL permitir al usuario con permiso `facturas:gestionar` registrar una factura presentada por un docente facturante.

#### Scenario: Registro exitoso con archivo adjunto
- **WHEN** FINANZAS registra una factura con usuario_id (docente facturador), periodo=2026-06, detalle="Honorarios junio 2026", archivo PDF
- **THEN** el sistema crea la factura en estado Pendiente con fecha de carga, tamaño del archivo y referencia al almacenamiento

#### Scenario: Registro sin archivo adjunto
- **WHEN** FINANZAS registra una factura sin archivo adjunto
- **THEN** el sistema crea la factura con referencia_archivo=null

#### Scenario: Factura para docente no facturador
- **WHEN** FINANZAS intenta registrar una factura para un docente con `facturador = false`
- **THEN** el sistema rechaza con error 422 (validación de negocio)

#### Scenario: Factura sin permiso
- **WHEN** un usuario sin permiso `facturas:gestionar` intenta registrar
- **THEN** el sistema retorna 403 Forbidden

### Requirement: Cambio de estado de factura
El sistema SHALL permitir cambiar el estado de una factura entre Pendiente y Abonada.

#### Scenario: Marcar como abonada
- **WHEN** FINANZAS cambia estado de una factura Pendiente a Abonada
- **THEN** el sistema actualiza estado a Abonada y registra fecha de pago (abonada_at)

#### Scenario: Estado de factura ya abonada
- **WHEN** FINANZAS intenta cambiar estado de una factura ya Abonada
- **THEN** el sistema rechaza con error 409 Conflict

#### Scenario: Registro de cambio en auditoría
- **WHEN** FINANZAS cambia estado de factura
- **THEN** el sistema registra evento en AuditLog con accion FACTURA_ABONAR

### Requirement: Listado de facturas con filtros
El sistema SHALL permitir listar facturas con filtros por docente, estado y rango de fechas.

#### Scenario: Listado con filtros combinados
- **WHEN** FINANZAS consulta facturas con filtro (docente=UUID, estado=Pendiente, desde=2026-01-01, hasta=2026-06-30)
- **THEN** el sistema retorna las facturas que coinciden con todos los filtros

#### Scenario: Búsqueda por texto libre
- **WHEN** FINANZAS realiza búsqueda libre sobre el detalle de facturas
- **THEN** el sistema retorna facturas cuyo detalle contiene el texto buscado

### Requirement: Exclusión de facturantes de liquidación general
El sistema SHALL asegurar que los docentes facturantes no se incluyan en el cálculo de liquidación general Base+Plus.

#### Scenario: Facturante excluido de liquidación
- **WHEN** FINANZAS ejecuta cálculo de liquidación para un período
- **THEN** los docentes con `facturador = true` generan Liquidacion con `excluido_por_factura = true` y no se suman al total general

### Requirement: Multi-tenancy en facturas
El sistema SHALL aislar las facturas por tenant.

#### Scenario: Facturas aisladas por tenant
- **WHEN** FINANZAS del tenant A consulta facturas
- **THEN** solo ve facturas del tenant A, nunca del B
