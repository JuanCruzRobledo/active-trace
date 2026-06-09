## ADDED Requirements

### Requirement: Modelo Calificacion
El sistema SHALL persistir calificaciones de alumnos con soporte para nota numérica y/o textual, derivación automática de `aprobado`, y origen (Importado/Manual). Cada calificación SHALL estar vinculada a una `EntradaPadron` (alumno), una `Materia`, y una actividad evaluable.

#### Scenario: Creación de calificación con nota numérica
- **WHEN** se importa una calificación con `nota_numerica=75` para un alumno en una materia con umbral 60%
- **THEN** el sistema persiste la calificación y deriva `aprobado=True`.

#### Scenario: Creación de calificación con nota textual
- **WHEN** se importa una calificación con `nota_textual="Satisfactorio"` y el umbral incluye ese valor como aprobatorio
- **THEN** el sistema persiste la calificación y deriva `aprobado=True`.

#### Scenario: Calificación sin nota (solo pendiente)
- **WHEN** se importa una calificación sin `nota_numerica` ni `nota_textual`
- **THEN** el sistema rechaza la operación con error de validación.

### Requirement: Derivación del campo aprobado
El sistema SHALL derivar el campo `aprobado` en el momento de importación según estas reglas:
- Si existe `nota_numerica`: se compara contra el umbral configurado para esa asignación (o default 60%).
- Si solo existe `nota_textual`: se evalúa contra el conjunto de valores aprobatorios configurados.
- Si existen ambas: la numérica tiene prioridad.

#### Scenario: Aprobado por nota numérica sobre umbral
- **WHEN** una calificación tiene `nota_numerica=80` y el umbral de la asignación es 60%
- **THEN** `aprobado=True`.

#### Scenario: No aprobado por nota numérica bajo umbral
- **WHEN** una calificación tiene `nota_numerica=40` y el umbral de la asignación es 60%
- **THEN** `aprobado=False`.

#### Scenario: Aprobado por valor textual aprobatorio
- **WHEN** una calificación tiene `nota_textual="Supera lo esperado"` y ese valor está en `valores_aprobatorios`
- **THEN** `aprobado=True`.

#### Scenario: No aprobado por valor textual no aprobatorio
- **WHEN** una calificación tiene `nota_textual="No satisfactorio"` y ese valor NO está en `valores_aprobatorios`
- **THEN** `aprobado=False`.

#### Scenario: Recálculo de aprobado al cambiar umbral
- **WHEN** un docente cambia el umbral de 60% a 70%
- **THEN** todas las calificaciones de esa asignación recalculan su campo `aprobado`.

### Requirement: Importar calificaciones desde archivo LMS
El sistema SHALL permitir importar calificaciones desde un archivo `.xlsx` o `.csv` exportado del LMS, con detección automática de columnas numéricas (sufijo `(Real)` según RN-01) y textuales (RN-02), vista previa obligatoria y selección de actividades a incluir.

#### Scenario: Preview con detección de columnas numéricas
- **WHEN** un PROFESOR sube un archivo con una columna "Parcial (Real)"
- **THEN** el sistema detecta esa columna como nota numérica y la incluye en la vista previa.

#### Scenario: Preview con columna textual
- **WHEN** un PROFESOR sube un archivo con una columna "Desempeño" con valores "Satisfactorio"
- **THEN** el sistema detecta esa columna como textual y la incluye en la vista previa.

#### Scenario: Confirmación de importación con actividades seleccionadas
- **WHEN** un PROFESOR confirma la importación seleccionando solo 2 de 5 actividades detectadas
- **THEN** el sistema persiste solo las calificaciones de las 2 actividades seleccionadas.

#### Scenario: Preview token inválido rechaza confirmación
- **WHEN** un PROFESOR intenta confirmar con un preview_token que no coincide con el hash del archivo
- **THEN** el sistema rechaza la operación con error 400.

### Requirement: Importar reporte de finalización
El sistema SHALL aceptar un reporte de finalización de actividades del LMS y cruzarlo contra las calificaciones importadas para detectar entregas finalizadas sin calificación. Solo aplica a actividades de escala textual (RN-08).

#### Scenario: Detección de entrega sin calificar
- **WHEN** un PROFESOR sube un reporte de finalización que incluye un alumno con actividad textual finalizada pero sin calificación
- **THEN** el sistema incluye esa entrega en la tabla de "posibles trabajos sin corregir".

#### Scenario: Actividad ya calificada no aparece como pendiente
- **WHEN** un PROFESOR sube un reporte de finalización que incluye un alumno con actividad textual finalizada y YA calificada
- **THEN** el sistema NO incluye esa entrega en la tabla de pendientes.

#### Scenario: Actividad numérica no se reporta como pendiente (RN-08)
- **WHEN** un PROFESOR sube un reporte de finalización que incluye un alumno con actividad numérica finalizada sin calificación
- **THEN** el sistema NO incluye esa entrega en la tabla (ausencia de nota numérica = no entregado, no pendiente).

### Requirement: Auditoría de importación
El sistema SHALL generar un registro de auditoría con código `CALIFICACIONES_IMPORTAR` en cada operación de importación de calificaciones.

#### Scenario: Audit log al importar calificaciones
- **WHEN** un PROFESOR confirma una importación de calificaciones
- **THEN** el sistema registra un evento de auditoría `CALIFICACIONES_IMPORTAR` con metadata del usuario, materia y cantidad de calificaciones.

### Requirement: Página de importación de calificaciones (frontend)
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

### Requirement: Selección de actividades en importación (frontend)
El sistema SHALL permitir al usuario seleccionar qué actividades incluir en la importación antes de confirmar.

#### Scenario: Selección de actividades en preview
- **WHEN** el preview muestra las actividades detectadas en el archivo
- **THEN** cada actividad tiene un checkbox, y el botón "Confirmar importación" solo importa las actividades seleccionadas
