## 1. Modelos y Migración

- [x] 1.1 Crear modelo `Tarea` con campos: id, tenant_id, materia_id (nullable), asignado_a, asignado_por, estado (enum), descripcion, contexto_id (nullable), soft delete mixin
- [x] 1.2 Crear modelo `ComentarioTarea` con campos: id, tenant_id, tarea_id, autor_id, texto, creado_at (sin updated_at ni deleted_at — es append-only)
- [x] 1.3 Agregar enum `EstadoTarea` a `backend/app/models/enums.py`: Pendiente, En progreso, Resuelta, Cancelada
- [x] 1.4 Crear migración Alembic 017 con tablas `tarea` y `comentario_tarea` + índices + FK constraints
- [x] 1.5 Agregar relaciones SQLAlchemy entre Tarea ↔ ComentarioTarea (one-to-many) y Tarea ↔ Usuario (asignado_a, asignado_por)
- [x] 1.6 Registrar modelos en `backend/app/models/__init__.py`

## 2. Pydantic Schemas

- [x] 2.1 Crear `TareaCreate` (materia_id opcional, asignado_a, descripcion, contexto_id opcional)
- [x] 2.2 Crear `TareaUpdate` (todos los campos de create opcionales)
- [x] 2.3 Crear `TareaEstadoUpdate` (nuevo_estado)
- [x] 2.4 Crear `TareaResponse` (todos los campos del modelo + created_at, updated_at)
- [x] 2.5 Crear `ComentarioCreate` (texto)
- [x] 2.6 Crear `ComentarioResponse` (id, tarea_id, autor_id, texto, creado_at + datos de autor)
- [x] 2.7 Crear `TareaConComentariosResponse` (tarea + lista de comentarios)
- [x] 2.8 Crear `TareaListResponse` (items + total)
- [x] 2.9 Agregar `ConfigDict(extra='forbid')` en todos los schemas

## 3. Repository

- [x] 3.1 Implementar `TareaRepository` con métodos: create, get_by_id (con tenant scope), list_by_asignado (filtros estado/materia), list_by_tenant (filtros combinables + búsqueda textual), update_estado, update (partial)
- [x] 3.2 Implementar `ComentarioRepository` con métodos: create, list_by_tarea (orden cronológico ASC)
- [x] 3.3 Implementar tenant scope obligatorio en todos los repositorios

## 4. Service

- [x] 4.1 Implementar `TareaService.crear_tarea` — validar asignado existe en el tenant, crear tarea, audit log `TAREA_CREAR`
- [x] 4.2 Implementar `TareaService.cambiar_estado` — validar transición según workflow (Pend→Progreso→Resuelta, Pend/Cancel, Progreso/Cancel), audit log `TAREA_ESTADO_CAMBIAR`
- [x] 4.3 Implementar `TareaService.agregar_comentario` — validar tarea existe y usuario tiene acceso, crear comentario, audit log `TAREA_COMENTARIO`
- [x] 4.4 Implementar `TareaService.obtener_tarea` — con verificación de acceso (asignado o `tareas:gestionar`)
- [x] 4.5 Implementar `TareaService.listar_mias` — timeline del usuario autenticado con filtros
- [x] 4.6 Implementar `TareaService.listar_todas` — vista admin con filtros combinables

## 5. Router y Endpoints

- [x] 5.1 Crear router `/api/tareas` con prefix y tags
- [x] 5.2 Crear endpoint `POST /api/tareas` — crear tarea, guard `tareas:gestionar`
- [x] 5.3 Crear endpoint `GET /api/tareas/mias` — timeline del usuario, sin permiso especial (implícito por ser el asignado)
- [x] 5.4 Crear endpoint `GET /api/tareas` — listar todas (admin), guard `tareas:gestionar`
- [x] 5.5 Crear endpoint `GET /api/tareas/{id}` — detalle con comentarios, verifica acceso
- [x] 5.6 Crear endpoint `PATCH /api/tareas/{id}/estado` — cambiar estado, verifica acceso
- [x] 5.7 Crear endpoint `POST /api/tareas/{id}/comentarios` — agregar comentario, verifica acceso
- [x] 5.8 Registrar router en app/main.py

## 6. Tests

- [x] 6.1 Tests de repositorio: CRUD Tarea, filtros por tenant, listar por asignado, listar admin con filtros, búsqueda textual, crear comentario
- [x] 6.2 Tests de servicio: crear tarea, cambiar estado (transiciones válidas e inválidas), agregar comentario, verificar acceso (asignado vs no asignado vs admin)
- [x] 6.3 Tests de router: endpoints REST con autenticación, permisos (403 en gestionar), flujos felices, 404 en tareas inexistentes
- [x] 6.4 Tests de timeline: verificar que un usuario ve solo sus tareas, filtros por estado/materia
- [x] 6.5 Verificar aislamiento multi-tenant en todos los tests

## 7. Auditoría y Seed

- [x] 7.1 Agregar constantes `ACCION_TAREA_CREAR`, `ACCION_TAREA_ESTADO_CAMBIAR`, `ACCION_TAREA_COMENTARIO` a audit_service.py + `VALID_ACCION_CODES`
- [x] 7.2 Verificar que `PERM_TAREAS_GESTIONAR` existe en permissions.py y está en PERMISOS_CATALOGO
- [x] 7.3 Mapear `tareas:gestionar` a roles COORDINADOR, ADMIN y PROFESOR en seed script
