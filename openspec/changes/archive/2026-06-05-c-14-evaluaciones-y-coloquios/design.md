## Context

Activia-trace ya cuenta con los módulos de estructura académica (C-06), usuarios y asignaciones (C-07), encuentros (C-13) y calificaciones (C-10). El módulo de coloquios completa el ciclo de evaluaciones orales: desde la convocatoria y reserva de turnos hasta el registro de resultados. Los actores involucrados son COORDINADOR/ADMIN (gestión), PROFESOR (importación de candidatos y registro de notas) y ALUMNO (reserva de turno).

## Goals / Non-Goals

**Goals:**
- Modelar convocatorias de coloquio con materia, cohorte, instancia y días disponibles con cupo.
- Permitir al COORDINADOR/ADMIN importar alumnos habilitados a una convocatoria.
- Permitir al ALUMNO reservar turno en un día con cupo disponible.
- Proveer panel de métricas (convocados, reservas, cupos libres, notas registradas).
- Proveer agenda consolidada de reservas para COORDINADOR/ADMIN.
- Registrar resultados (nota final) por alumno.

**Non-Goals:**
- enviar notificaciones automáticas (se cubre en C-12 comunicaciones).
- Integración con Moodle para sincronización de coloquios (futuro).
- Time slots específicos dentro de un día (la reserva es por día completo).
- Calendario visual (se hará en frontend C-23).

## Decisions

1. **Reserva por día con cupo, no por time slot**: La convocatoria define N días con cupo máximo por día. El alumno elige un día. Esto simplifica el modelo y cubre el caso de uso real (el coordinador asigna franjas manualmente después).

2. **Importación de alumnos desde usuarios existentes**: No es subida de archivo como en C-09. El COORDINADOR selecciona alumnos del padrón (Usuarios con rol ALUMNO asociados a la materia/cohorte). Se implementa como un endpoint que recibe una lista de `alumno_id`.

3. **Cupo como columna en la convocatoria, no entidad separada**: `Evaluacion.dias_disponibles` define la ventana. Los cupos por día se modelan implícitamente: al crear la convocatoria se definen `cupos_por_dia` y se calculan turnos disponibles = `cupos_por_dia × dias_disponibles - reservas_activas`.

4. **Estados de reserva**: Solo Activa y Cancelada. No hay estado "Pendiente" ni "Confirmada" — la reserva es inmediata si hay cupo. Esto evita complejidad de expiración de reservas.

5. **Sin entidad "convocatoria" separada**: Evaluacion es la convocatoria misma. El campo `instancia` sirve como nombre (ej. "Coloquio Final"). No se necesita una tabla aparte.

6. **ResultadoEvaluacion como entidad independiente**: No es un atributo de ReservaEvaluacion porque puede existir resultado sin reserva (ej. alumno eximido) y porque un alumno puede rendir sin haber reservado (casos administrativos).

## Risks / Trade-offs

- **[Simplicidad vs flexibilidad]** No modelar time slots dentro del día es más simple pero obliga al coordinador a gestionar la asignación horaria fuera del sistema. → Mitigación: este es un MVP; time slots se pueden agregar como entidad separada en el futuro.
- **[Concurrencia]** Dos alumnos podrían reservar el último cupo casi simultáneamente. → Mitigación: usar `SELECT ... FOR UPDATE` o decremento atómico con check de cupo > 0 en la transacción de reserva.
- **[Datos existentes]** Al cerrar una convocatoria, las reservas activas sin resultado quedan huérfanas. → Regla: al cerrar, las reservas activas pasan automáticamente a Cancelada.
