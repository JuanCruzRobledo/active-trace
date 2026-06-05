## 1. Migración y Modelo

- [x] 1.1 Crear migración Alembic para la tabla `comunicaciones` con columnas: id (UUID), tenant_id, enviado_por_id, materia_id, destinatario (texto cifrado), asunto, cuerpo, estado (enum: Pendiente/Enviando/Enviado/Error/Cancelado), lote_id (UUID), enviado_at (nullable), creado_at
- [x] 1.2 Crear `backend/app/models/comunicacion.py` con el modelo SQLAlchemy 2.0 async y el enum `EstadoComunicacion`
- [x] 1.3 Registrar el modelo en la configuración de Alembic y verificar la migración

## 2. Schemas (DTOs)

- [x] 2.1 Crear `backend/app/schemas/comunicacion.py` con modelos Pydantic (`extra='forbid'`):
  - `PreviewRequest` — asunto, cuerpo, destinatarios
  - `PreviewResponse` — preview_token, preview_html, cantidad_destinatarios
  - `EnvioRequest` — preview_token, asunto, cuerpo, materia_id, destinatarios
  - `EnvioIndividualRequest` — preview_token, asunto, cuerpo, materia_id, entrada_padron_id
  - `ComunicacionResponse` — id, estado, destinatario, asunto, enviado_at
  - `LoteResponse` — lote_id, estado, total, enviados, fallidos, cancelados, pendientes
  - `AprobarRequest` — accion (aprobar/rechazar)
  - `MisEnviosResponse` — items, total, pagina
  - `CancelarResponse` — comunicacion_id, estado

## 3. Repository

- [x] 3.1 Crear `backend/app/repositories/comunicacion_repository.py` con `ComunicacionRepository` que implemente:
  - `crear_muchos(tenant_id, datos)` — insert masivo de N comunicaciones con el mismo lote_id
  - `listar_por_lote(tenant_id, lote_id)` — consulta comunicaciones de un lote con conteo por estado
  - `listar_pendientes_worker(tenant_id, limit)` — SELECT con FOR UPDATE SKIP LOCKED para el worker
  - `actualizar_estado(comunicacion_id, estado, enviado_at)` — update atómico de estado
  - `cancelar(comunicacion_id, usuario_id)` — cambio a Cancelado con verificación de dueño
  - `listar_por_usuario(tenant_id, usuario_id, pagina, tamano)` — historial paginado
  - `listar_lotes_pendientes_aprobacion(tenant_id)` — lotes que requieren aprobación
  - `aprobar_lote(lote_id)` / `rechazar_lote(lote_id)` — aprobación masiva

## 4. Service

- [x] 4.1 Crear `backend/app/services/comunicacion_service.py` con `ComunicacionService` que implemente:
  - `generar_preview(asunto, cuerpo, destinatarios)` — genera preview_token = hash(asunto+cuerpo+destinatarios)
  - `validar_preview(preview_token, asunto, cuerpo, destinatarios)` — verifica coincidencia de hash
  - `encolar_envio(usuario, tenant_id, preview_token, asunto, cuerpo, materia_id, destinatarios)` — valida preview, verifica alcance según rol, crea comunicaciones Pendiente
  - `encolar_envio_individual(usuario, tenant_id, preview_token, asunto, cuerpo, materia_id, entrada_padron_id)` — similar pero para 1 destinatario
  - `obtener_estado_lote(tenant_id, lote_id)` — consulta agregada
  - `obtener_mis_envios(usuario, tenant_id, pagina, tamano)` — historial
  - `cancelar_comunicacion(comunicacion_id, usuario)` — cancelación con verificación
  - `aprobar_lote(lote_id, aprobador)` — cambia estado de aprobación
  - `rechazar_lote(lote_id, aprobador)` — cancela lote completo
  - `requiere_aprobacion(tenant_id, cantidad_destinatarios)` — consulta flag del tenant

## 5. Router (Endpoints)

- [x] 5.1 Crear `backend/app/api/v1/routers/comunicaciones.py` con los endpoints:
  - `POST /api/comunicaciones/preview` — `require_permission("comunicacion:enviar")`
  - `POST /api/comunicaciones/enviar` — `require_permission("comunicacion:enviar")` con validación de alcance por rol
  - `POST /api/comunicaciones/enviar-individual` — `require_permission("comunicacion:enviar")`
  - `GET /api/comunicaciones/{lote_id}` — `require_permission("comunicacion:enviar")`
  - `PUT /api/comunicaciones/{lote_id}/aprobar` — `require_permission("comunicacion:aprobar")`
  - `GET /api/comunicaciones/mis-envios` — `require_permission("comunicacion:enviar")`
  - `POST /api/comunicaciones/{comunicacion_id}/cancelar` — `require_permission("comunicacion:enviar")`
