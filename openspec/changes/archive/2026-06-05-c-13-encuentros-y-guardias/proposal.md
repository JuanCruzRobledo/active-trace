## Why

Con los equipos docentes configurados (C-08) y la ingesta de datos funcionando (C-09→C-12), los PROFESORES necesitan gestionar los encuentros sincrónicos con sus comisiones y registrar las guardias de atención a alumnos. Sin este módulo, los encuentros se planifican fuera del sistema (sin trazabilidad) y las guardias no tienen un registro formal. Este change implementa la planificación de encuentros recurrentes y únicos (F6.1, F6.2), la edición de instancias con registro de grabaciones (F6.3), la generación de contenido embebible para el LMS (F6.4), la vista administrativa de encuentros (F6.5) y el registro completo de guardias con exportación (F6.6).

## What Changes

- **Nuevo modelo `SlotEncuentro`**: plantilla de recurrencia semanal con día, hora, fecha de inicio, cantidad de semanas (RN-13). Soporta dos modos excluyentes: recurrente (`cant_semanas > 0`) y único (`fecha_unica`).
- **Nuevo modelo `InstanciaEncuentro`**: encuentro concreto derivado de un slot o independiente. Estado propio (Programado/Realizado/Cancelado) independiente del slot (RN-14). Almacena meet_url, video_url y comentario.
- **Nuevo modelo `Guardia`**: registro de guardia de tutor/docente con día, horario, estado (Pendiente/Realizada/Cancelada) y comentarios.
- **Endpoint de creación de slot recurrente**: `POST /api/encuentros/slots` — recibe configuración del slot y genera N instancias automáticamente.
- **Endpoint de creación de encuentro único**: `POST /api/encuentros/instancias` — crea una instancia sin slot asociado.
- **Endpoint de edición de instancia**: `PATCH /api/encuentros/instancias/{id}` — modifica estado, meet_url, video_url, comentario.
- **Endpoint de generación de contenido LMS**: `GET /api/encuentros/{materia_id}/exportar-aula` — genera bloque HTML con el calendario de encuentros.
- **Endpoint de listado de encuentros**: `GET /api/encuentros` — listado con filtros por materia, fechas, estado. Vista admin sin restricción de docente.
- **Endpoints de guardias**: CRUD `POST/GET/PATCH /api/guardias/*` — registro de guardias con filtros y exportación.
- **Permisos**: `encuentros:gestionar` (PROFESOR propio, COORDINADOR, ADMIN), `encuentros:ver-admin` (COORDINADOR, ADMIN), `guardias:registrar` (TUTOR propio, PROFESOR propio, COORDINADOR), `guardias:ver-admin` (COORDINADOR, ADMIN).
- **Audit log**: acciones `ENCUENTRO_CREAR`, `ENCUENTRO_MODIFICAR`, `GUARDIA_REGISTRAR`, `GUARDIA_MODIFICAR`.
- **Migración Alembic**: tablas `slot_encuentro`, `instancia_encuentro`, `guardia`.

## Capabilities

### New Capabilities
- `encuentros-slots`: Gestión de slots de encuentro recurrentes y únicos. Creación de slot con generación automática de instancias (RN-13). Edición y cancelación.
- `encuentros-instancias`: Gestión de instancias de encuentro individuales. Estados programado/realizado/cancelado (RN-14), registro de meet_url, video_url (grabación) y comentarios.
- `encuentros-exportacion-aula`: Generación de bloque HTML con calendario de encuentros y grabaciones, listo para embeber en el LMS (F6.4).
- `encuentros-vista-admin`: Vista transversal de todos los encuentros del tenant para supervisión de COORDINADOR/ADMIN (F6.5).
- `guardias-registro`: Registro y consulta de guardias de tutores/docentes con estados, filtros y exportación (F6.6).

### Modified Capabilities
<!-- No existing spec-level requirements change — no existing spec covers encuentros or guardias. -->

## Impact

- **Nuevos modelos**: `backend/app/models/slot_encuentro.py`, `instancia_encuentro.py`, `guardia.py` — entidades SQLAlchemy 2.0 async con tenant_id
- **Nuevos schemas Pydantic**: `backend/app/schemas/encuentros.py`, `guardias.py` — DTOs con `extra='forbid'`
- **Nuevos repositorios**: `backend/app/repositories/slot_encuentro_repository.py`, `instancia_encuentro_repository.py`, `guardia_repository.py` — queries con scope de tenant
- **Nuevo service**: `backend/app/services/encuentro_service.py`, `guardia_service.py` — lógica de generación de instancias, validación de slots, registro de guardias
- **Nuevos routers**: `backend/app/api/v1/routers/encuentros.py`, `guardias.py` — endpoints bajo `/api/encuentros/*` y `/api/guardias/*`
- **Nueva migración Alembic**: migración para tablas `slot_encuentro`, `instancia_encuentro`, `guardia`
- **Nuevos enums**: agregar `EstadoEncuentro` (Programado, Realizado, Cancelado), `EstadoGuardia` (Pendiente, Realizada, Cancelada), `DiaSemana` (Lunes–Domingo)
- **Permisos**: seed de `encuentros:gestionar`, `encuentros:ver-admin`, `guardias:registrar`, `guardias:ver-admin` en la matriz RBAC
- **Audit log**: códigos `ENCUENTRO_CREAR`, `ENCUENTRO_MODIFICAR`, `GUARDIA_REGISTRAR`, `GUARDIA_MODIFICAR`
- **Tests**: tests de integración con base real para modelos, generación de instancias, estados, scope tenant