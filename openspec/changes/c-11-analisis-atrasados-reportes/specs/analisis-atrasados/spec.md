## ADDED Requirements

### Requirement: Cómputo de alumnos atrasados por materia
El sistema SHALL computar el listado de alumnos atrasados para una materia+cohorte dados, según RN-06: un alumno se considera atrasado si tiene al menos una actividad faltante (sin calificación) o si su nota numérica está por debajo del umbral configurado.

#### Scenario: Alumno con actividad faltante aparece como atrasado
- **WHEN** se consultan atrasados para una materia donde un alumno tiene actividad(es) sin registro de calificación
- **THEN** el sistema incluye a ese alumno en la lista de atrasados.

#### Scenario: Alumno con nota bajo umbral aparece como atrasado
- **WHEN** se consultan atrasados para una materia donde un alumno tiene `nota_numerica=40` y el umbral es 60%
- **THEN** el sistema incluye a ese alumno en la lista de atrasados.

#### Scenario: Alumno con todas las actividades aprobadas NO aparece como atrasado
- **WHEN** se consultan atrasados para una materia donde un alumno tiene todas las actividades con nota >= umbral
- **THEN** el sistema NO incluye a ese alumno en la lista de atrasados.

#### Scenario: Cómputo usa umbral configurado o default 60%
- **WHEN** se consultan atrasados para una materia SIN `UmbralMateria` configurado
- **THEN** el sistema usa 60% como umbral por defecto.

#### Scenario: Filtro por comisión
- **WHEN** se consultan atrasados con `comision=A`
- **THEN** el sistema solo incluye alumnos de esa comisión.

#### Scenario: Alumno con nota textual aprobatoria NO aparece como atrasado
- **WHEN** un alumno tiene `nota_textual="Satisfactorio"` que está en `valores_aprobatorios`
- **THEN** el sistema NO lo considera atrasado para esa actividad.

### Requirement: Scope multi-tenant en cómputo de atrasados
El sistema SHALL filtrar todos los cómputos de atrasados por `tenant_id` del usuario autenticado, sin exponer datos de otros tenants.

#### Scenario: Aislamiento multi-tenant
- **WHEN** un usuario del Tenant-A consulta atrasados
- **THEN** el sistema solo devuelve alumnos del Tenant-A, incluso si Tenant-B tiene datos similares.

### Requirement: Permiso atrasados:ver
El sistema SHALL requerir el permiso `atrasados:ver` para acceder a cualquier endpoint de análisis de atrasados.

#### Scenario: Sin permiso devuelve 403
- **WHEN** un usuario sin permiso `atrasados:ver` intenta consultar atrasados
- **THEN** el sistema devuelve HTTP 403 Forbidden.
