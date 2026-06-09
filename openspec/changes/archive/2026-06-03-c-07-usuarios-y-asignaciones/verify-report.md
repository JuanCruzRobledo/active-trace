## Verification Report

**Change**: C-07 usuarios-y-asignaciones
**Mode**: Strict TDD
**Date**: 2026-06-03

---

### Resumen

| Métrica | Valor |
|---------|-------|
| Specs user-management cubiertas | 9/11 escenarios |
| Specs asignaciones cubiertas | 8/10 escenarios |
| Tests totales (C-07) | 91 — 91 passed, 0 failed |
| Regresiones (otros módulos) | **SÍ** — 8 tests de migración rotos |
| Tasks totales | 19 |
| Tasks completas | 19 (100%) |
| Estado | **FAIL** — issues críticos detectados |

---

### Tasks Completeness

Todas las 19 tasks están marcadas como `[x]` en `tasks.md`:
- 1.1–1.4: Migración y Modelos ✅
- 2.1–2.5: Schemas y Repositories ✅
- 3.1–3.6: Services ✅
- 4.1–4.5: Routers y Endpoints ✅
- 5.1–5.5: Tests de Seguridad ✅

---

### Build & Tests Execution

**Tests C-07**: ✅ **91 passed** en 16.79s

```
tests/unit/test_usuarios_schemas.py .............. 21 passed
tests/integration/test_usuarios_asignaciones_models.py .... 8 passed
tests/integration/test_usuarios_asignaciones_repositories.py 14 passed
tests/integration/test_usuarios_asignaciones_services.py .. 13 passed
tests/integration/test_usuarios_routers.py ............... 13 passed
tests/integration/test_asignaciones_routers.py ........... 11 passed
tests/integration/test_usuarios_security.py ............. 11 passed
```

**Regresiones**: ❌ **8 failed** en `test_migration_002.py`

Todos los 8 fallos tienen la misma causa raíz:

```
alembic.util.exc.CommandError: Multiple head revisions are present
for given argument 'head'
```

**Causa**: Existen DOS archivos de migración que apuntan a `down_revision = "008"`:
1. `009_usuario_asignacion.py` (revision: `009`)
2. `31773bc02927_009_usuarios_y_asignaciones.py` (revision: `31773bc02927`)

Esto crea dos heads en Alembic, rompiendo `alembic upgrade head` y todos los tests que lo usan.

**Pruebas anteriores pasando**: 710 tests pasan sin problemas. Solo los 8 de migración fallan.

---

### Cobertura por spec scenario

#### User Management (11 escenarios)

| # | Escenario | Cubierto? | Test file(s) | Notas |
|---|-----------|-----------|--------------|-------|
| 1 | Creación exitosa de usuario | ✅ | `test_usuarios_routers.py::test_crear_usuario_returns_201`, `test_usuarios_asignaciones_services.py::test_create_usuario_exitoso` | |
| 2 | Fallo por email duplicado | ✅ | `test_usuarios_routers.py::test_crear_usuario_email_duplicado_returns_409`, `test_usuarios_asignaciones_services.py::test_create_email_duplicado_mismo_tenant_raise` | |
| 3 | Email duplicado en distinto tenant es válido | ✅ | `test_usuarios_asignaciones_services.py::test_create_mismo_email_distinto_tenant_ok` | |
| 4 | Listado paginado de usuarios | ⚠️ | — | **Schema `UsuarioListResponse` existe pero NO se usa en el router**. El endpoint `GET /api/admin/usuarios` retorna `list[UsuarioResponse]` sin paginación. |
| 5 | Filtro por estado | ⚠️ | `test_usuarios_asignaciones_repositories.py::test_list_with_filters` | El repo soporta filtros, pero el **router no expone query params** de filtro (estado, nombre) en la API. No hay test HTTP para filtrado. |
| 6 | Edición de datos no sensibles | ✅ | `test_usuarios_routers.py::test_actualizar_usuario_returns_200`, `test_usuarios_asignaciones_services.py::test_update_usuario` | |
| 7 | Edición de email existente | ⚠️ | `test_usuarios_asignaciones_services.py::test_create_email_duplicado_mismo_tenant_raise` | La validación existe en el service (`actualizar()` chequea unicidad de email), pero **no hay test HTTP que verifique 409 al cambiar email a uno existente**. |
| 8 | Soft-delete exitoso | ✅ | `test_usuarios_routers.py::test_soft_delete_usuario_returns_200`, `test_usuarios_asignaciones_services.py::test_soft_delete_no_reusar_email` | |
| 9 | Consulta de usuario eliminado | ❌ | — | **El spec dice "el usuario aparece en la respuesta con estado 'Inactivo'"**, pero el endpoint `GET /api/admin/usuarios/{id}` retorna 404 porque filtra por `deleted_at IS NULL`. El repo tiene `get_including_deleted()` pero **no está expuesto en la API**. |
| 10 | Email no visible en log | ✅ | `test_usuarios_security.py::test_crear_usuario_no_logea_pii`, `test_usuarios_security.py::test_listar_usuarios_no_logea_pii` | Usa `caplog` para verificar. |
| 11 | Respuesta HTTP sin PII en texto plano | ✅ | `test_usuarios_security.py::test_crear_respuesta_no_expone_pii_plano`, `test_get_respuesta_no_expone_pii_plano`, `test_listar_no_expone_pii_plano` | |

