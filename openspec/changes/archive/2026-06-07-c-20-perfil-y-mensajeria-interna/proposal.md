## Why

Todo usuario autenticado necesita gestionar su propia identidad y comunicarse con otros usuarios del sistema. Hoy el perfil solo puede editarlo un ADMIN vía `/api/admin/usuarios` (C-07) y no existe mensajería interna entre usuarios registrados — la entidad `Comunicacion` (C-12) solo modela emails salientes a alumnos. Este change cubre la Épica 11 del catálogo (F11.1 editar perfil propio, F11.2 bandeja de mensajes, F11.3 cierre de sesión) y el flujo FL-10 (mensajería interna entre usuarios), todos para self-service del usuario autenticado.

## What Changes

- **Perfil propio (F11.1)**: nuevo endpoint self-scoped `GET /api/perfil` y `PATCH /api/perfil` que opera SIEMPRE sobre el usuario del JWT (nunca por id en URL). Campos editables: nombre, apellidos, identificación fiscal secundaria, banco, CBU/alias, regional, email, modalidad de cobro (`facturador`), legajo profesional. El **CUIL es de solo lectura** — se devuelve enmascarado pero no se puede modificar.
- **Mensajería interna (F3.4, F11.2, FL-10)**: nuevos modelos `MensajeHilo` y `Mensaje` con su migración Alembic. Endpoints `/api/inbox/*` para listar hilos recibidos, leer un hilo completo y responder dentro del hilo. La mensajería es entre usuarios registrados, paralela y separada de las comunicaciones a alumnos.
- **Cierre de sesión (F11.3)**: se documenta como reuso del `POST /api/auth/logout` ya implementado en C-03. **No requiere código nuevo.**
- **Auditoría**: nuevos códigos `PERFIL_EDITAR`, `MENSAJE_ENVIAR`.
- **Aislamiento**: todos los endpoints respetan `tenant_id` y la identidad del JWT; el inbox solo expone los hilos donde el usuario es participante.

## Capabilities

### New Capabilities
- `perfil-propio`: Gestión self-service del perfil del usuario autenticado — lectura y edición de campos editables con CUIL de solo lectura, identidad siempre derivada del JWT, PII enmascarada en respuestas.
- `mensajeria-interna`: Bandeja de mensajes entre usuarios registrados del tenant — hilos de conversación, lectura de hilos recibidos y respuesta dentro del hilo, aislamiento por participante y tenant.

### Modified Capabilities
- *(ninguna — F11.3 reusa `auth-jwt` logout sin cambios de requisito; `user-management` no se modifica, el perfil es un endpoint nuevo self-scoped)*

## Impact

- **Modelos nuevos**: `MensajeHilo`, `Mensaje` en `backend/app/models/`
- **Migración nueva**: `021_perfil_y_mensajeria.py` — tablas `mensaje_hilo`, `mensaje`
- **API nueva**: `/api/perfil` (router `perfil.py`), `/api/inbox/*` (router `inbox.py`)
- **Schemas nuevos**: `backend/app/schemas/perfil.py`, `backend/app/schemas/mensajeria.py`
- **Services nuevos**: `PerfilService`, `MensajeriaService`
- **Repos nuevos**: `MensajeHiloRepository`, `MensajeRepository`
- **Auditoría nueva**: `PERFIL_EDITAR`, `MENSAJE_ENVIAR` en `audit_service.py` + `VALID_ACCION_CODES`
- **Reuso sin cambios**: `POST /api/auth/logout` (C-03), modelo `Usuario` (C-07), `mask_*` (C-07 PII)
- **Dependencia**: C-07 (usuarios-y-asignaciones) — `Usuario` es el participante de hilos y el sujeto del perfil
- **Governance**: BAJO — CRUDs self-service sobre datos del propio usuario, sin lógica de billing/auth crítica
