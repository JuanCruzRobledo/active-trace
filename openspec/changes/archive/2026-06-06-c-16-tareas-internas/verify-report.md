# Verification Report

**Change**: C-16 tareas-internas
**Version**: 1.0
**Mode**: Standard

---

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 40 |
| Tasks complete | 40 |
| Tasks incomplete | 0 |

All 40 tasks marked [x] en tasks.md. ✅

---

## Build & Tests Execution

**Tests**: ✅ 65 passed / ❌ 0 failed / ⚠️ 0 skipped

All 65 tests passed successfully against real PostgreSQL database.

---

## Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| REQ-01: Tarea con asignador, asignado, estado y descripción | Crear tarea con todos los campos | `test_6_2_1_crear_tarea`, `test_6_3_1_crear_tarea_201` | ✅ COMPLIANT |
| REQ-01: Tarea con asignador, asignado, estado y descripción | Crear tarea sin materia | `test_6_2_2_crear_tarea_sin_materia` | ✅ COMPLIANT |
| REQ-02: Workflow de estados con transiciones válidas | Pendiente → En progreso | `test_6_2_4`, `test_6_3_11` | ✅ COMPLIANT |
| REQ-02: Workflow de estados con transiciones válidas | En progreso → Resuelta | `test_6_2_5` | ✅ COMPLIANT |
| REQ-02: Workflow de estados con transiciones válidas | Resuelta → Pendiente (inválida) | `test_6_2_6`, `test_6_3_12` | ✅ COMPLIANT |
| REQ-02: Workflow de estados con transiciones válidas | Cancelación desde Pendiente | `test_6_2_7` | ✅ COMPLIANT |
| REQ-03: Timeline de mis tareas | Docente ve solo sus tareas | `test_6_3_3`, `test_6_4_1`, `test_6_4_2` | ✅ COMPLIANT |
| REQ-03: Timeline de mis tareas | Filtrar por estado | `test_6_3_5`, `test_6_4_4` | ✅ COMPLIANT |
| REQ-03: Timeline de mis tareas | Timeline vacía | `test_6_2_16`, `test_6_4_3` | ✅ COMPLIANT |
| REQ-04: Vista de administración con filtros | Admin ve todas las tareas | `test_6_2_18`, `test_6_3_6` | ✅ COMPLIANT |
| REQ-04: Vista de administración con filtros | Filtrar por múltiples criterios | `test_6_2_19` | ✅ COMPLIANT |
| REQ-04: Vista de administración con filtros | Búsqueda textual | `test_6_2_20`, `test_6_3_8` | ✅ COMPLIANT |
| REQ-04: Vista de administración con filtros | Sin permiso retorna 403 | `test_6_3_2`, `test_6_3_7` | ✅ COMPLIANT |
| REQ-05: Comentarios asincrónicos | Agregar comentario a tarea | `test_6_2_9`, `test_6_3_14` | ✅ COMPLIANT |
| REQ-05: Comentarios asincrónicos | Comentario de asignador | `test_6_2_9` (coord_user_id comenta) | ✅ COMPLIANT |
| REQ-05: Comentarios asincrónicos | Listar comentarios ordenados | `test_6_1_18` | ✅ COMPLIANT |
| REQ-06: Creación de tarea con auditoría | Crear tarea con permiso | `test_6_2_21` | ✅ COMPLIANT |
| REQ-06: Creación de tarea con auditoría | Crear tarea sin permiso | `test_6_3_2` | ✅ COMPLIANT |
| REQ-07: Acceso a detalle de tarea | Asignado ve detalle | `test_6_2_12`, `test_6_3_9` | ✅ COMPLIANT |
| REQ-07: Acceso a detalle de tarea | Usuario no autorizado | `test_6_2_14` | ✅ COMPLIANT |
| REQ-07: Acceso a detalle de tarea | Tarea inexistente | `test_6_2_13`, `test_6_3_10` | ✅ COMPLIANT |
| REQ-08: Aislamiento multi-tenant | Tareas aisladas por tenant | `test_6_5_1`, `test_6_5_2` | ✅ COMPLIANT |
| REQ-08: Aislamiento multi-tenant | Acceso cross-tenant denegado | `test_6_5_3` | ✅ COMPLIANT |

**Compliance summary**: 23/23 scenarios compliant ✅

---

