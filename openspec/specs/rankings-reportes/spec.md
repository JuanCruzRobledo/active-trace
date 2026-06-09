## ADDED Requirements

### Requirement: Ranking de actividades aprobadas
El sistema SHALL generar un ranking de alumnos ordenado por cantidad de actividades aprobadas (descendente) para una materia+cohorte dados. Solo incluye alumnos con al menos una actividad aprobada (RN-09).

#### Scenario: Ranking incluye solo alumnos con >= 1 aprobada
- **WHEN** se genera el ranking para una materia donde algunos alumnos tienen 0 actividades aprobadas
- **THEN** el ranking solo incluye alumnos con al menos una actividad aprobada.

#### Scenario: Ranking ordenado descendente por cantidad de aprobadas
- **WHEN** se genera el ranking
- **THEN** los alumnos aparecen ordenados de mayor a menor cantidad de actividades aprobadas.

#### Scenario: Ranking muestra total de actividades por alumno
- **WHEN** se genera el ranking
- **THEN** cada entrada incluye `cantidad_aprobadas` y `total_actividades` para ese alumno.

### Requirement: Reporte rápido por materia
El sistema SHALL devolver métricas consolidadas de una materia: total de alumnos, cantidad de aprobados, cantidad de atrasados, porcentaje de aprobación y cantidad de actividades evaluables.

#### Scenario: Reporte rápido con datos completos
- **WHEN** se solicita el reporte rápido para una materia con datos importados
- **THEN** el sistema devuelve `total_alumnos`, `aprobados`, `atrasados`, `porcentaje_aprobacion` y `cantidad_actividades`.

#### Scenario: Reporte rápido sin datos importados
- **WHEN** se solicita el reporte rápido para una materia sin calificaciones importadas
- **THEN** el sistema devuelve métricas en cero (0 alumnos, 0% aprobación).

### Requirement: Notas finales agrupadas por alumno
El sistema SHALL agrupar y promediar las calificaciones de las actividades seleccionadas por alumno, calculando un promedio general y una bandera de aprobado (promedio >= umbral).

#### Scenario: Notas finales con promedio correcto
- **WHEN** se solicitan notas finales para una materia filtrando 3 actividades
- **THEN** el sistema devuelve por alumno: nombre, apellidos, promedio de las 3 actividades y si está aprobado.

#### Scenario: Notas finales con actividades específicas
- **WHEN** se solicitan notas finales con `actividades[]=Parcial1&actividades[]=Parcial2`
- **THEN** el sistema solo promedia esas dos actividades, ignorando el resto.

### Requirement: Exportar TPs sin corregir
El sistema SHALL detectar entregas finalizadas sin calificación y que sean de tipo textual (RN-08), retornando el listado de posibles TPs sin corregir para una materia+cohorte.

#### Scenario: TP textual sin calificar aparece como pendiente
- **WHEN** se consultan TPs sin corregir para una materia donde un alumno tiene una actividad textual finalizada pero sin calificación
- **THEN** el sistema incluye esa entrega en el listado de pendientes.

#### Scenario: Actividad numérica sin calificar NO aparece (RN-08)
- **WHEN** se consultan TPs sin corregir para una materia donde un alumno tiene una actividad numérica finalizada sin calificación
- **THEN** el sistema NO incluye esa entrega (ausencia de nota numérica = no entregado).

#### Scenario: Actividad ya calificada no aparece como pendiente
- **WHEN** se consultan TPs sin corregir y una actividad textual ya tiene calificación registrada
- **THEN** el sistema NO incluye esa entrega en el listado.

### Requirement: Página de ranking de actividades aprobadas (frontend)
El sistema SHALL proveer una página donde el PROFESOR vea el ranking de alumnos por actividades aprobadas.

#### Scenario: Visualizar ranking
- **WHEN** el usuario navega a `/comision/:materiaId/rankings`
- **THEN** el sistema muestra una tabla ordenada por cantidad de actividades aprobadas descendente, con columnas: alumno, actividades aprobadas, total actividades, porcentaje

#### Scenario: Ranking vacío
- **WHEN** no hay alumnos con actividades aprobadas
- **THEN** el sistema muestra un mensaje "Aún no hay datos de actividades aprobadas"

### Requirement: Página de notas finales agrupadas (frontend)
El sistema SHALL proveer una vista de notas finales calculadas por alumno.

#### Scenario: Visualizar notas finales
- **WHEN** el usuario navega a `/comision/:materiaId/rankings?view=notas-finales`
- **THEN** el sistema muestra una tabla con alumno y nota final calculada, lista para exportar

### Requirement: Página de reportes rápidos (frontend)
El sistema SHALL proveer una página con métricas consolidadas de la materia.

#### Scenario: Visualizar reportes rápidos
- **WHEN** el usuario navega a `/comision/:materiaId/reportes`
- **THEN** el sistema muestra tarjetas con métricas: total alumnos, actividades registradas, % aprobación, alumnos atrasados, alumnos al día

#### Scenario: Estado sin datos
- **WHEN** la materia no tiene datos importados
- **THEN** el sistema muestra un estado informativo "No hay datos disponibles. Importe calificaciones primero."

### Requirement: Exportar entregas sin corregir (frontend)
El sistema SHALL permitir descargar un listado de entregas pendientes de corrección.

#### Scenario: Exportar listado
- **WHEN** el usuario hace clic en "Exportar entregas sin corregir"
- **THEN** el sistema descarga un archivo CSV con el listado de entregas pendientes por alumno y actividad
