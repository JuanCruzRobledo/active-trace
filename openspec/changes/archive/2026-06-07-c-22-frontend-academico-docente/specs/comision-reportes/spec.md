## ADDED Requirements

### Requirement: Página de reportes rápidos
El sistema SHALL proveer una página con métricas consolidadas de la materia.

#### Scenario: Visualizar reportes rápidos
- **WHEN** el usuario navega a `/comision/:materiaId/reportes`
- **THEN** el sistema muestra tarjetas con métricas: total alumnos, actividades registradas, % aprobación, alumnos atrasados, alumnos al día

#### Scenario: Estado sin datos
- **WHEN** la materia no tiene datos importados
- **THEN** el sistema muestra un estado informativo "No hay datos disponibles. Importe calificaciones primero."

### Requirement: Exportar entregas sin corregir
El sistema SHALL permitir descargar un listado de entregas pendientes de corrección.

#### Scenario: Exportar listado
- **WHEN** el usuario hace clic en "Exportar entregas sin corregir"
- **THEN** el sistema descarga un archivo CSV con el listado de entregas pendientes por alumno y actividad
