# Spec: liquidacion-honorarios

## ADDED Requirements

### Requirement: Cálculo automático de liquidación
El sistema SHALL calcular la liquidación mensual de todos los docentes de una cohorte para un período dado, usando la fórmula: `Total = Base(rol vigente al mes) + Σ(Plus(clave_materia, rol) × N_comisiones_activas)`.

#### Scenario: Cálculo exitoso de liquidación
- **WHEN** FINANZAS ejecuta cálculo para (cohorte=UUID, mes=2026-06)
- **THEN** el sistema genera una Liquidacion por cada docente con asignaciones activas en el período

#### Scenario: Base salarial según rol vigente
- **WHEN** un docente tiene rol PROFESOR en el período
- **THEN** el sistema toma el SalarioBase vigente para ese rol al mes de cálculo

#### Scenario: Plus por comisiones activas
- **WHEN** un docente tiene 3 comisiones activas de materias con clave PROG en el período
- **THEN** el sistema calcula: monto_plus = 3 × Plus(PROG, PROFESOR) vigente

#### Scenario: Materias sin clave no generan plus
- **WHEN** un docente tiene comisiones de materias sin `clave_plus_id`
- **THEN** esas comisiones no aportan al cálculo del plus (solo cuentan para el base)

#### Scenario: Multi-key accumulation
- **WHEN** un docente tiene comisiones de materias con distintas claves (2 PROG + 1 BD)
- **THEN** el sistema suma: monto_plus = 2 × Plus(PROG, PROFESOR) + 1 × Plus(BD, PROFESOR)

#### Scenario: Docente facturante excluido del cálculo
- **WHEN** un docente tiene `facturador = true`
- **THEN** el sistema genera Liquidacion con `excluido_por_factura = true` y `total = 0`

#### Scenario: NEXO con base pero sin plus
- **WHEN** se liquida un docente con rol NEXO
- **THEN** la liquidación tiene `es_nexo = true`, `monto_base > 0`, `monto_plus = 0`

### Requirement: Vista previa de liquidación
El sistema SHALL mostrar una vista previa de las liquidaciones calculadas antes del cierre, con KPIs de cabecera.

#### Scenario: Vista previa con KPIs
- **WHEN** FINANZAS solicita vista previa para (cohorte, mes)
- **THEN** el sistema retorna lista de liquidaciones + KPIs: "Total sin factura", "Total con factura"

#### Scenario: Segmentación NEXO en vista previa
- **WHEN** FINANZAS visualiza la vista previa
- **THEN** las liquidaciones con `es_nexo = true` se muestran en sección diferenciada pero incluidas en el total general

### Requirement: Cierre de liquidación
El sistema SHALL permitir cerrar una liquidación, haciéndola inmutable, con permiso `liquidaciones:cerrar`.

#### Scenario: Cierre exitoso
- **WHEN** FINANZAS cierra una liquidación en estado Abierta
- **THEN** el sistema cambia estado a Cerrada y registra evento `LIQUIDACION_CERRAR` en AuditLog

#### Scenario: Cierre de liquidación ya cerrada
- **WHEN** FINANZAS intenta cerrar una liquidación ya Cerrada
- **THEN** el sistema rechaza con error 409 Conflict

#### Scenario: Liquidación cerrada no puede modificarse
- **WHEN** cualquier usuario intenta modificar una liquidación Cerrada
- **THEN** el sistema rechaza con error 409 Conflict

#### Scenario: Cierre sin permiso
- **WHEN** un usuario sin permiso `liquidaciones:cerrar` intenta cerrar
- **THEN** el sistema retorna 403 Forbidden

### Requirement: Historial de liquidaciones
El sistema SHALL permitir consultar liquidaciones cerradas de períodos anteriores con permiso `liquidaciones:ver`.

#### Scenario: Consulta por filtros
- **WHEN** FINANZAS consulta liquidaciones filtrando por (cohorte, mes, docente)
- **THEN** el sistema retorna las liquidaciones que coinciden con los filtros

#### Scenario: Consulta de documento inmutable
- **WHEN** FINANZAS consulta una liquidación cerrada
- **THEN** el sistema retorna el registro exacto con todos los campos del momento del cierre

### Requirement: Exportación de liquidación
El sistema SHALL permitir exportar la planilla de liquidación de un período completo.

#### Scenario: Exportación exitosa
- **WHEN** FINANZAS exporta liquidaciones para (cohorte, mes)
- **THEN** el sistema genera un archivo (CSV o Excel) con todos los datos del período

### Requirement: Multi-tenancy en liquidaciones
El sistema SHALL aislar las liquidaciones por tenant.

#### Scenario: Liquidaciones aisladas por tenant
- **WHEN** FINANZAS del tenant A consulta liquidaciones
- **THEN** solo ve liquidaciones del tenant A, nunca del B

### Requirement: Auditoría de liquidación
El sistema SHALL registrar en AuditLog toda operación de cierre de liquidación.

#### Scenario: Registro de cierre en auditoría
- **WHEN** FINANZAS cierra una liquidación
- **THEN** el sistema crea un AuditLog con accion=LIQUIDACION_CERRAR, actor_id, materia_id, detalle=JSON con id de liquidación y período