## Correctness (Static — Structural Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| Tarea con asignador, asignado, estado y descripción | ✅ Implemented | Modelo con materia_id nullable, contexto_id nullable, enum estado |
| Workflow de estados con transiciones válidas | ✅ Implemented | VALID_TRANSITIONS dict + _validar_transicion + audit log |
| Timeline de mis tareas | ✅ Implemented | listar_mias → list_by_asignado, filtros estado/materia |
| Vista de administración con filtros | ✅ Implemented | listar_todas → list_by_tenant, filtros combinables + ILIKE |
| Comentarios asincrónicos | ✅ Implemented | ComentarioTarea append-only, orden ASC |
| Creación con auditoría | ✅ Implemented | TAREA_CREAR event, require_permission guard |
| Acceso a detalle con verificación | ✅ Implemented | _puede_acceder_tarea check |
| Aislamiento multi-tenant | ✅ Implemented | BaseRepository._scope_query con tenant_id |
| Soft delete en Tarea | ✅ Implemented | BaseMixin (deleted_at) |
| Append-only en ComentarioTarea | ✅ Implemented | Sin updated_at ni deleted_at |
| Permiso tareas:gestionar en create/admin | ✅ Implemented | require_permission("tareas:gestionar") |
| /mias route BEFORE /{id} | ✅ Implemented | Línea 112 antes de 163 |
| snake_case en Python | ✅ Implemented | Todos los archivos |
| extra='forbid' en Pydantic schemas | ✅ Implemented | Todos los 8 schemas |
| ≤500 LOC por archivo backend | ✅ Implemented | Max 318 (tarea_service.py) |
| Registro del router en main.py | ✅ Implemented | Línea 83 |
| Modelos en __init__.py | ✅ Implemented | Línea 48 |
| Seed: permiso mapeado a roles | ✅ Implemented | seed.py: COORDINADOR, ADMIN, PROFESOR con tareas:gestionar |
| Audit codes en whitelist | ✅ Implemented | TAREA_CREAR, TAREA_ESTADO_CAMBIAR, TAREA_COMENTARIO en VALID_ACCION_CODES |
| Migración con índices | ✅ Implemented | 5 índices en tarea, 2 en comentario_tarea |

---

## Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Estado como columna simple en Tarea | ✅ Yes | Columna enum in-place, histórico vía audit log |
| Contexto como UUID polimórfico sin FK | ✅ Yes | contexto_id nullable, sin FK declarado |
| Comentarios como entidad separada | ✅ Yes | Tabla comentario_tarea con FK a tarea |
| Permiso tareas:gestionar para creación y admin | ✅ Yes | require_permission en POST y GET admin |
| Transiciones de estado válidas | ✅ Yes | VALID_TRANSITIONS en tarea_service.py |
| Materia opcional | ✅ Yes | materia_id nullable, validación FK en DB |
| Búsqueda textual con ILIKE | ✅ Yes | Tarea.descripcion.ilike(f"%{busqueda}%") |
| Ordenamiento por defecto DESC | ✅ Yes | order_by(Tarea.created_at.desc()) |
| Optimistic locking en estado | ⚠️ Deviated | Design dice UPDATE con WHERE, pero implementación es read → set → save sin verificar estado actual |

---

## Issues Found

### CRITICAL (must fix before archive)

None.

### WARNING (should fix)

1. **Optimistic locking no implementado en `update_estado`**: El diseño dice explícitamente "el repository usa UPDATE con `WHERE id = X AND estado_actual = Y` (optimistic locking)" para mitigar concurrencia. La implementación actual hace un read → set en objeto Python → save. Dos requests concurrentes pueden pisar el estado del otro. En la práctica, la validación de transición ocurre ANTES del update, pero no hay garantía atómica.
   - **Dónde**: `backend/app/repositories/tarea_repository.py` método `update_estado` (línea 96)
   - **Impacto**: Bajo para la versión inicial, pero contradice el diseño.

2. **Created_at/updated_at devueltos como strings en lugar de datetime**: `_to_tarea_response` convierte `created_at` y `updated_at` con `str()`, pero `TareaResponse` los declara como `datetime | None = None`. FastAPI serializa el dict tal cual, así que no hay bug funcional, pero hay inconsistencia entre el schema Pydantic y la respuesta real.
   - **Dónde**: `backend/app/services/tarea_service.py` líneas 160-161
   - **Impacto**: Bajo. Los consumers HTTP reciben strings ISO sin importar el tipo Python.

3. **Sin validación tenant-scope de materia_id**: El servicio no verifica que `materia_id` pertenezca al tenant actual. La FK en DB asegura integridad referencial pero no tenant-scope. El diseño dice "cuando tiene materia, se valida que exista en el tenant".
   - **Dónde**: `backend/app/services/tarea_service.py` método `crear_tarea`
   - **Impacto**: Bajo. Podría asignarse una materia de otro tenant (si el UUID existe).

### SUGGESTION (nice to have)

1. **Faltan tests de búsqueda textual con caracteres especiales**: `ILIKE` con `%{busqueda}%` podría tener problemas con caracteres como `%` o `_` en la búsqueda. Los tests existentes solo prueban texto plano.
2. **Sin paginación en listados**: Endpoints GET /api/tareas y GET /api/tareas/mias no soportan `offset`/`limit`. Para decenas de tareas no importa, pero si un tenant tiene cientos, se vuelve necesario.
3. **El endpoint PATCH /api/tareas/{id}/estado no tiene rate limiting**: Podría ser spammeado. Considerar agregar rate limiting al cambiar estados.

---

## Verdict

**PASS WITH WARNINGS**

23/23 spec scenarios compliant, 40/40 tasks complete, 65/65 tests passing, 3 warnings (no critical blockers). El warning más relevante es la falta de optimistic locking en `update_estado`, que es una desviación del diseño pero no bloquea el archive.
