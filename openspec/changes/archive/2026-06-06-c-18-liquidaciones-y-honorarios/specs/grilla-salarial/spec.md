# Spec: grilla-salarial

## ADDED Requirements

### Requirement: Gestión de SalarioBase
El sistema SHALL permitir al usuario con permiso `liquidaciones:configurar-salarios` gestionar los salarios base por rol (COORDINADOR, NEXO, PROFESOR, TUTOR) con vigencia temporal.

#### Scenario: Crear SalarioBase exitoso
- **WHEN** FINANZAS crea un SalarioBase con rol=PROFESOR, monto=500000, desde=2026-01-01, hasta=null
- **THEN** el sistema retorna el registro creado con los datos provistos

#### Scenario: SalarioBase vigente por período
- **WHEN** FINANZAS consulta la grilla vigente para el mes 2026-06-01
- **THEN** el sistema retorna solo los registros con `desde <= 2026-06-01` y (`hasta >= 2026-06-01` o `hasta IS NULL`)

#### Scenario: Actualizar SalarioBase cierra vigencia anterior
- **WHEN** FINANZAS actualiza el monto de un SalarioBase vigente para PROFESOR
- **THEN** el sistema marca el registro anterior con `hasta = fecha_actual - 1 día` y crea uno nuevo con `desde = fecha_actual`

#### Scenario: Solo un SalarioBase vigente por rol por período
- **WHEN** FINANZAS intenta crear un segundo SalarioBase vigente para el mismo rol en el mismo período
- **THEN** el sistema rechaza con error de conflicto (409)

#### Scenario: SalarioBase sin permiso
- **WHEN** un usuario sin permiso `liquidaciones:configurar-salarios` intenta acceder a la grilla
- **THEN** el sistema retorna 403 Forbidden

### Requirement: Gestión de SalarioPlus
El sistema SHALL permitir al usuario con permiso `liquidaciones:configurar-salarios` gestionar los plus salariales por (clave de materia × rol) con vigencia temporal.

#### Scenario: Crear SalarioPlus exitoso
- **WHEN** FINANZAS crea un SalarioPlus con grupo=PROG, rol=PROFESOR, monto=100000, desde=2026-01-01
- **THEN** el sistema retorna el registro creado con los datos provistos

#### Scenario: SalarioPlus por clave y rol
- **WHEN** FINANZAS lista los SalarioPlus vigentes
- **THEN** el sistema retorna todos los registros filtrados por tenant, agrupables por clave y rol

#### Scenario: SalarioPlus acumulable por comisión
- **WHEN** FINANZAS consulta el detalle de un SalarioPlus
- **THEN** el sistema muestra el monto unitario que se multiplica por N comisiones activas de la misma clave
