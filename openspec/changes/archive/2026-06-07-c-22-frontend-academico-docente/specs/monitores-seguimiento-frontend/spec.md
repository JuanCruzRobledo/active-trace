## ADDED Requirements

### Requirement: Monitor de seguimiento (vista tutor/profesor)
El sistema SHALL proveer una página donde TUTOR y PROFESOR vean el estado de actividades de los alumnos asignados.

#### Scenario: Visualizar monitor de seguimiento
- **WHEN** el usuario navega a `/monitores`
- **THEN** el sistema muestra una tabla filtrable con columnas: alumno, correo, comisión, actividad, estado, nota, materia

#### Scenario: Filtros en monitor
- **WHEN** el usuario aplica filtros (nombre, correo, comisión, materia, actividad, mínimo de actividades cumplidas)
- **THEN** el sistema actualiza los resultados mostrando solo los registros que coinciden

#### Scenario: Exportar monitor
- **WHEN** el usuario hace clic en "Exportar"
- **THEN** el sistema descarga un archivo CSV con los datos filtrados

#### Scenario: Limpiar filtros
- **WHEN** el usuario hace clic en "Limpiar filtros"
- **THEN** el sistema restablece todos los filtros a su valor por defecto y recarga los datos sin filtros

#### Scenario: Monitor sin datos
- **WHEN** no hay alumnos asignados al usuario
- **THEN** el sistema muestra un mensaje "No tienes alumnos asignados actualmente"
