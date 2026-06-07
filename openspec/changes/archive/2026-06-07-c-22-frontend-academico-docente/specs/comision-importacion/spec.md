## ADDED Requirements

### Requirement: Página de importación de calificaciones
El sistema SHALL proveer una página donde el PROFESOR pueda importar calificaciones de una materia con preview previo a la confirmación.

#### Scenario: Acceso a página de importación
- **WHEN** el usuario navega a `/comision/:materiaId/importar`
- **THEN** el sistema muestra un formulario con selector de archivo y botón "Previsualizar"

#### Scenario: Preview de importación exitosa
- **WHEN** el usuario selecciona un archivo válido y hace clic en "Previsualizar"
- **THEN** el sistema envía el archivo a POST `/api/v1/calificaciones/preview` y muestra una tabla con las filas parseadas, cantidad de filas, y botones "Confirmar importación" y "Cancelar"

#### Scenario: Confirmar importación
- **WHEN** el usuario hace clic en "Confirmar importación" tras el preview
- **THEN** el sistema envía POST a `/api/v1/calificaciones/importar` y muestra indicador de éxito con resumen (filas importadas, errores si los hubo)

#### Scenario: Error en preview
- **WHEN** el archivo tiene formato inválido o datos incorrectos
- **THEN** el sistema muestra un mensaje de error específico del backend y permite reintentar

### Requirement: Selección de actividades en importación
El sistema SHALL permitir al usuario seleccionar qué actividades incluir en la importación antes de confirmar.

#### Scenario: Selección de actividades en preview
- **WHEN** el preview muestra las actividades detectadas en el archivo
- **THEN** cada actividad tiene un checkbox, y el botón "Confirmar importación" solo importa las actividades seleccionadas
