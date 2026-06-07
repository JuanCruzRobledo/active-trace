## ADDED Requirements

### Requirement: Página de ranking de actividades aprobadas
El sistema SHALL proveer una página donde el PROFESOR vea el ranking de alumnos por actividades aprobadas.

#### Scenario: Visualizar ranking
- **WHEN** el usuario navega a `/comision/:materiaId/rankings`
- **THEN** el sistema muestra una tabla ordenada por cantidad de actividades aprobadas descendente, con columnas: alumno, actividades aprobadas, total actividades, porcentaje

#### Scenario: Ranking vacío
- **WHEN** no hay alumnos con actividades aprobadas
- **THEN** el sistema muestra un mensaje "Aún no hay datos de actividades aprobadas"

### Requirement: Página de notas finales agrupadas
El sistema SHALL proveer una vista de notas finales calculadas por alumno.

#### Scenario: Visualizar notas finales
- **WHEN** el usuario navega a `/comision/:materiaId/rankings?view=notas-finales`
- **THEN** el sistema muestra una tabla con alumno y nota final calculada, lista para exportar
