## Why

Coordinación y equipos docentes necesitan un mecanismo formal de seguimiento de tareas internas: asignar acciones a docentes, trackear su estado (pendiente, en progreso, resuelta, cancelada) y mantener una conversación asincrónica con comentarios. Actualmente estas tareas se gestionan por canales informales sin trazabilidad. Este change implementa el módulo de tareas internas para cubrir F8.1, F8.2 y F8.3 del catálogo de funcionalidades.

## What Changes

- Nuevos modelos `Tarea` (materia, asignado_a, asignado_por, estado, descripción, contexto opcional) y `ComentarioTarea` con su migración Alembic.
- API REST para gestión de tareas: crear, listar (propias y global con filtros), cambiar estado, agregar comentarios.
- Workflow de estado: Pendiente → En progreso → Resuelta | Cancelada, con trazabilidad de quién y cuándo cambió cada estado.
- Timeline de tareas para el docente autenticado: solo tareas asignadas a él/ella, con filtros por estado y materia.
- Vista de administración (COORDINADOR/ADMIN): todas las tareas del tenant con filtros por docente, materia, asignador, estado y búsqueda textual.
- Comentarios asincrónicos en cada tarea para comunicación entre asignador y asignado.
- RBAC con permiso `tareas:gestionar` (COORDINADOR/ADMIN/PROFESOR para gestionar).

## Capabilities

### New Capabilities
- `tareas-internas`: Gestión de tareas internas con asignación a docentes, workflow de estados por ciclo de resolución, comentarios asincrónicos, timeline personal y vista de administración con filtros.

### Modified Capabilities
- *(ninguna — no se modifican capacidades existentes)*

## Impact

- **Modelos nuevos**: `Tarea`, `ComentarioTarea` en `backend/app/models/`
- **Migración nueva**: tabla `tarea`, `comentario_tarea`
- **API nueva**: `/api/tareas/*` con endpoints CRUD, cambio de estado, comentarios
- **Permiso existente**: `tareas:gestionar` ya está en el catálogo de permisos — solo mapear a roles COORDINADOR/ADMIN/PROFESOR
- **Auditoría nueva**: `TAREA_CREAR`, `TAREA_ESTADO_CAMBIAR`, `TAREA_COMENTARIO`
- **Dependencia**: C-07 (usuarios) — necesario para relación con `Usuario`
