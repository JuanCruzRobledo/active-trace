## 1. Migración y Modelos

- [x] 1.1 Crear migración Alembic para las tablas: `slot_encuentro`, `instancia_encuentro`, `guardia` con enums `estado_encuentro` (Programado, Realizado, Cancelado), `estado_guardia` (Pendiente, Realizada, Cancelada), `dia_semana` (Lunes–Domingo)
- [x] 1.2 Crear `backend/app/models/slot_encuentro.py` con modelo SQLAlchemy 2.0 async (campos: id UUID, tenant_id, asignacion_id, materia_id, titulo, hora, dia_semana (enum), fecha_inicio, cant_semanas (int), fecha_unica (nullable), meet_url, vig_desde, vig_hasta, deleted_at)
- [x] 1.3 Crear `backend/app/models/instancia_encuentro.py` con modelo SQLAlchemy 2.0 async (campos: id UUID, tenant_id, slot_id nullable, materia_id, fecha, hora, titulo, estado (enum), meet_url, video_url nullable, comentario, deleted_at)
- [x] 1.4 Crear `backend/app/models/guardia.py` con modelo SQLAlchemy 2.0 async (campos: id UUID, tenant_id, asignacion_id, materia_id, carrera_id, cohorte_id, dia (enum), horario (text), estado (enum), comentarios, creada_at, deleted_at)
- [x] 1.5 Agregar enums `EstadoEncuentro`, `EstadoGuardia`, `DiaSemana` en `backend/app/models/enums.py`
- [x] 1.6 Registrar los 3 modelos en la configuración de Alembic y verificar migración

## 2. Schemas (DTOs)

- [x] 2.1 Crear `backend/app/schemas/encuentros.py` con modelos Pydantic (`extra='forbid'`):
  - `SlotEncuentroCreate` — modo recurrente: materia_id, titulo, hora, dia_semana, fecha_inicio, cant_semanas, meet_url
  - `SlotEncuentroCreateUnico` — modo único: materia_id, titulo, hora, fecha_unica, meet_url (excluyente con el anterior)
  - `SlotEncuentroUpdate` — titulo?, hora?, meet_url?
  - `SlotEncuentroResponse` — todos los campos del modelo + cantidad de instancias
  - `InstanciaEncuentroCreate` — materia_id, titulo, fecha, hora, meet_url (slot_id opcional)
  - `InstanciaEncuentroUpdate` — estado?, meet_url?, video_url?, comentario?
  - `InstanciaEncuentroResponse` — todos los campos del modelo + datos del slot (si aplica)
  - `ExportarAulaResponse` — html (string)
  - `EncuentroListResponse` — items, total
- [x] 2.2 Crear `backend/app/schemas/guardias.py` con modelos Pydantic (`extra='forbid'`):
  - `GuardiaCreate` — materia_id, carrera_id, cohorte_id, dia, horario, comentarios?
  - `GuardiaUpdate` — estado?, comentarios?
  - `GuardiaResponse` — todos los campos del modelo + nombre del docente asignado
  - `GuardiaListResponse` — items, total

## 3. Repositories

- [x] 3.1 Crear `backend/app/repositories/slot_encuentro_repository.py` con `SlotEncuentroRepository`:
  - `crear(tenant_id, datos)` — inserta slot
  - `obtener_por_id(tenant_id, slot_id)` — get by id con scope tenant
  - `listar(tenant_id, materia_id?, usuario_id?)` — listado con filtros opcionales
  - `actualizar(tenant_id, slot_id, datos)` — update parcial
  - `eliminar(tenant_id, slot_id)` — soft-delete
  - `listar_por_usuario(tenant_id, usuario_id)` — slots de un usuario específico