#### Asignaciones (10 escenarios)

| # | Escenario | Cubierto? | Test file(s) | Notas |
|---|-----------|-----------|--------------|-------|
| 1 | Creación exitosa de asignación | ✅ | `test_asignaciones_routers.py::test_crear_asignacion_returns_201`, `test_usuarios_asignaciones_services.py::test_create_asignacion_exitosa` | |
| 2 | Asignación sin contexto académico (rol global) | ✅ | `test_usuarios_asignaciones_models.py::test_crear_asignacion_global` | |
| 3 | Listado filtrado por materia | ⚠️ | `test_usuarios_asignaciones_repositories.py::test_list_by_context` | El repo soporta filtros, pero **no hay test HTTP** que verifique `GET /api/asignaciones?materia_id=...` filtra correctamente. |
| 4 | Historial incluye asignaciones vencidas | ✅ | `test_usuarios_asignaciones_services.py::test_listar_asignaciones_vigentes_y_vencidas`, `test_asignaciones_routers.py::test_asignacion_vencida_tiene_estado_vencida` | |
| 5 | Extensión de vigencia | ⚠️ | `test_asignaciones_routers.py::test_actualizar_asignacion_returns_200` | El PATCH endpoint funciona, pero **no hay test específico** que extienda `hasta` y verifique que `estado_vigencia` se recalcula. |
| 6 | Soft-delete de asignación | ✅ | `test_asignaciones_routers.py::test_soft_delete_asignacion_returns_200`, `test_usuarios_asignaciones_services.py::test_soft_delete_asignacion` | |
| 7 | Asignación vencida no autoriza | ⚠️ | `test_usuarios_security.py::test_asignacion_vencida_estado_vencida` | **El spec dice "el sistema deniega el acceso (403 Forbidden)"**. El test solo verifica `estado_vigencia == "Vencida"` en el response, NO que un usuario con asignación vencida reciba 403 al intentar acceder a recursos. |
| 8 | Asignación vigente autoriza | ⚠️ | `test_usuarios_security.py::test_asignacion_vigente_estado_vigente` | Mismo problema que #7 — verifica estado pero no autorización real. |
| 9 | Asignación con responsable | ✅ | `test_asignaciones_routers.py::test_crear_asignacion_con_jerarquia`, `test_usuarios_security.py::test_asignacion_con_responsable_se_persiste` | |
| 10 | Usuario con dos roles simultáneos | ✅ | `test_usuarios_asignaciones_services.py::test_asignacion_multi_rol` | |

---

### Reglas duras verificadas

| Regla | Estado | Evidencia |
|-------|--------|-----------|
| `extra='forbid'` en schemas Pydantic | ✅ | Tests `test_create_extra_field_forbidden`, `test_update_extra_forbidden` en ambos schemas pasan |
| PII cifrada AES-256 (EncryptedColumn) | ✅ | Modelo usa `EncryptedColumn` con `inject_encryption_keys()` en startup. Tests con DB real verifican cifrado/descifrado. |
| PII enmascarada en respuestas HTTP | ✅ | Router usa `mask_email()`, `mask_dni()`, `mask_cuil()`, `mask_cbu()`, `mask_alias_cbu()`. Tests de seguridad verifican que no hay texto plano. |
| Multi-tenancy row-level | ✅ | `tenant_id` en ambas tablas. Repos usan `_scope_query()` del `BaseRepository`. Tests de aislamiento multi-tenant pasan. |
| Soft delete + partial unique indexes | ✅ | `deleted_at` en ambos modelos. Partial unique index `uq_usuario_tenant_email_active` en migración. Tests de soft-delete pasan. |
| ≤500 LOC por archivo | ✅ | Archivo más grande: 219 LOC (asignaciones router). Todos bajo 500. |
| RBAC fino con `require_permission()` | ✅ | `admin:gestionar-usuarios` en usuarios, `equipos:asignar` en asignaciones. Tests 403 pasan. |
| snake_case en Python | ✅ | Todo en snake_case (funciones, variables, columnas, módulos). |
| Pydantic v2 `model_config` | ✅ | `model_config = ConfigDict(extra='forbid')` en todos los schemas. |
| Identidad desde JWT | ✅ | Routers usan `get_current_user` + `require_permission`. |
| ≤500 LOC backend | ✅ | Todos los archivos < 500 LOC. |

---

### Coherence (Design)

