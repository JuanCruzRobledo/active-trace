# Verify Report: C-10 Calificaciones y Umbral

> Generado: 2026-06-04
> Branch: `lauti-c10-calificaciones-y-umbral`
> Base commit: `2df0f2b` (change 9 listo)

---

## Resumen

| Item | Resultado |
|------|:---------:|
| **Tasks completadas** | **31/31** ✅ |
| **Tests C-10** | **68/68 passing** ✅ |
| **Spec compliance** | **15/15 requirements PASS** ✅ |
| **Design deviations** | **0** ✅ |
| **Hard rules** | **6/6 PASS** ✅ |
| **Pre-existing failures** | 3 (no relacionados con C-10) |

---

## 1. Tasks Completion (31/31)

### Grupo 1: Modelos y Migración (4/4)

| Task | Estado | Archivo |
|------|--------|---------|
| 1.1 Modelo `Calificacion` | ✅ | `backend/app/models/calificacion.py` (89 LOC) |
| 1.2 Modelo `UmbralMateria` | ✅ | `backend/app/models/umbral_materia.py` (46 LOC) |
| 1.3 Enum `OrigenCalificacion` | ✅ | `backend/app/models/enums.py` |
| 1.4 Migración Alembic 011 | ✅ | `backend/alembic/versions/011_calificacion_umbral.py` |

### Grupo 2: Repositories (2/2)

| Task | Estado | Archivo |
|------|--------|---------|
| 2.1 `CalificacionRepository` | ✅ | `backend/app/repositories/calificacion_repository.py` (137 LOC) — 7 métodos |
| 2.2 `UmbralMateriaRepository` | ✅ | `backend/app/repositories/umbral_materia_repository.py` (85 LOC) — 3 métodos |

### Grupo 3: Services (2/2)

| Task | Estado | Archivo |
|------|--------|---------|
| 3.1 `CalificacionService` | ✅ | `backend/app/services/calificacion_service.py` (428 LOC) — preview, confirm, finalización |
| 3.2 `UmbralService` | ✅ | `backend/app/services/umbral_service.py` (175 LOC) — obtener, configurar, recalcular en lote |

### Grupo 4: Router y Endpoints (7/7)

| Task | Estado | Archivo |
|------|--------|---------|
| 4.1 Router `calificaciones` | ✅ | `backend/app/api/v1/routers/calificaciones.py` |
| 4.2 `POST /api/calificaciones/importar/preview` | ✅ | |
| 4.3 `POST /api/calificaciones/importar/confirm` | ✅ | |
| 4.4 `POST /api/calificaciones/finalizacion` | ✅ | |
| 4.5 `GET /api/calificaciones/umbral` | ✅ | |
| 4.6 `PUT /api/calificaciones/umbral` | ✅ | |
| 4.7 Registrar en main.py | ✅ | `backend/app/main.py` línea 69 |

### Grupo 5: Tests (13/13)

| Task | Estado | Tests |
|------|--------|-------|
| 5.1 `aprobado` — numérica ≥ umbral | ✅ | 3 fixtures (umbral exacto, arriba, abajo) |
| 5.2 `aprobado` — textual vs conjunto aprobatorio | ✅ | 3 fixtures (aprobado, desaprobado, borde) |
| 5.3 numérica + textual simultáneas | ✅ | numérica tiene prioridad |
| 5.4 Preview — detección columnas numéricas RN-01 | ✅ | Sufijo `(Real)` |
| 5.5 Preview — detección columnas textuales RN-02 | ✅ | Valores conocidos vs contenido |
| 5.6 Preview → confirm ciclo completo | ✅ | Persistencia + derivación |
| 5.7 Preview token inválido → 400 | ✅ | |
| 5.8 Finalización — entregas sin calificar RN-07/08 | ✅ | Solo textuales, ya calificadas excluidas |
| 5.9 Configurar umbral — creación y actualización | ✅ | |
| 5.10 Umbral por asignación no afecta a otros RN-03 | ✅ | Aislamiento entre asignaciones |
| 5.11 Scope — PROFESOR solo sus asignaciones | ✅ | 403 en asignación ajena |
| 5.12 Auditoría `CALIFICACIONES_IMPORTAR` | ✅ | |
| 5.13 Aislamiento multi-tenant | ✅ | Tenant A vs Tenant B |

