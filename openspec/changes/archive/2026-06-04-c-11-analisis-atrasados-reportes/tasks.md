## 1. Schemas (DTOs)

- [x] 1.1 Crear `backend/app/schemas/analisis.py` con modelos Pydantic (`extra='forbid'`) para request/response de todos los endpoints de análisis:
  - `AtrasadosResponse` — lista de alumnos atrasados + total + porcentaje
  - `RankingResponse` — ranking de actividades aprobadas (`RankingEntry` con alumno, cantidad_aprobadas, total_actividades)
  - `ReporteResponse` — métricas rápidas (total_alumnos, aprobados, atrasados, porcentaje, actividades)
  - `NotasFinalesResponse` — notas agrupadas por alumno (`NotaFinalEntry` con promedio, aprobado)
  - `TpsPendientesResponse` — lista de TPs sin corregir (`TpPendienteEntry`)
  - `MonitorGeneralResponse` — vista transversal con alumnos y estado de actividades
  - `MonitorSeguimientoEntry` — entrada individual de monitor con filtros

## 2. Repository (queries de agregación)

- [x] 2.1 Crear `backend/app/repositories/analisis_repository.py` con `AnalisisRepository` que implemente:
  - `listar_atrasados(materia_id, cohorte_id, comision)` — obtiene alumnos + calificaciones + umbral para clasificar
  - `ranking_aprobados(materia_id, cohorte_id, comision)` — cuenta actividades aprobadas por alumno (≥1)
  - `reporte_rapido(materia_id, cohorte_id)` — agregaciones: count alumnos, avg aprobación, count actividades
  - `notas_finales(materia_id, cohorte_id, comision, actividades)` — promedio por alumno de actividades seleccionadas
  - `tps_sin_corregir(materia_id, cohorte_id, comision)` — cruce reporte finalización vs calificaciones (solo textuales)
  - `monitor_general(tenant_id, materia_id, regional, comision, estado, q)` — query transversal con filtros
  - `monitor_seguimiento(usuario_id, filtros)` — query acotada a asignaciones del tutor/profesor

## 3. Service (lógica de negocio)

- [x] 3.1 Crear `backend/app/services/analisis_service.py` con `AnalisisService` que implemente:
  - `obtener_atrasados(materia_id, cohorte_id, comision)` — clasifica alumnos según RN-06
  - `obtener_ranking(materia_id, cohorte_id, comision)` — ranking con filtro RN-09
  - `obtener_reporte_rapido(materia_id, cohorte_id)` — consolida métricas
  - `obtener_notas_finales(materia_id, cohorte_id, comision, actividades)` — promedio por alumno, bandera aprobado
  - `obtener_tps_sin_corregir(materia_id, cohorte_id, comision)` — listado detección RN-07/08
  - `obtener_monitor_general(filtros)` — orquesta filtros y scope según rol
  - `obtener_monitor_seguimiento(usuario_id, filtros)` — orquesta scope del tutor/profesor

## 4. Router (endpoints)

- [x] 4.1 Crear `backend/app/api/v1/routers/analisis.py` con los endpoints:
  - `GET /api/analisis/atrasados` — `require_permission("atrasados:ver")` → `AnalisisService.obtener_atrasados()`
  - `GET /api/analisis/ranking` — `require_permission("atrasados:ver")` → `AnalisisService.obtener_ranking()`
  - `GET /api/analisis/reporte-rapido` — `require_permission("atrasados:ver")` → `AnalisisService.obtener_reporte_rapido()`
  - `GET /api/analisis/notas-finales` — `require_permission("atrasados:ver")` → `AnalisisService.obtener_notas_finales()`
  - `GET /api/analisis/tps-sin-corregir` — `require_permission("atrasados:ver")` → `AnalisisService.obtener_tps_sin_corregir()`
  - `GET /api/analisis/monitor-general` — `require_permission("atrasados:ver")` → COORDINADOR/ADMIN scope
  - `GET /api/analisis/monitor-seguimiento` — `require_permission("atrasados:ver")` → scope según rol (TUTOR/PROFESOR vs COORDINADOR/ADMIN)
- [x] 4.2 Registrar el router en `backend/app/api/v1/__init__.py`

## 5. Tests

- [x] 5.1 Crear `backend/tests/integration/test_analisis_repository.py` con tests para cada query del repositorio:
  - Test: listar atrasados identifica alumnos con actividad faltante
  - Test: listar atrasados identifica alumnos con nota bajo umbral
  - Test: ranking excluye alumnos sin actividades aprobadas (RN-09)
  - Test: reporte rápido devuelve métricas correctas
  - Test: notas finales promedia solo actividades seleccionadas
  - Test: TPs sin corregir solo incluye textuales (RN-08)
  - Test: monitor general filtra por materia/regional/comisión
  - Test: monitor seguimiento solo alumnos del tutor/profesor
  - Test: aislamiento multi-tenant en todas las queries
- [x] 5.2 Crear `backend/tests/integration/test_analisis_router.py` con tests E2E via cliente HTTP:
  - Test: GET atrasados sin permiso → 403
  - Test: GET atrasados con datos → 200 + respuesta correcta
  - Test: GET ranking → 200 + orden descendente
  - Test: GET reporte-rapido → 200 + métricas
  - Test: GET notas-finales → 200 + promedio
  - Test: GET tps-sin-corregir → 200 + solo textuales
  - Test: GET monitor-general → 200 + scope coordinación
  - Test: GET monitor-seguimiento → 200 + scope tutor/profesor
  - Test: aislamiento tenant en endpoints
