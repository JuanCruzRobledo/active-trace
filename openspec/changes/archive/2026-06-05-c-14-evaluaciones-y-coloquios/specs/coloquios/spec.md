# Coloquios

> Gestión de convocatorias de coloquio, reserva de turnos, registro de resultados y métricas.

## ADDED Requirements

### Requirement: Crear convocatoria de coloquio
El sistema SHALL permitir al COORDINADOR/ADMIN crear una convocatoria de coloquio especificando materia, cohorte, nombre de instancia, días disponibles y cupos por día.

#### Scenario: Creación exitosa
- **WHEN** el COORDINADOR envía materia_id, cohorte_id, instancia="Coloquio Final", dias_disponibles=5, cupos_por_dia=10
- **THEN** el sistema crea una Evaluacion con estado activa y retorna sus datos

#### Scenario: Creación sin materia inexistente
- **WHEN** el COORDINADOR envía un materia_id que no existe en el tenant
- **THEN** el sistema retorna 404

#### Scenario: Creación sin permiso
- **WHEN** un ALUMNO intenta crear una convocatoria
- **THEN** el sistema retorna 403

### Requirement: Listar convocatorias
El sistema SHALL listar las convocatorias de coloquio con métricas: total de alumnos cargados, instancias activas, reservas activas y notas registradas.

#### Scenario: Listado exitoso
- **WHEN** el COORDINADOR solicita el listado de convocatorias
- **THEN** el sistema retorna todas las convocatorias del tenant con sus métricas (convocados, reservas activas, cupos libres)

#### Scenario: Filtro por materia
- **WHEN** el COORDINADOR solicita convocatorias filtradas por materia_id
- **THEN** el sistema retorna solo las convocatorias de esa materia

### Requirement: Importar alumnos a convocatoria
El sistema SHALL permitir al COORDINADOR/ADMIN importar una lista de alumnos habilitados para una convocatoria de coloquio.

#### Scenario: Importación exitosa
- **WHEN** el COORDINADOR envía evaluacion_id y una lista de alumno_ids
- **THEN** el sistema asocia esos alumnos a la convocatoria y retorna la lista de importados

#### Scenario: Alumno duplicado
- **WHEN** el COORDINADOR importa un alumno que ya está en la convocatoria
- **THEN** el sistema omite el duplicado sin error y retorna los importados nuevos

#### Scenario: Convocatoria inexistente
- **WHEN** el COORDINADOR envía un evaluacion_id que no existe
- **THEN** el sistema retorna 404

### Requirement: Reservar turno de coloquio
El sistema SHALL permitir al ALUMNO reservar un turno en un día disponible con cupo.

#### Scenario: Reserva exitosa
- **WHEN** el ALUMNO envía evaluacion_id y una fecha_hora dentro de los días disponibles
- **THEN** el sistema crea una ReservaEvaluacion con estado Activa, decrementa el cupo disponible y retorna la reserva

#### Scenario: Reserva sin cupo
- **WHEN** el ALUMNO intenta reservar en un día sin cupo disponible
- **THEN** el sistema retorna 409 Conflict y no crea la reserva

#### Scenario: Reserva duplicada
- **WHEN** el ALUMNO intenta reservar un turno en una convocatoria donde ya tiene una reserva Activa
- **THEN** el sistema retorna 409 Conflict

#### Scenario: Reserva fuera de ventana
- **WHEN** el ALUMNO intenta reservar fuera de los días disponibles de la convocatoria
- **THEN** el sistema retorna 422

#### Scenario: Reserva sin permiso
- **WHEN** un PROFESOR intenta reservar un turno (sin permiso coloquios:reservar)
- **THEN** el sistema retorna 403

### Requirement: Cancelar reserva
El sistema SHALL permitir al ALUMNO cancelar su propia reserva activa.

#### Scenario: Cancelación exitosa
- **WHEN** el ALUMNO cancela su reserva activa
- **THEN** el sistema cambia el estado a Cancelada y libera el cupo

#### Scenario: Cancelación de reserva inexistente
- **WHEN** el ALUMNO intenta cancelar una reserva que no le pertenece
- **THEN** el sistema retorna 404

### Requirement: Registrar resultado de coloquio
El sistema SHALL permitir al PROFESOR/COORDINADOR registrar la nota final de un alumno en una convocatoria.

#### Scenario: Registro exitoso
- **WHEN** el PROFESOR envía evaluacion_id, alumno_id y nota_final="Aprobado"
- **THEN** el sistema crea un ResultadoEvaluacion y lo retorna

#### Scenario: Resultado duplicado
- **WHEN** el PROFESOR intenta registrar un resultado para un alumno que ya tiene resultado en esa evaluación
- **THEN** el sistema actualiza el resultado existente (upsert)

### Requirement: Cerrar convocatoria
El sistema SHALL permitir al COORDINADOR/ADMIN cerrar una convocatoria activa.

#### Scenario: Cierre exitoso
- **WHEN** el COORDINADOR cierra una convocatoria activa
- **THEN** el sistema marca la Evaluacion como inactiva y cancela todas las reservas activas sin resultado

#### Scenario: Cierre de convocatoria ya cerrada
- **WHEN** el COORDINADOR intenta cerrar una convocatoria ya inactiva
- **THEN** el sistema retorna 409 Conflict

### Requirement: Panel de métricas de coloquios
El sistema SHALL exponer métricas agregadas: total de alumnos cargados, instancias activas, reservas activas, notas registradas.

#### Scenario: Métricas globales
- **WHEN** el COORDINADOR solicita el panel de métricas
- **THEN** el sistema retorna: total_convocatorias, total_alumnos_importados, reservas_activas, resultados_registrados

#### Scenario: Métricas por convocatoria
- **WHEN** el COORDINADOR solicita métricas de una convocatoria específica
- **THEN** el sistema retorna: convocados, reservas_activas, cupos_libres, resultados_registrados

### Requirement: Agenda consolidada de reservas
El sistema SHALL exponer una agenda consolidada de todas las reservas activas para COORDINADOR/ADMIN.

#### Scenario: Agenda global
- **WHEN** el COORDINADOR solicita la agenda de reservas
- **THEN** el sistema retorna todas las reservas activas con datos de alumno, materia, cohorte, fecha_hora

#### Scenario: Filtro por convocatoria
- **WHEN** el COORDINADOR solicita la agenda filtrada por evaluacion_id
- **THEN** el sistema retorna solo las reservas de esa convocatoria
