## 1. Modelos y Migración (Mensajería)

- [x] 1.1 Crear modelo `MensajeHilo` (BaseMixin) con campos: id, tenant_id, asunto, usuario_a (FK usuario), usuario_b (FK usuario)
- [x] 1.2 Crear modelo `Mensaje` (append-only: id, tenant_id, hilo_id FK, autor_id FK usuario, cuerpo, creado_at, leido_at nullable) — sin updated_at ni deleted_at
- [x] 1.3 Agregar relaciones SQLAlchemy: MensajeHilo ↔ Mensaje (one-to-many, lazy selectin), Mensaje ↔ Usuario (autor)
- [x] 1.4 Registrar modelos en `backend/app/models/__init__.py`
- [x] 1.5 Crear migración Alembic `021_perfil_y_mensajeria.py` con tablas `mensaje_hilo`, `mensaje` + índices (tenant_id, hilo_id, participantes) + FK constraints

## 2. Pydantic Schemas

- [x] 2.1 Crear `backend/app/schemas/perfil.py`: `PerfilResponse` (campos del usuario con PII enmascarada, incluye cuil read-only), `PerfilUpdate` (campos editables — SIN cuil; con `ConfigDict(extra="forbid")`)
- [x] 2.2 Crear `backend/app/schemas/mensajeria.py`: `HiloCreate` (destinatario_id, asunto, cuerpo), `MensajeCreate` (cuerpo), `MensajeResponse`, `HiloResponse` (asunto + participantes + flag no_leidos), `HiloConMensajesResponse`, `HiloListResponse` (items + total) — todos con `ConfigDict(extra="forbid")`

## 3. Repositories

- [x] 3.1 Tests `MensajeHiloRepository`: create, get_by_id (tenant scope), list_by_participante (orden por último mensaje DESC), filtro de participación (usuario_a OR usuario_b), aislamiento cross-tenant
- [x] 3.2 Implementar `MensajeHiloRepository` para pasar 3.1
- [x] 3.3 Tests `MensajeRepository`: create (append-only), list_by_hilo (orden ASC), marcar_leido, derivar hilos con no-leídos (EXISTS), tenant scope
- [x] 3.4 Implementar `MensajeRepository` para pasar 3.3

## 4. Services

- [x] 4.1 Tests `PerfilService`: obtener_mio (resuelve usuario por JWT id dual), actualizar_mio (solo campos editables, ignora identidad de URL), audit `PERFIL_EDITAR`, aislamiento tenant
- [x] 4.2 Implementar `PerfilService` para pasar 4.1 (reusa modelo Usuario + mask_*; excluye cuil/estado/legajo administrativo del set editable)
- [x] 4.3 Tests `MensajeriaService`: crear_hilo (valida destinatario en tenant), responder (valida participación, audit `MENSAJE_ENVIAR`), obtener_hilo (verifica participación o 404), listar_inbox (solo hilos propios), marcar_leido, no-participante denegado
- [x] 4.4 Implementar `MensajeriaService` para pasar 4.3

## 5. Auditoría

- [x] 5.1 Agregar `ACCION_PERFIL_EDITAR = "PERFIL_EDITAR"` y `ACCION_MENSAJE_ENVIAR = "MENSAJE_ENVIAR"` a `audit_service.py` + agregarlos a `VALID_ACCION_CODES`
- [x] 5.2 Verificar que `PERFIL_EDITAR` registra solo nombres de campos cambiados (nunca valores PII en claro)

## 6. Routers y Endpoints

- [x] 6.1 Tests router perfil: `GET /api/perfil` self-scoped (ignora `?usuario_id=`), `PATCH /api/perfil` parcial, 422 al enviar `cuil`, PII enmascarada, auth requerida
- [x] 6.2 Crear router `backend/app/api/v1/routers/perfil.py` (prefix `/api/perfil`) con `GET` y `PATCH`, identidad resuelta del JWT (helper `_resolve_usuario_id`)
- [x] 6.3 Tests router inbox: `GET /api/inbox` (solo propios), `GET /api/inbox/{id}` (participante OK / no-participante 404 / inexistente 404), `POST /api/inbox` crear hilo, `POST /api/inbox/{id}/mensajes` responder, no-participante 404 al responder
- [x] 6.4 Crear router `backend/app/api/v1/routers/inbox.py` (prefix `/api/inbox`) con listar, leer hilo, crear hilo, responder; rutas estáticas antes de `/{hilo_id}`
- [x] 6.5 Registrar ambos routers en el agregador de `backend/app/api/v1/routers/__init__.py` / `main.py`

## 7. Cierre de sesión (reuso C-03)

- [x] 7.1 Test de humo: `POST /api/auth/logout` sigue revocando el refresh token del usuario autenticado (verifica reuso F11.3 — NO reimplementar logout)

## 8. Tests de integración y aislamiento

- [x] 8.1 Test end-to-end perfil: usuario edita banco/regional → relee → cambios persisten; intento de editar cuil → 422
- [x] 8.2 Test end-to-end mensajería: usuario A crea hilo a B → B lo ve en su inbox → B responde → A ve la respuesta en el hilo
- [x] 8.3 Test de aislamiento cross-tenant: perfil e inbox de tenant A nunca exponen datos de tenant B
- [x] 8.4 Test de aislamiento cross-usuario: usuario no participante recibe 404 al leer/responder un hilo ajeno
