## ADDED Requirements

### Requirement: Página de alumnos atrasados
El sistema SHALL proveer una página donde el PROFESOR visualice los alumnos atrasados de una materia, según el umbral configurado.

#### Scenario: Visualizar tabla de atrasados
- **WHEN** el usuario navega a `/comision/:materiaId/atrasados`
- **THEN** el sistema muestra una tabla con columnas: alumno, actividades faltantes, nota actual, estado (atrasado/al día), y métrica de riesgo
- **THEN** la tabla se ordena por riesgo descendente

#### Scenario: Filtros en atrasados
- **WHEN** el usuario aplica filtros (por nombre, actividad, rango de nota)
- **THEN** el sistema actualiza la tabla mostrando solo los registros que coinciden con los filtros

#### Scenario: Sin atrasados
- **WHEN** no hay alumnos atrasados en la materia
- **THEN** el sistema muestra un mensaje informativo "No hay alumnos atrasados en esta materia" con un indicador visual positivo
