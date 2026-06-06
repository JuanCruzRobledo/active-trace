## Why

Durante la regresión de C-19 se detectaron 4 fallas **preexistentes** (no causadas por C-19) en tests de integración y unitarios que dependen de PostgreSQL real. Estos tests fallan consistentemente en la suite completa, impidiendo tener una línea base verde. Se corrigen ahora para que el conjunto completo de tests pase limpio antes de avanzar a C-20.

## What Changes

1. **test_migration.py**: Reemplazar credenciales hardcodeadas (`postgres:nikolan`) con valores derivados de `_test_db_url()` — los helpers asyncpg deben parsear la URL en lugar de usar credenciales fijas.
2. **test_migration_002.py**: Misma corrección que test_migration.py — todos los helpers asyncpg usan credenciales hardcodeadas.
3. **test_padron_api.py**: Agregar columna `estado` al `INSERT INTO carrera` raw SQL en `_seed_materia_cohorte()` — el modelo `Carrera` tiene `estado = Column(nullable=False, default="Activa")` pero el INSERT raw no incluye la columna, causando `NotNullViolationError`.
4. **test_auth_identity_immutable.py**: Manejar rate limiting en el endpoint `/api/auth/login` — múltiples tests auth consecutivos disparan 429 Too Many Requests.

## Capabilities

### New Capabilities
- `test-infra-consistency`: Asegura que todos los tests de integración que conectan a PostgreSQL real usen credenciales consistentes desde la configuración en lugar de valores hardcodeados.

### Modified Capabilities
<!-- No existing specs change — son fixes de tests, no cambios de requerimientos -->

## Impact

- **Archivos modificados**:
  - `backend/tests/integration/test_migration.py`
  - `backend/tests/unit/test_migration_002.py`
  - `backend/tests/integration/test_padron_api.py`
  - `backend/tests/integration/test_auth_identity_immutable.py`
- **Sin cambios** en modelos, schemas, servicios, routers ni lógica de negocio.
- **Sin nuevas dependencias**.