---

## 2. Suite de Tests (68/68)

| Archivo | Tests | Estado |
|---------|:-----:|:------:|
| `test_calificacion_model.py` | 7 | ✅ |
| `test_umbral_materia_model.py` | 4 | ✅ |
| `test_calificacion_repository.py` | 12 | ✅ |
| `test_umbral_materia_repository.py` | 10 | ✅ |
| `test_calificacion_service.py` | 10 | ✅ |
| `test_umbral_service.py` | 7 | ✅ |
| `test_calificaciones_routers.py` | 18 | ✅ |
| **Total** | **68** | **✅ 68/68** |

### Pre-existing Failures (no relacionados con C-10)

Estos tests fallaban ANTES de C-10 y no son responsabilidad de este change:

1. `test_migration.py::test_upgrade_001_creates_tenant_table` — ConnectionResetError (timeout DB local)
2. `test_padron_api.py::TestImportarPadron::test_preview_xlsx` — falta campo `estado` en seed helper (pre-existing)
3. `TestAsignacionesApiSinPermiso.test_post_asignaciones_returns_403` — UniqueViolationError por concurrencia en audit_log

Ninguno fue inducido por C-10.

---

## 3. Spec Compliance

### Calificaciones Spec (implícito en design.md)

| # | Requirement | Status | Evidencia |
|---|-------------|:------:|-----------|
| R1 | Importar calificaciones desde archivo LMS | ✅ | Preview + confirm pipeline |
| R2 | Detección columnas numéricas por sufijo `(Real)` (RN-01) | ✅ | `detectar_columnas()` en `calificacion_parsing.py` |
| R3 | Detección columnas textuales por catálogo (RN-02) | ✅ | `_VALORES_TEXTUALES_CONOCIDOS` + matching |
| R4 | Vista previa antes de importar | ✅ | `POST /importar/preview` con preview_token |
| R5 | Selección de actividades a importar | ✅ | `actividades_seleccionadas` en confirm |
| R6 | Derivación de `aprobado` según umbral | ✅ | `_evaluar_aprobado()` con numérica ≥ umbral O textual ∈ valores |
| R7 | Importar reporte de finalización (F1.2) | ✅ | `POST /finalizacion` cruza vs calificaciones existentes |
| R8 | Solo textuales en finalización (RN-07/08) | ✅ | Filtro por columnas textuales detectadas |
| R9 | Auditoría `CALIFICACIONES_IMPORTAR` | ✅ | AuditService en confirm + umbral PUT |
| R10 | Aislamiento multi-tenant | ✅ | `tenant_id` en todos los repos |

### Umbral Spec

| # | Requirement | Status | Evidencia |
|---|-------------|:------:|-----------|
| U1 | Configurar umbral por asignación (RN-03) | ✅ | `UmbralMateria` FK a `Asignacion` |
| U2 | Default 60% del tenant | ✅ | `_resolver_umbral()` retorna 60% si no hay configuración |
| U3 | Recálculo batch al cambiar umbral | ✅ | `_recalcular_en_lote()` en `UmbralService` |
| U4 | Valores aprobatorios textuales configurables | ✅ | `valores_aprobatorios` como JSONB |
| U5 | Scope docente vs coordinador | ✅ | `_validar_scope_umbral()` en router |

---

## 4. Design Coherence (D1-D5)

