## ADDED Requirements

### Requirement: Monitor general de actividades (F2.7)
El sistema SHALL proveer una vista transversal de todos los alumnos del tenant con filtros por materia, regional, comisión, estado de actividad y búsqueda libre por alumno. Disponible para COORDINADOR y ADMIN.

#### Scenario: Monitor general con filtro por materia
- **WHEN** un COORDINADOR consulta el monitor general filtrando por `materia_id`
- **THEN** el sistema devuelve solo los alumnos de esa materia con su estado de actividades.

#### Scenario: Monitor general con búsqueda libre
- **WHEN** un ADMIN consulta el monitor general con `q="García"`
- **THEN** el sistema filtra alumnos cuyo nombre o apellidos contienen "García".

#### Scenario: Monitor general sin filtro de materia (scope global)
- **WHEN** un ADMIN consulta el monitor general sin `materia_id`
- **THEN** el sistema devuelve alumnos de todas las materias del tenant (con paginación por defecto).

### Requirement: Monitor de seguimiento — vista tutor/profesor (F2.8)
El sistema SHALL proveer una vista filtrable del estado de actividades de los alumnos asignados al TUTOR o PROFESOR consultante, con filtros por alumno, correo, comisión, regional, actividad y mínimo de actividades aprobadas.

#### Scenario: Monitor seguimiento solo muestra alumnos del tutor
- **WHEN** un TUTOR consulta el monitor de seguimiento
- **THEN** el sistema solo devuelve alumnos de las materias donde el tutor tiene asignación.

#### Scenario: Monitor seguimiento con filtro por actividad
- **WHEN** un PROFESOR consulta el monitor con `actividad="Parcial 1"`
- **THEN** el sistema muestra solo el estado de esa actividad para cada alumno.

#### Scenario: Monitor seguimiento con mínimo de aprobadas
- **WHEN** un TUTOR consulta el monitor con `min_aprobadas=3`
- **THEN** el sistema solo incluye alumnos con al menos 3 actividades aprobadas.

### Requirement: Monitor de seguimiento — vista coordinación/admin (F2.9)
El sistema SHALL extender la vista F2.8 con un filtro adicional de rango de fechas (`fecha_desde`, `fecha_hasta`) para COORDINADOR y ADMIN, permitiendo acotar el período de análisis.

#### Scenario: Monitor extendido con rango de fechas
- **WHEN** un COORDINADOR consulta el monitor con `fecha_desde=2026-03-01&fecha_hasta=2026-06-01`
- **THEN** el sistema solo considera actividades con `importado_at` dentro del rango.

#### Scenario: Monitor extendido sin rango de fechas
- **WHEN** un COORDINADOR consulta el monitor sin `fecha_desde` ni `fecha_hasta`
- **THEN** el sistema se comporta como F2.8 (sin filtro temporal).

### Requirement: Scope multi-tenant en monitores
El sistema SHALL filtrar todos los monitores por `tenant_id` del usuario autenticado.

#### Scenario: Aislamiento tenant en monitores
- **WHEN** un usuario del Tenant-A consulta cualquier monitor
- **THEN** el sistema solo devuelve datos del Tenant-A.
