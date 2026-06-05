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
