## 1. AuditoriaService — Capa de servicio

- [x] 1.1 Crear `backend/app/services/auditoria_service.py` con clase `AuditoriaService` (inyección: `AuditLogRepository`, `ComunicacionRepository`, `AsignacionRepository`, `UsuarioRepository` via `DbSession`)
- [x] 1.2 Implementar `acciones_por_dia(filtros)` con `func.date_trunc('day', AuditLog.fecha_hora)`, `func.count()`, GROUP BY, filtros por rango de fechas y materia_id
- [x] 1.3 Implementar `comunicaciones_por_docente(filtros)` con GROUP BY `Comunicacion.actor_id`, conteo por estado (Pendiente/Enviando/OK/Fallido/Cancelado), join con Usuario para nombre, filtros por materia y fechas
- [x] 1.4 Implementar `interacciones_por_docente_materia(filtros)` con GROUP BY `AuditLog.actor_id, AuditLog.materia_id`, conteo por `accion`, join con Usuario y Materia, filtro por fechas
- [x] 1.5 Implementar `ultimas_acciones(limit=200)` con límite configurable (techo duro 1000), ordenado por `fecha_hora DESC`, join con Usuario y Materia para nombres
- [x] 1.6 Implementar `log_completo(filtros, offset, limit)`: lista paginada con filtros combinables (fecha_desde, fecha_hasta, materia_id, usuario_id, accion), ordenado por `fecha_hora DESC`, incluyendo `count(*)` total sin paginación
- [x] 1.7 Implementar helper `_scope_materias(user, db)` que retorna lista de materia_ids si el usuario es COORDINADOR (scope propio), o None si es ADMIN

## 2. Schemas Pydantic — DTOs de request/response

- [x] 2.1 Crear `backend/app/schemas/auditoria.py` con `AccionesPorDiaItem(fecha: date, total: int)`
- [x] 2.2 Crear `ComunicacionesPorDocenteItem(usuario_id, nombre, Pendiente, Enviando, OK, Fallido, Cancelado)` con `extra='forbid'`
- [x] 2.3 Crear `InteraccionesItem(usuario_id, nombre, materia_id, materia_nombre, acciones: dict[str, int], total: int)` con `extra='forbid'`
- [x] 2.4 Crear `UltimasAccionesItem(id, fecha_hora, actor_nombre, accion, materia_nombre, detalle, ip)` con `extra='forbid'`
- [x] 2.5 Crear `LogItem(id, fecha_hora, actor_id, actor_nombre, materia_id, materia_nombre, accion, detalle, filas_afectadas, ip, user_agent)` con `extra='forbid'`
- [x] 2.6 Crear `LogPaginado(items: list[LogItem], total: int, offset: int, limit: int)` con `extra='forbid'`
- [x] 2.7 Crear `FiltrosAuditoria(fecha_desde, fecha_hasta, materia_id, usuario_id, accion)` con todos opcionales y `extra='forbid'`

## 3. Router — Endpoints REST

- [x] 3.1 Crear `backend/app/api/v1/routers/auditoria.py` con router prefix `/api/auditoria`, tag `Auditoría`
- [x] 3.2 Implementar `GET /acciones-por-dia` con `require_permission("auditoria:ver")` y scope propio para COORDINADOR
- [x] 3.3 Implementar `GET /comunicaciones-por-docente` con `require_permission("auditoria:ver")` y scope propio
- [x] 3.4 Implementar `GET /interacciones-por-docente-materia` con `require_permission("auditoria:ver")` y scope propio
- [x] 3.5 Implementar `GET /ultimas-acciones` con `require_permission("auditoria:ver")`, query param `limit` (default 200, max 1000), scope propio
- [x] 3.6 Implementar `GET /log` con `require_permission("auditoria:ver")`, guard adicional `require_role("ADMIN")`, query params de filtros + paginación (`offset`, `limit` default 50)
- [x] 3.7 Wire el router en `backend/app/api/v1/__init__.py` o donde se registren los routers existentes

## 4. Tests de integración

- [x] 4.1 Escribir tests para `GET /api/auditoria/acciones-por-dia`: sin filtros, con rango fechas, con materia_id, scope propio COORDINADOR
- [x] 4.2 Escribir tests para `GET /api/auditoria/comunicaciones-por-docente`: distribución de estados, filtro por materia, por fechas, scope propio
- [x] 4.3 Escribir tests para `GET /api/auditoria/interacciones-por-docente-materia`: agregación por tipo de acción, con fechas, scope propio
- [x] 4.4 Escribir tests para `GET /api/auditoria/ultimas-acciones`: límite default (200), límite explícito, techo duro (1000), scope propio
- [x] 4.5 Escribir tests para `GET /api/auditoria/log`: paginación, filtros combinables, acceso ADMIN ok, acceso COORDINADOR → 403, acceso FINANZAS → 403
- [x] 4.6 Escribir tests para scope propio: crear datos de dos materias distintas, asignar COORDINADOR solo a una, verificar que solo ve datos de su materia
- [x] 4.7 Ejecutar suite completa y verificar que no hay regresiones (tests existentes + nuevos)
