## 1. Modelos y Migración

- [x] 1.1 Crear modelo `Evaluacion` con campos: id, tenant_id, materia_id, cohorte_id, tipo (enum: Parcial|TP|Coloquio|Recuperatorio), instancia, dias_disponibles, cupos_por_dia, fecha_inicio, fecha_fin, estado (Activa|Inactiva), soft delete mixin
- [x] 1.2 Crear modelo `ReservaEvaluacion` con campos: id, tenant_id, evaluacion_id, alumno_id, fecha_hora, estado (Activa|Cancelada), soft delete mixin
- [x] 1.3 Crear modelo `ResultadoEvaluacion` con campos: id, tenant_id, evaluacion_id, alumno_id, nota_final, soft delete mixin
- [x] 1.4 Crear migración Alembic con tablas evaluacion, reserva_evaluacion, resultado_evaluacion + índices
- [x] 1.5 Agregar relaciones SQLAlchemy entre Evaluacion → ReservaEvaluacion, Evaluacion → ResultadoEvaluacion

## 2. Pydantic Schemas

- [x] 2.1 Crear `EvaluacionCreate` (materia_id, cohorte_id, tipo, instancia, dias_disponibles, cupos_por_dia, fecha_inicio, fecha_fin)
- [x] 2.2 Crear `EvaluacionResponse` (todos los campos + métricas: convocados, reservas_activas, cupos_libres, resultados)
- [x] 2.3 Crear `ReservaCreate` (evaluacion_id, fecha_hora)
- [x] 2.4 Crear `ReservaResponse` (todos los campos + datos de alumno)
- [x] 2.5 Crear `ResultadoCreate` (evaluacion_id, alumno_id, nota_final)
- [x] 2.6 Crear `ResultadoResponse` (todos los campos)
- [x] 2.7 Crear `ImportarAlumnosRequest` (alumno_ids: list[UUID])
- [x] 2.8 Crear `MetricasColoquiosResponse` (total_convocatorias, total_alumnos_importados, reservas_activas, resultados_registrados)
- [x] 2.9 Agregar ConfigDict(extra='forbid') en todos los schemas

## 3. Repository

- [x] 3.1 Implementar `EvaluacionRepository` con métodos: create, list (con filtros por tenant/materia/cohorte/estado), get_by_id, update, close (cambiar estado + cancelar reservas activas)
- [x] 3.2 Implementar `ReservaEvaluacionRepository` con métodos: create (con control de cupo atómico), cancel, list_active_by_evaluacion, list_by_alumno, get_by_id, count_active_by_evaluacion
- [x] 3.3 Implementar `ResultadoEvaluacionRepository` con métodos: upsert, list_by_evaluacion, get_by_alumno_y_evaluacion
- [x] 3.4 Implementar tenant scope obligatorio en todos los repositorios

## 4. Service

- [x] 4.1 Implementar `ColoquioService.crear_convocatoria` — validar materia/cohorte existen, crear Evaluacion, audit log
- [x] 4.2 Implementar `ColoquioService.importar_alumnos` — asociar alumnos a convocatoria, omitir duplicados
- [x] 4.3 Implementar `ColoquioService.reservar_turno` — validar cupo con lock atómico, crear reserva, audit log
- [x] 4.4 Implementar `ColoquioService.cancelar_reserva` — validar pertenencia, cancelar, liberar cupo
- [x] 4.5 Implementar `ColoquioService.registrar_resultado` — upsert resultado, audit log
- [x] 4.6 Implementar `ColoquioService.cerrar_convocatoria` — cambiar estado, cancelar reservas activas sin resultado
- [x] 4.7 Implementar `ColoquioService.obtener_metricas` — consultas agregadas por tenant
- [x] 4.8 Implementar `ColoquioService.obtener_agenda` — listado consolidado de reservas activas

## 5. Router y Endpoints

- [x] 5.1 Crear router `/api/coloquios/convocatorias` con endpoints CRUD y guards `coloquios:gestionar`
- [x] 5.2 Crear endpoint `POST /api/coloquios/convocatorias/{id}/importar-alumnos` con guard `coloquios:gestionar`
- [x] 5.3 Crear endpoint `POST /api/coloquios/convocatorias/{id}/reservar` con guard `coloquios:reservar`
- [x] 5.4 Crear endpoint `POST /api/coloquios/reservas/{id}/cancelar` con guard `coloquios:reservar`
- [x] 5.5 Crear endpoint `POST /api/coloquios/convocatorias/{id}/resultados` con guard `coloquios:gestionar`
- [x] 5.6 Crear endpoint `POST /api/coloquios/convocatorias/{id}/cerrar` con guard `coloquios:gestionar`
- [x] 5.7 Crear endpoint `GET /api/coloquios/metricas` con guard `coloquios:ver`
- [x] 5.8 Crear endpoint `GET /api/coloquios/agenda` con guard `coloquios:ver` (scope (propias) para PROFESOR, global para COORDINADOR)
- [x] 5.9 Registrar router en app/main.py

## 6. Tests

- [x] 6.1 Tests de repositorio: CRUD Evaluacion, filtros por tenant, create/cancel reserva con control de cupo, upsert resultado
- [x] 6.2 Tests de servicio: crear convocatoria, importar alumnos (con duplicados), reserva exitosa vs sin cupo vs duplicada, cancelar, registrar resultado (upsert), cerrar (cancela reservas activas)
- [x] 6.3 Tests de router: endpoints REST con autenticación, permisos (403), flujos felices, 404 en entidades inexistentes, 409 en conflictos de reserva
- [x] 6.4 Tests de métricas: conteo correcto de convocados, reservas activas, cupos libres, resultados
- [x] 6.5 Verificar aislamiento multi-tenant en todos los tests

## 7. Permisos y Seed

- [x] 7.1 Agregar permisos `coloquios:gestionar`, `coloquios:reservar`, `coloquios:ver` al catálogo de permisos
- [x] 7.2 Mapear permisos a roles en seed script: COORDINADOR/ADMIN tienen `coloquios:gestionar`, ALUMNO tiene `coloquios:reservar`, PROFESOR/COORDINADOR tienen `coloquios:ver`