| Decisión | Seguida? | Notas |
|----------|----------|-------|
| Modelos separados de auth User | ✅ | `Usuario` tiene FK `auth_user_id` → `users.id`. |
| Partial unique index para soft-delete | ✅ | `uq_usuario_tenant_email_active` con `WHERE deleted_at IS NULL`. |
| Encrypted fields con EncryptionService | ✅ | `EncryptedColumn` type decorator + `inject_encryption_keys()` en startup. |
| `estado_vigencia` derivado (no almacenado) | ✅ | `_calcular_estado_vigencia()` en el router. |
| Endpoints separados por permiso | ✅ | `/api/admin/usuarios` (ADMIN) vs `/api/asignaciones` (equipos:asignar). |
| Relación Usuario ↔ Auth User vía FK + creación automática | ✅ | `UsuarioService.create()` crea `User` de auth con password temporal. |

---

### Issues encontrados

#### CRITICAL (debe arreglarse antes de archivar)

1. **Dos migraciones 009 — "Multiple head revisions"**
   - **Qué**: Existen `009_usuario_asignacion.py` (rev: `009`) y `31773bc02927_009_usuarios_y_asignaciones.py` (rev: `31773bc02927`), ambas con `down_revision = "008"`.
   - **Impacto**: Alembic no puede resolver `head`. **8 tests existentes** de migración (`test_migration_002.py`) fallan. La base de datos real no puede migrar automáticamente.
   - **Qué hacer**: Eliminar el archivo duplicado (`31773bc02927_009_usuarios_y_asignaciones.py`) o establecer una rama de merge. Probablemente el canonical es `009_usuario_asignacion.py`.

#### WARNING (debería arreglarse)

2. **Paginación no implementada en router de usuarios**
   - **Qué**: El spec dice "lista paginada de usuarios del tenant". El schema `UsuarioListResponse` existe (con `items`, `total`, `page`, `page_size`) pero **nunca se usa**.
   - **Impacto**: El endpoint `GET /api/admin/usuarios` retorna `list[UsuarioResponse]` sin paginación. Para listas grandes (>1000 usuarios), esto es problemático.
   - **Fix**: Agregar `page`/`page_size` query params al router y usar `UsuarioListResponse`.

3. **Filtros por estado/nombre no expuestos en API**
   - **Qué**: El spec scenario "Filtro por estado" requiere que el ADMIN pueda filtrar usuarios por estado. El repositorio soporta filtros (`list_by_tenant`) pero el **router no expone query params**.
   - **Impacto**: Funcionalidad incompleta vs spec.
   - **Fix**: Agregar `estado` y `nombre` como query params opcionales en `GET /api/admin/usuarios`.

4. **"Consulta de usuario eliminado" no implementada**
   - **Qué**: El spec scenario #9 dice "el usuario aparece en la respuesta con estado 'Inactivo'" al consultar un usuario soft-deleteado. El endpoint actual retorna 404.
   - **Impacto**: Comportamiento inconsistentes con spec.
   - **Fix**: Agregar query param `?incluir_eliminados=true` al endpoint GET, o exponer `GET /api/admin/usuarios/{id}/historial`.

5. **No hay endpoint para verificar autorización de asignación vencida (403)**
   - **Qué**: El spec #7 de asignaciones dice "asignación vencida no autoriza — 403 Forbidden". No hay test que demuestre esto con un request real a un endpoint protegido.
   - **Impacto**: La lógica de autorización basada en vigencia no está probada a nivel de API. Los tests actuales solo verifican que el campo `estado_vigencia` diga "Vencida".

#### SUGGESTION (nice to have)

6. **Router de asignaciones usa `prefix="/api"` en vez de `prefix="/api/asignaciones"`**
   - **Qué**: El patrón estándar del proyecto sería `prefix="/api/asignaciones"` con rutas raíz `@router.get("/")`. Actualmente usa `prefix="/api"` con `@router.get("/asignaciones")`.
   - **Impacto**: Funciona, pero es inconsistente con cómo se estructuran otros routers del proyecto.
   - **Fix**: Cambiar a `prefix="/api/asignaciones"` y rutas relativas, o mantenerlo como está si es el patrón del proyecto.

7. **No hay test HTTP para "extensión de vigencia" específica**
   - **Qué**: Se testea PATCH genérico cambiando `rol`, pero no hay test que cambie `hasta` a una fecha futura y verifique que `estado_vigencia` cambia a "Vigente".

8. **No hay test HTTP para filtrar asignaciones por materia**
   - **Qué**: El repo y service soportan `list_by_context(materia_id=...)`, pero no hay test de integración HTTP que lo verifique.

---

### Conclusión

**Veredicto**: ❌ **FAIL** — issues críticos detectados.

**El cambio C-07 está casi completo pero no puede archivarse hasta resolver:**

1. **🔴 CRITICAL**: La migración duplicada rompe Alembic y 8 tests existentes.
2. **🟡 4 WARNINGS**: Paginación faltante, filtros no expuestos, consulta de eliminados, y autorización por vigencia no testeada.

**Resumen**: La implementación base es sólida (91 tests pasan, 19/19 tasks completas), pero los issues de migración son bloqueantes para archive. Los WARNINGS son funcionalidades especificadas pero no implementadas al 100%.

**Proximo paso**: Fix del CRITICAL (eliminar migración duplicada), luego evaluar si los WARNINGS deben resolverse antes de archivar o pueden pasar a un change futuro.
