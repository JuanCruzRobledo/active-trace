## 1. Modelos y Migración

- [x] 1.1 Crear modelo `Aviso` con campos: id, tenant_id, alcance (enum: Global|PorMateria|PorCohorte|PorRol), materia_id (nullable), cohorte_id (nullable), rol_destino (nullable), severidad (enum: Info|Advertencia|Crítico), titulo, cuerpo, inicio_en, fin_en, orden, activo, requiere_ack, soft delete mixin
- [x] 1.2 Crear modelo `AcknowledgmentAviso` con campos: id, tenant_id, aviso_id, usuario_id, confirmado_at, soft delete mixin
- [x] 1.3 Agregar enums `AlcanceAviso`, `SeveridadAviso` a `backend/app/models/enums.py`
- [x] 1.4 Crear migración Alembic 016 con tablas `aviso` y `acknowledgment_aviso` + índices + unique constraint `(aviso_id, usuario_id)` en acknowledgment
- [x] 1.5 Agregar relaciones SQLAlchemy entre Aviso → AcknowledgmentAviso (one-to-many)
- [x] 1.6 Registrar modelos en `backend/app/models/__init__.py`

## 2. Pydantic Schemas

- [x] 2.1 Crear `AvisoCreate` (alcance, materia_id opcional, cohorte_id opcional, rol_destino opcional, severidad, titulo, cuerpo, inicio_en, fin_en, orden, requiere_ack)
- [x] 2.2 Crear `AvisoUpdate` (mismos campos que create, todos opcionales salvo al menos uno requerido)
- [x] 2.3 Crear `AvisoResponse` (todos los campos + métricas: total_ack, total_usuarios_alcance, porcentaje_ack)
- [x] 2.4 Crear `AcknowledgmentCreate` (aviso_id)
- [x] 2.5 Crear `AcknowledgmentResponse` (id, aviso_id, usuario_id, confirmado_at + datos de usuario)
- [x] 2.6 Crear `AvisoListResponse` (lista de avisos con metadata de ack del usuario actual)
- [x] 2.7 Crear `TrackingAvisoResponse` (total_usuarios, total_ack, porcentaje, lista de acknowledgments)
- [x] 2.8 Agregar `ConfigDict(extra='forbid')` en todos los schemas

## 3. Repository

- [x] 3.1 Implementar `AvisoRepository` con métodos: create, list_active_by_usuario (filtrado por alcance + perfil), get_by_id, list_by_tenant (con filtros), update, soft_delete, hard_delete (solo si no tiene acknowledgments)
- [x] 3.2 Implementar `AcknowledgmentRepository` con métodos: create (con unique constraint handling), has_acknowledged, list_by_aviso, count_by_aviso
- [x] 3.3 Implementar método `count_usuarios_in_alcance` para calcular universo de destinatarios según alcance del aviso
- [x] 3.4 Implementar tenant scope obligatorio en todos los repositorios

## 4. Service

- [x] 4.1 Implementar `AvisoService.crear_aviso` — validar alcance, crear aviso, audit log `AVISO_CREAR`
- [x] 4.2 Implementar `AvisoService.editar_aviso` — validar existencia, verificar si ya tiene acknowledgments (no editar si ya se vio), audit log
- [x] 4.3 Implementar `AvisoService.eliminar_aviso` — hard delete si sin acknowledgments, soft delete si ya vieron
- [x] 4.4 Implementar `AvisoService.obtener_timeline` — avisos activos en vigencia para el usuario actual, ordenados por severidad desc → orden asc → created_at desc
- [x] 4.5 Implementar `AvisoService.acknowledge` — crear acknowledgment, validar requiere_ack, audit log `AVISO_ACK`
- [x] 4.6 Implementar `AvisoService.obtener_tracking` — conteo de acknowledgments vs universo del alcance

## 5. Router y Endpoints

- [x] 5.1 Crear router `/api/avisos` con prefix y tags
- [x] 5.2 Crear endpoint `POST /api/avisos` — crear aviso, guard `avisos:gestionar`
- [x] 5.3 Crear endpoint `GET /api/avisos` — listar avisos del tenant (con filtros), guard `avisos:gestionar`
- [x] 5.4 Crear endpoint `GET /api/avisos/{id}` — detalle de aviso, guard `avisos:ver`
- [x] 5.5 Crear endpoint `PUT /api/avisos/{id}` — editar aviso, guard `avisos:gestionar`
- [x] 5.6 Crear endpoint `DELETE /api/avisos/{id}` — eliminar aviso, guard `avisos:gestionar`
- [x] 5.7 Crear endpoint `GET /api/avisos/timeline` — timeline del usuario actual, guard `avisos:ver`
- [x] 5.8 Crear endpoint `POST /api/avisos/{id}/acknowledge` — confirmar lectura, guard `avisos:ver`
- [x] 5.9 Crear endpoint `GET /api/avisos/{id}/tracking` — tracking de acknowledgments, guard `avisos:gestionar`
- [x] 5.10 Registrar router en app/main.py

## 6. Tests

- [x] 6.1 Tests de repositorio: CRUD Aviso, filtros por tenant, timeline query con distintos alcances, create ack con unique constraint, conteo de universo
- [x] 6.2 Tests de servicio: crear aviso, editar (antes y después de acknowledgments), eliminar (hard vs soft), timeline ordenado, acknowledge exitoso vs duplicado, tracking de agregados
- [x] 6.3 Tests de router: endpoints REST con autenticación, permisos (403 en gestionar vs ver), flujos felices, 404 en entidades inexistentes
- [x] 6.4 Tests de timeline por rol: verificar que un aviso global aparece en timeline de todos, un aviso por materia solo a usuarios con esa materia
- [x] 6.5 Verificar aislamiento multi-tenant en todos los tests

## 7. Permisos y Seed

- [x] 7.1 Agregar permisos `avisos:gestionar` y `avisos:ver` al catálogo de permisos
- [x] 7.2 Mapear permisos a roles en seed script: COORDINADOR/ADMIN tienen `avisos:gestionar` + `avisos:ver`; PROFESOR/TUTOR/NEXO/FINANZAS tienen `avisos:ver`