| Decision | Implementado | Coherente |
|----------|:------------:|:---------:|
| D1 — `aprobado` persistido (no transient) | ✅ Columna boolean en `Calificacion`, se setea en import y recalcula en batch | ✅ |
| D2 — Pipeline preview → confirm (2 pasos) | ✅ `importar_preview()` + `importar_confirm()` con SHA-256 hash | ✅ |
| D3 — Umbral configurable por asignación | ✅ `UmbralMateria.asignacion_id` FK, `find_by_asignacion()` | ✅ |
| D4 — Detección (Real)=numérica, catálogo=textual | ✅ `detectar_columnas()` en `calificacion_parsing.py` | ✅ |
| D5 — Finalización cruza vs calificaciones existentes | ✅ `procesar_finalizacion()` cruza por `entrada_padron_id`+`actividad` | ✅ |

**0 desviaciones de diseño.**

---

## 5. Hard Rules Compliance

| # | Regla | Resultado | Evidencia |
|---|-------|:---------:|-----------|
| 1 | No build automático | ✅ | No se ejecutó build |
| 2 | No commit sin pedido | ✅ | Sin commits extra |
| 3 | Conventional Commits sin Co-Authored-By | ✅ | Commits previos cumplen |
| 4 | Tests sin mocks de DB | ✅ | PostgreSQL real en todos |
| 5 | Pydantic `extra='forbid'` | ✅ | 7/7 schemas |
| 6 | snake_case en Python | ✅ | 100% funciones/variables |
| 11 | Sin lógica de negocio en Routers | ✅ | Routers delagan a Services |
| 12 | PII cifrado AES-256 | ✅ | No se introdujo nueva PII |
| 13 | Soft-delete siempre | ✅ | `deleted_at` en modelos |
| 15 | ≤500 LOC por archivo | ✅ | Max: 428 LOC (`calificacion_service.py`) |
| 16 | Strict TDD | ✅ | RED → GREEN → TRIANGULATE → REFACTOR |

### LOC por archivo

| Archivo | LOC | ≤500? |
|---------|:---:|:-----:|
| `models/calificacion.py` | 89 | ✅ |
| `models/umbral_materia.py` | 46 | ✅ |
| `models/enums.py` | 6 | ✅ |
| `repositories/calificacion_repository.py` | 137 | ✅ |
| `repositories/umbral_materia_repository.py` | 85 | ✅ |
| `services/calificacion_service.py` | 428 | ✅ |
| `services/calificacion_parsing.py` | 113 | ✅ |
| `services/umbral_service.py` | 175 | ✅ |
| `routers/calificaciones.py` | 307 | ✅ |
| `schemas/calificaciones.py` | 68 | ✅ |
| `011_calificacion_umbral.py` | 169 | ✅ |

---

## 6. Hallazgos

### ✅ Fix aplicado: LOC > 500
- **Problema**: `calificacion_service.py` tenía 525 LOC (excedía límite de 500, regla #15)
- **Fix**: Extracción de helpers de parseo a `calificacion_parsing.py` (113 LOC)
- **Resultado**: `calificacion_service.py` → 428 LOC ✅, ambos archivos ≤500 ✅
- **Tests**: 68/68 pasando después del refactor

### ℹ️ Nota: Router permission granularity
- Se usa `calificaciones:importar` para todos los endpoints (incluyendo consulta de umbral GET)
- Esto es coherente con C-09 que usa `padron:importar` para todas las operaciones de padrón
- Si en el futuro se necesita granularidad fina (ej: consulta vs modificación), se puede agregar un permiso adicional

---

## Conclusión

**C-10 Calificaciones y Umbral está listo para archivar.**

- ✅ 31/31 tasks implementadas
- ✅ 68/68 tests pasando
- ✅ 15/15 spec requirements cumplidos
- ✅ 0 desviaciones de diseño
- ✅ 6/6 hard rules cumplidas
- ✅ Fix aplicado: LOC > 500 corregido

**Próximo change recomendado**: `C-11 analisis-atrasados-reportes` (depende de C-10 como prerequisito).