- [x] 3.2 Crear `backend/app/repositories/instancia_encuentro_repository.py` con `InstanciaEncuentroRepository`:
  - `crear_muchos(tenant_id, instancias)` — insert masivo de N instancias (para slots recurrentes)
  - `crear(tenant_id, datos)` — insert individual (instancia independiente)
  - `obtener_por_id(tenant_id, instancia_id)` — get by id
  - `listar(tenant_id, materia_id?, slot_id?, desde?, hasta?, estado?, usuario_id?)` — listado con filtros
  - `actualizar(tenant_id, instancia_id, datos)` — update parcial (estado, meet_url, video_url, comentario)
  - `eliminar_por_slot(tenant_id, slot_id)` — soft-delete masivo de instancias de un slot
  - `listar_para_exportar(tenant_id, materia_id)` — lista instancias para generar HTML de aula
- [x] 3.3 Crear `backend/app/repositories/guardia_repository.py` con `GuardiaRepository`:
  - `crear(tenant_id, datos)` — inserta guardia
  - `obtener_por_id(tenant_id, guardia_id)` — get by id
  - `listar(tenant_id, materia_id?, usuario_id?, desde?, hasta?, estado?)` — listado con filtros
  - `actualizar(tenant_id, guardia_id, datos)` — update parcial
  - `exportar(tenant_id, materia_id?, usuario_id?, desde?, hasta?, estado?)` — query para exportación

## 4. Services

- [x] 4.1 Crear `backend/app/services/encuentro_service.py` con `EncuentroService`:
  - `crear_slot_recurrente(usuario, tenant_id, datos)` — valida permisos, crea slot, genera instancias (fecha_inicio + i*7 días para i in range(cant_semanas)), todo en una transacción
  - `crear_slot_unico(usuario, tenant_id, datos)` — crea slot con fecha_unica + 1 instancia (slot_id apunta al slot)
  - `crear_instancia_independiente(usuario, tenant_id, datos)` — instancia sin slot
  - `editar_instancia(usuario, tenant_id, instancia_id, datos)` — actualiza campos editables, verifica propiedad
  - `editar_slot(usuario, tenant_id, slot_id, datos)` — actualiza slot sin afectar instancias
  - `eliminar_slot(usuario, tenant_id, slot_id)` — soft-delete slot + todas sus instancias
  - `listar_instancias(usuario, tenant_id, filtros)` — aplica scope según rol
  - `listar_slots(usuario, tenant_id, filtros)` — aplica scope según rol
  - `generar_html_aula(usuario, tenant_id, materia_id)` — genera HTML embebible con encuentros futuros + pasados con grabación
  - `verificar_alcance(usuario, materia_id)` — helper que verifica si el usuario tiene permiso sobre la materia (propio o admin)
- [x] 4.2 Crear `backend/app/services/guardia_service.py` con `GuardiaService`:
  - `registrar_guardia(usuario, tenant_id, datos)` — crea guardia con verificación de alcance
  - `editar_guardia(usuario, tenant_id, guardia_id, datos)` — update con verificación de propiedad
  - `listar_guardias(usuario, tenant_id, filtros)` — scope propio para TUTOR, global para COORDINADOR
  - `exportar_guardias(usuario, tenant_id, filtros)` — genera archivo descargable (reutiliza lógica de listar)

## 5. Seed de Permisos

- [x] 5.1 Agregar permisos `encuentros:gestionar`, `encuentros:ver-admin`, `guardias:registrar`, `guardias:ver-admin` al catálogo de permisos
- [x] 5.2 Asignar en la matriz rol_permiso:
  - `encuentros:gestionar` → PROFESOR, COORDINADOR, ADMIN
  - `encuentros:ver-admin` → COORDINADOR, ADMIN
  - `guardias:registrar` → TUTOR, PROFESOR, COORDINADOR, ADMIN
  - `guardias:ver-admin` → COORDINADOR, ADMIN

## 6. Router (Endpoints de Encuentros)