- [x] 5.2 Registrar el router en `backend/app/api/v1/__init__.py`

## 6. Worker Asíncrono

- [x] 6.1 Crear `backend/workers/comunicaciones_worker.py` con:
  - Loop asyncio con polling periódico configurable vía `COMUNICACIONES_POLL_INTERVAL`
  - SELECT comunicaciones Pendiente con `FOR UPDATE SKIP LOCKED` (cruzando todos los tenants)
  - Llamada al `ComunicacionProvider` para cada envío
  - Update de estado a Enviado/Error según resultado
  - Graceful shutdown con signal handler (SIGTERM/SIGINT)
  - Soporte para `aprobacion_comunicaciones_requerida` desde tenant config
- [x] 6.2 Crear `backend/workers/providers/comunicacion_provider.py` con:
  - Interfaz abstracta `ComunicacionProvider` con método `async def enviar(destinatario, asunto, cuerpo) -> bool`
  - Implementación `StubComunicacionProvider` que loggea el intento y retorna True
- [x] 6.3 Crear `backend/workers/__init__.py` y `backend/workers/providers/__init__.py` para que el worker sea invocable como `python -m workers.comunicaciones_worker`

## 7. Configuración Multi-Tenant

- [x] 7.1 Agregar campo `config` (JSONB) al modelo `Tenant` con flags configurables (`aprobacion_comunicaciones_requerida`, `roles_aprobadores`)
- [x] 7.2 Crear migración 013 para agregar columna `config` a la tabla `tenant`

## 8. Auditoría

- [x] 8.1 Integrar audit log en el service: registrar `COMUNICACION_ENVIAR` al encolar con lote_id y cantidad de destinatarios
- [x] 8.2 Registrar evento de auditoría al aprobar/rechazar un lote con metadata del aprobador

## 9. Tests

- [x] 9.1 Crear `backend/tests/integration/test_comunicacion_repository.py` con tests para cada query del repositorio:
  - Test: crear_muchos persiste N comunicaciones con mismo lote_id
  - Test: listar_por_lote devuelve conteos correctos por estado
  - Test: listar_pendientes_worker usa SKIP LOCKED y no devuelve duplicados
  - Test: actualizar_estado cambia estado y registra enviado_at
  - Test: cancelar solo permite cancelar Pendientes propias
  - Test: aislamiento multi-tenant en todas las queries
- [x] 9.2 Crear `backend/tests/integration/test_comunicacion_service.py` con tests del service:
  - Test: preview genera token que coincide con hash del contenido
  - Test: validar_preview rechaza si contenido cambió
  - Test: encolar_envio con PROFESOR a alumno de su comisión → OK
  - Test: encolar_envio requiere aprobación si flag del tenant es true y múltiples destinatarios
  - Test: encolar_envio_individial NO requiere aprobación aunque flag sea true
- [x] 9.3 Crear `backend/tests/integration/test_comunicacion_router.py` con tests E2E vía cliente HTTP:
  - Test: POST /preview → 200 + preview_token
  - Test: POST /enviar con preview válido → 200 + lote_id
  - Test: POST /enviar sin acepta_terminos → 422
  - Test: POST /enviar sin permiso → 403
  - Test: GET /{lote_id} → 200 + conteos
  - Test: PUT /{lote_id}/aprobar → 200 (con permiso comunicacion:aprobar)
  - Test: PUT /{lote_id}/aprobar sin permiso → 403
  - Test: GET /mis-envios → 200 + items paginados
  - Test: POST /{lote_id}/cancelar → 200 + estado Cancelado
- [x] 9.4 Crear `backend/tests/integration/test_comunicaciones_worker.py` con tests del worker:
  - Test: procesar_comunicacion exitoso → estado Enviado
  - Test: procesar_comunicacion fallido → estado Error
  - Test: procesar_lote salta comunicaciones con necesita_aprobacion set
  - Test: procesar_lote procesa comunicaciones de lote aprobado si tenant no requiere aprobación
  - Test: sin pendientes → retorna 0
