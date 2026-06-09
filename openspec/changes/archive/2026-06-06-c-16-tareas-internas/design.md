## Context

activia-trace ya cuenta con usuarios y asignaciones (C-07), estructura académica (C-06) y el módulo de mensajería (C-12). El módulo de tareas internas completa el flujo de coordinación docente: coordinación asigna tareas a docentes, éstos las resuelven y toda la comunicación asociada queda trazada. Es un módulo de alta concurrencia (cientos de tareas simultáneas por tenant). Los actores involucrados son PROFESOR y TUTOR (asignados), COORDINADOR (gestión y supervisión) y ADMIN (visión global).

## Goals / Non-Goals

**Goals:**
- Modelar tareas internas con materia opcional, asignador, asignado, estado (Pendiente/En progreso/Resuelta/Cancelada) y contexto opcional referenciando otra entidad del dominio.
- Permitir a COORDINADOR/ADMIN/PROFESOR crear tareas y asignarlas a cualquier docente del tenant.
- Proveer timeline de tareas para el usuario autenticado: solo ve las tareas asignadas a él/ella, con filtros por estado y materia.
- Vista de administración con filtros por docente, materia, asignador, estado y búsqueda textual (COORDINADOR/ADMIN).
- Soportar cambios de estado con trazabilidad vía audit log.
- Comentarios asincrónicos por tarea para comunicación entre asignador y asignado.

**Non-Goals:**
- Notificaciones push o email al asignar/modificar una tarea (se cubre en C-12 comunicaciones).
- Tareas recurrentes o programadas (solo tareas ad-hoc).
- Archivos adjuntos en comentarios (se puede agregar en el futuro).
- Workflow de aprobación de resolución (la resolución la marca el asignado; coordinación cierra con comentarios).

## Decisions

1. **Estado como columna simple en Tarea, no entidad separada**: El estado se almacena como columna en la tabla `tarea` y se actualiza in-place. El histórico de cambios se reconstruye vía audit log (`TAREA_ESTADO_CAMBIAR`). Esto evita una tabla extra y mantiene la query de timeline simple sin JOINs innecesarios. Si en el futuro se necesita un historial de estados consultable sin audit log, se puede migrar a una tabla `tarea_estado_cambio`.

2. **Contexto como UUID polimórfico sin FK**: El campo `contexto_id` en `Tarea` referencia otra entidad del dominio (ej: un Encuentro, una Comunicacion) sin FK foráneo explícito. Esto mantiene el modelo desacoplado: no hay dependencia circular entre módulos. La validación de existencia se hace a nivel servicio cuando el contexto es requerido.

3. **Comentarios como entidad separada**: `ComentarioTarea` con relación directa a `Tarea`. No se embeden como JSONB porque los comentarios son consultados frecuentemente (cada vez que un usuario abre una tarea) y necesitan paginación futura. Una tabla separada permite queries eficientes y evita problemas de concurrencia.

4. **Permiso `tareas:gestionar` para creación y admin**: Cualquier usuario con `tareas:gestionar` puede crear tareas y ver la vista de administración (todas las tareas). Los usuarios sin el permiso solo ven las tareas asignadas a ellos. El permiso ya existe en el catálogo (`PERM_TAREAS_GESTIONAR` en `permissions.py`). Se mapea a COORDINADOR, ADMIN y PROFESOR.

5. **Transiciones de estado válidas**: Pendiente → En progreso → Resuelta. Pendiente → Cancelada. En progreso → Cancelada. No se permite retroceder de Resuelta a Pendiente (debe crearse una nueva tarea). El asignado puede cambiar el estado de sus propias tareas; los usuarios con `tareas:gestionar` pueden cambiar el estado de cualquier tarea.

6. **Materia opcional**: Una tarea puede no estar asociada a una materia (tarea institucional). Cuando tiene materia, se valida que exista en el tenant. La materia es informativa para filtros, no restrictiva.

7. **Búsqueda textual con ILIKE**: Para la búsqueda textual en la vista de administración, se usa `ILIKE` sobre `descripcion`. PostgreSQL maneja esto eficientemente con índices de tipo `gin` si se necesita en el futuro.

8. **Ordenamiento por defecto**: Las tareas se listan con las más recientes primero (`created_at DESC`). En la vista de administración, se puede ordenar por cualquier campo.

## Risks / Trade-offs

- **[Simplicidad vs histórico]** Estado in-place significa que no se puede consultar el histórico de estados sin recurrir al audit log. **Mitigación**: el audit log ya captura `TAREA_ESTADO_CAMBIAR` con timestamp y actor. Para la versión inicial es suficiente.
- **[Concurrencia]** Dos usuarios podrían cambiar el estado de la misma tarea simultáneamente. **Mitigación**: el repository usa UPDATE con `WHERE id = X AND estado_actual = Y` (optimistic locking) y verifica transiciones válidas.
- **[Performance con muchos comentarios]** Una tarea con cientos de comentarios podría afectar la carga de la tarea. **Mitigación**: los comentarios se cargan lazy vía relación SQLAlchemy. Si es necesario, se puede paginar en el futuro.
- **[Permiso granular]** Actualmente `tareas:gestionar` cubre tanto crear tareas como ver todas las tajas. Si se necesita separar (ej: un rol que pueda ver pero no crear), habría que agregar `tareas:ver`. **Mitigación**: se acepta la granularidad actual por simplicidad; se puede dividir en el futuro.