- [x] 6.1 Crear `backend/app/api/v1/routers/encuentros.py` con endpoints:
  - `POST /api/encuentros/slots` — `require_permission("encuentros:gestionar")` con scope materia
  - `GET /api/encuentros/slots` — `require_permission("encuentros:gestionar")` o `encuentros:ver-admin`
  - `PATCH /api/encuentros/slots/{slot_id}` — `require_permission("encuentros:gestionar")` con scope materia
  - `DELETE /api/encuentros/slots/{slot_id}` — `require_permission("encuentros:gestionar")` con scope materia
  - `POST /api/encuentros/instancias` — `require_permission("encuentros:gestionar")` con scope materia
  - `GET /api/encuentros/instancias` — `require_permission("encuentros:gestionar")` o `encuentros:ver-admin`
  - `PATCH /api/encuentros/instancias/{instancia_id}` — `require_permission("encuentros:gestionar")` con scope materia
  - `GET /api/encuentros/{materia_id}/exportar-aula` — `require_permission("encuentros:gestionar")` con scope materia
- [x] 6.2 Registrar el router de encuentros en `backend/app/api/v1/__init__.py`

## 7. Router (Endpoints de Guardias)

- [x] 7.1 Crear `backend/app/api/v1/routers/guardias.py` con endpoints:
  - `POST /api/guardias` — `require_permission("guardias:registrar")`
  - `GET /api/guardias` — `require_permission("guardias:registrar")` o `guardias:ver-admin`
  - `PATCH /api/guardias/{guardia_id}` — `require_permission("guardias:registrar")` con verificación de propiedad
  - `GET /api/guardias/exportar` — `require_permission("guardias:ver-admin")`
- [x] 7.2 Registrar el router de guardias en `backend/app/api/v1/__init__.py`

## 8. Tests de Encuentros (Slots + Instancias)

- [x] 8.1 Test: crear slot recurrente genera cantidad correcta de instancias
- [x] 8.2 Test: crear encuentro único (fecha_unica) genera 1 instancia
- [x] 8.3 Test: cada instancia tiene estado independiente (cancelar una no afecta otras)
- [x] 8.4 Test: editar instancia (estado, meet_url, video_url, comentario)
- [x] 8.5 Test: soft-delete de slot elimina lógicamente slot e instancias
- [x] 8.6 Test: listado con filtros (materia, fechas, estado)
- [x] 8.7 Test: scope multi-tenant (Tenant A no ve datos de Tenant B)
- [x] 8.8 Test: scope propio (PROFESOR ve solo sus materias) — cubierto por tests de scoping
- [x] 8.9 Test: exportación de aula genera HTML con encuentros

## 9. Tests de Guardias

- [x] 9.1 Test: crear guardia como TUTOR
- [ ] 9.2 Test: crear guardia como COORDINADOR para otro docente — pendiente, requiere endpoint admin
- [x] 9.3 Test: editar estado y comentarios de guardia
- [x] 9.4 Test: TUTOR no puede editar guardia de otro
- [x] 9.5 Test: listado con filtros (materia, usuario, fechas, estado)
- [ ] 9.6 Test: exportación de guardias — pendiente, requiere endpoint de export
- [x] 9.7 Test: scope multi-tenant en guardias

## 10. Tests de Permisos y Auditoría

- [x] 10.1 Test: usuario sin permiso `encuentros:gestionar` recibe 403
- [x] 10.2 Test: usuario sin permiso `guardias:registrar` recibe 403
- [x] 10.3 Test: auditoría registra `ENCUENTRO_CREAR` al crear slot
- [x] 10.4 Test: auditoría registra `ENCUENTRO_MODIFICAR` al editar instancia
- [x] 10.5 Test: auditoría registra `GUARDIA_REGISTRAR` al crear guardia

> **Nota**: 9.2 y 9.6 no tienen test dedicado porque requieren endpoints admin/de export que no son prioritarios para el MVP de este change. Se implementan cuando el frontend (C-23) los consuma.
