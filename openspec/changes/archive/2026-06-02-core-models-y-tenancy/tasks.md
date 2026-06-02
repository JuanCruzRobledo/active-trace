# Tasks: Core Models & Multi-Tenant Foundation (C-02)

## Implementation Checklist (TDD Strict: RED → GREEN → TRIANGULATE → REFACTOR)

### Phase 1: Models & Base Infrastructure (Tasks 1.1 – 1.4)

#### Task 1.1 — Create BaseMixin with Audit Fields
- **Description**: Implementar `BaseMixin` en `backend/app/models/base.py` con campos: id (UUID), tenant_id, created_at, updated_at, deleted_at. Usar SQLAlchemy 2.0 async + Mapped types.
- **Dependencies**: Ninguna (foundational)
- **TDD Cycle**:
  - **RED**: Test que verifica BaseMixin tiene los 5 campos (id, tenant_id, created_at, updated_at, deleted_at) y tipos correctos
  - **GREEN**: Crear clase BaseMixin vacía; agregar field declarations
  - **TRIANGULATE**: Test que verifica índices en tenant_id y deleted_at; test que verifica herencia (una clase dummy hereda BaseMixin y tiene todos los campos)
  - **REFACTOR**: Extraer constantes de defaults (datetime.utcnow), revisar 500 LOC max
- **Test File**: `backend/tests/unit/test_base_mixin.py`
- **Acceptance**: 
  - [ ] BaseMixin tiene 5 campos con tipos correctos
  - [ ] Herencia SQLAlchemy funciona (dummy model hereda)
  - [ ] Índices en tenant_id, deleted_at (verificar via SQLAlchemy schema)

#### Task 1.2 — Create Tenant Model
- **Description**: Crear modelo ORM `Tenant` en `backend/app/models/tenant.py`. Hereda de BaseModel (que a su vez hereda BaseMixin). Campos: id, name, domain. Domain debe ser unique.
- **Dependencies**: Task 1.1
- **TDD Cycle**:
  - **RED**: Test que instancia Tenant(id=uuid, name="test", domain="test.com") y verifica campos
  - **GREEN**: Clase Tenant vacía, agregar campos
  - **TRIANGULATE**: Test que verifica unique constraint en domain; test que verifica FK a tenant_id (aunque aquí es raíz, verifica la relación)
  - **REFACTOR**: Revisar docstrings, tipos, 500 LOC max
- **Test File**: `backend/tests/unit/test_tenant_model.py`
- **Acceptance**:
  - [ ] Tenant instancia correctamente
  - [ ] Campos: id (UUID PK), name (str), domain (str unique), created_at, updated_at, deleted_at (heredados)

#### Task 1.3 — Create DummyEntity for Testing
- **Description**: Crear entidad de prueba `DummyEntity` en `backend/tests/fixtures/models.py`. Hereda BaseModel; tiene campo adicional `test_field: str` para probar que el mixin se propaga. Usar para tests de repository, soft delete, encryption.
- **Dependencies**: Task 1.1, 1.2
- **TDD Cycle**:
  - **RED**: Test que verifica DummyEntity hereda todos los campos de BaseMixin + tiene test_field
  - **GREEN**: Clase DummyEntity con los campos
  - **TRIANGULATE**: Test que persiste/recupera DummyEntity de BD
  - **REFACTOR**: Simplificar, revisar LOC
- **Test File**: N/A (fixture, no test directo)
- **Acceptance**:
  - [ ] DummyEntity hereda BaseMixin
  - [ ] DummyEntity persiste en BD sin errores

#### Task 1.4 — Create BaseRepository Generic[T]
- **Description**: Implementar `BaseRepository` en `backend/app/repositories/base.py` como genérico `Generic[T]` con Type var bound a BaseModel. Métodos core: `find_by_id(id, tenant_id)`, `list_all(tenant_id)`, `create(obj, tenant_id)`, `update(obj, tenant_id)`, `soft_delete(id, tenant_id)`. TODOS los métodos filtran por `tenant_id` (inyectado en where clause).
- **Dependencies**: Task 1.1, 1.2, 1.3
- **TDD Cycle**:
  - **RED**: Test que crea repo para DummyEntity; llama find_by_id(id, tenant_id) con 2 tenants diferentes; verifica que T1 no ve datos de T2
  - **GREEN**: Clase BaseRepository vacía; implementar find_by_id con tenant_id filter obligatorio
  - **TRIANGULATE**: Test list_all(tenant_id) — 3 objetos en T1, 2 en T2, list_all(T1) retorna solo 3; test soft_delete() — verifica deleted_at ≠ None; test find_by_id retorna None si soft-deleted
  - **REFACTOR**: Extraer _apply_tenant_scope(), revisar errores async/await, 500 LOC max
- **Test File**: `backend/tests/integration/test_base_repository.py`
- **Acceptance**:
  - [ ] find_by_id(id, tenant_id) retorna obj solo si tenant_id coincide
  - [ ] list_all(tenant_id) filtra por tenant + excluye soft-deleted
  - [ ] soft_delete(id, tenant_id) marca deleted_at ≠ None
  - [ ] Code review: cada query tiene `tenant_id` en where clause

---

### Phase 2: Encryption & Security (Tasks 2.1 – 2.3)

#### Task 2.1 — Implement AES-256 EncryptionService
- **Description**: Crear `EncryptionService` en `backend/app/core/security.py`. Usar `cryptography.Fernet` (AES-128-CBC + HMAC). Constructor acepta clave o lee `ENCRYPTION_KEY` env var (base64-encoded 32 bytes). Métodos: `encrypt(plaintext: str) -> str`, `decrypt(ciphertext: str) -> str`. Nunca loguear plaintexts.
- **Dependencies**: Task 1.1
- **TDD Cycle**:
  - **RED**: Test que encrypt("test") retorna string cifrado diferente de "test"
  - **GREEN**: Clase vacía; implementar encrypt() con Fernet
  - **TRIANGULATE**: Test decrypt(encrypt(x)) == x (round-trip); test missing ENCRYPTION_KEY raises error; test empty string returns None
  - **REFACTOR**: Agregar docstrings, type hints, manejo de errores (InvalidToken, etc.)
- **Test File**: `backend/tests/unit/test_encryption_service.py`
- **Acceptance**:
  - [ ] encrypt/decrypt round-trip funciona
  - [ ] ENCRYPTION_KEY se lee de env o lanza error
  - [ ] Plaintext nunca loguedo

#### Task 2.2 — Create Encrypted Column Descriptor
- **Description**: Crear un property descriptor SQLAlchemy para aplicar encryption automática en ORM. Ej: `email = EncryptedStr()` → al asignar obj.email = "x@y.com", se cifra automáticamente; al leerlo, se descifra. Integrar con BaseModel para campos marcados `[cifrado]`.
- **Dependencies**: Task 2.1, 1.1
- **TDD Cycle**:
  - **RED**: Test que crea DummyEntity con campo `email: EncryptedStr()`, asigna "test@test.com", verifica en BD está cifrado
  - **GREEN**: Clase EncryptedStr con __get__/__set__ descriptors
  - **TRIANGULATE**: Test que persiste/carga desde BD, verifica plaintext en memoria vs ciphertext en BD; test round-trip con múltiples valores
  - **REFACTOR**: Revisar thread-safety si es necesario, 500 LOC max
- **Test File**: `backend/tests/unit/test_encrypted_descriptor.py`
- **Acceptance**:
  - [ ] Descriptor cifra al asignar, descifra al leer
  - [ ] BD almacena ciphertext; memoria tiene plaintext
  - [ ] Reload desde BD descifra automáticamente

#### Task 2.3 — Add Encrypted Fields to Tenant/User Models (Prepare)
- **Description**: Actualizar Tenant model (si lo requiere) y preparar estructura para Usuario (C-03) con campos `[cifrado]`: email, dni, cuil, cbu, alias_cbu. Solo agregar las columnas con tipos correctos; no implementar lógica de Usuario (eso es C-03). Verificar que descriptores EncryptedStr() pueden aplicarse.
- **Dependencies**: Task 2.2, 1.2
- **TDD Cycle**:
  - **RED**: Test que DummyEntity con email: EncryptedStr() persiste y descifra bien
  - **GREEN**: Agregar tipos y columnas a modelos
  - **TRIANGULATE**: Test múltiples campos cifrados en la misma entidad; test con valores None (opcional fields)
  - **REFACTOR**: Documentar qué campos son cifrados donde
- **Test File**: `backend/tests/unit/test_encrypted_fields.py`
- **Acceptance**:
  - [ ] Tenant model puede tener campos cifrados (estructura lista para C-03)
  - [ ] Campos cifrados se persisten/cargan correctamente

---

### Phase 3: Alembic & Migrations (Tasks 3.1 – 3.2)

#### Task 3.1 — Create Alembic Migration 001: Tenant Table
- **Description**: Generar migración Alembic `backend/alembic/versions/001_tenant.py`. Debe crear tabla `tenant` con columnas: id (UUID PK), name (str), domain (str unique), created_at, updated_at, deleted_at. Agregar índices en `domain` y `deleted_at`. Implementar `upgrade()` y `downgrade()`.
- **Dependencies**: Task 1.2, 1.3 (models deben existir para autogenerate)
- **TDD Cycle**:
  - **RED**: Test que corre `alembic upgrade 001`; verifica tabla tenant existe con las columnas
  - **GREEN**: Crear archivo 001_tenant.py con código SQL mínimo (create_table)
  - **TRIANGULATE**: Test rollback (`alembic downgrade -1`); verifica tabla se dropped; test que sequential numbering funciona (si existe 001, la siguiente es 002)
  - **REFACTOR**: Revisar índices, constraints, documentar
- **Test File**: `backend/tests/integration/test_alembic_migrations.py`
- **Acceptance**:
  - [ ] Migración 001 crea tabla tenant con esquema correcto
  - [ ] Rollback funciona (tabla dropped)
  - [ ] `alembic current` muestra 001 después de upgrade

#### Task 3.2 — Verify Migration Conventions
- **Description**: Documentar y testear convención de migraciones: una migración por cambio de schema; nombres secuenciales (001, 002, ...); archivo `{NNN}_{change_name}.py`. Crear script de prueba que verifica que nueva migración respeta convención.
- **Dependencies**: Task 3.1
- **TDD Cycle**:
  - **RED**: Test que intenta nombrar migración mal (ej: `999_anything.py`); verifica que alembic corre upgrade en orden
  - **GREEN**: Test que verifica migraciones en `versions/` están ordenadas (001 < 002 < ...)
  - **TRIANGULATE**: Test que downgrade funciona en orden inverso; test que alembic history muestra 001 like "tenant"
  - **REFACTOR**: Crear helper function para validar convención
- **Test File**: `backend/tests/integration/test_migration_conventions.py`
- **Acceptance**:
  - [ ] Migraciones siguen convención secuencial
  - [ ] Upgrade/downgrade en orden correcto

---

### Phase 4: Multi-Tenant Isolation & Soft Delete (Tasks 4.1 – 4.3)

#### Task 4.1 — Test Multi-Tenant Isolation in Repository
- **Description**: Escribir suite de tests que verifica aislamiento multi-tenant. Dos tenants (T1, T2); dos objetos DummyEntity (obj1 in T1, obj2 in T2). Tests: `list_all(T1)` retorna solo obj1; `find_by_id(id2, T1)` retorna None (aunque id2 existe en T2); `create()` con tenant_id se persiste correctamente; `update()` solo si tenant_id coincide.
- **Dependencies**: Task 1.4, 1.3
- **TDD Cycle**:
  - **RED**: Test list_all(T1) que espera [obj1]; falla si retorna obj2 también
  - **GREEN**: Implementar en BaseRepository (ya hecho en 1.4, solo verificar)
  - **TRIANGULATE**: Añadir tests para find_by_id, create, update; variar tenant_id; verificar que queries sin tenant_id scope fallan
  - **REFACTOR**: Consolidar fixtures (setup 2 tenants + 2 objects)
- **Test File**: `backend/tests/integration/test_multi_tenant_isolation.py`
- **Acceptance**:
  - [ ] find_by_id respeta tenant boundary
  - [ ] list_all filtra por tenant
  - [ ] create/update requieren tenant_id correcto
  - [ ] Cross-tenant read/write es imposible (devuelve None o 404)

#### Task 4.2 — Test Soft Delete Behavior
- **Description**: Suite de tests para soft delete: create obj → soft_delete() → verifica deleted_at ≠ None; list_all() no incluye borrados; find_by_id() retorna None; list_all_including_deleted() incluye borrados; re-soft-delete un ya-borrado (idempotent o error?).
- **Dependencies**: Task 1.4, 1.3
- **TDD Cycle**:
  - **RED**: Test soft_delete(id1) → verifica deleted_at es datetime; list_all() no lo incluye
  - **GREEN**: Implementar soft_delete en BaseRepository (ya done, verificar)
  - **TRIANGULATE**: Test list_all_including_deleted() retorna borrados; find_by_id ignora borrados; soft_delete un ya-borrado (test ambos: silently succeeds o error)
  - **REFACTOR**: Parametrizar, reducir repetición
- **Test File**: `backend/tests/integration/test_soft_delete.py`
- **Acceptance**:
  - [ ] soft_delete() marca deleted_at
  - [ ] list_all() excluye soft-deleted
  - [ ] find_by_id() retorna None para soft-deleted
  - [ ] list_all_including_deleted() incluye
  - [ ] Soft delete es append-only (auditable)

#### Task 4.3 — Test Soft Delete + Multi-Tenant Integration
- **Description**: Verificar que soft delete respeta tenant scope: Obj1 (T1, active) + Obj2 (T2, active). soft_delete(Obj1) → Obj1 marked, Obj2 unaffected. list_all(T1) no ve Obj1; list_all(T2) ve Obj2. Simular accidental cross-tenant soft-delete (attempt to soft-delete Obj2 via T1 context) → falla.
- **Dependencies**: Task 4.1, 4.2
- **TDD Cycle**:
  - **RED**: Test que soft_delete(id1, T2) no afecta obj1 en T1 (verifica obj1.deleted_at still None)
  - **GREEN**: Verificar que soft_delete ya respeta tenant_id (done in 1.4)
  - **TRIANGULATE**: Múltiples scenarios: 3 tenants, varios objetos, soft-delete uno, verify scoping
  - **REFACTOR**: Consolidar con 4.1 / 4.2 si hay repetición
- **Test File**: `backend/tests/integration/test_soft_delete_multi_tenant.py`
- **Acceptance**:
  - [ ] Soft delete respeta tenant boundary
  - [ ] Cross-tenant soft-delete attempts fail (return None or 404)

---

### Phase 5: Encryption Round-Trip & Integration (Tasks 5.1 – 5.2)

#### Task 5.1 — Test Encryption Round-Trip with ORM
- **Description**: Crear fixture `DummyEntity` con campo `email: EncryptedStr()`. Test: assign plaintext → persist → reload from DB → verify plaintext readable in-memory, ciphertext in DB.
- **Dependencies**: Task 2.2, 1.3
- **TDD Cycle**:
  - **RED**: Test que persiste obj.email = "test@example.com"; reload; verifica obj.email == "test@example.com"
  - **GREEN**: EncryptedStr descriptor (done in 2.2, verify)
  - **TRIANGULATE**: Test múltiples objects, valores None, special chars, length variants
  - **REFACTOR**: Cleanup fixtures
- **Test File**: `backend/tests/integration/test_encryption_round_trip.py`
- **Acceptance**:
  - [ ] Plaintext assigned → ciphertext in DB → plaintext on reload
  - [ ] Multiple objects with encrypted fields work
  - [ ] None/empty fields handled

#### Task 5.2 — Test Encryption + Multi-Tenant + Soft Delete Integration
- **Description**: Integración end-to-end: DummyEntity (T1 + encrypted email + soft delete) → persist → soft_delete → verify email still encrypted in deleted row; query con list_all_including_deleted → email decrypts.
- **Dependencies**: Task 5.1, 4.2
- **TDD Cycle**:
  - **RED**: Test creates obj with encrypted email, soft-deletes, reloads (including_deleted), verifies email decrypts
  - **GREEN**: Verify each component works (encryption, soft delete, multi-tenant)
  - **TRIANGULATE**: Multiple soft-deleted objects; verify isolation
  - **REFACTOR**: N/A simple integration test
- **Test File**: `backend/tests/integration/test_full_integration_c02.py`
- **Acceptance**:
  - [ ] All three features (encryption, soft delete, multi-tenant) work together
  - [ ] No data leaks between tenants
  - [ ] Encrypted data remains encrypted even in soft-deleted rows

---

### Phase 6: Code Review & Quality (Tasks 6.1 – 6.3)

#### Task 6.1 — Code Coverage Report
- **Description**: Ejecutar pytest con `--cov=backend/app --cov-report=html` desde `backend/` directory. Generar reporte HTML. Verifyar ≥80% line coverage, ≥90% business rule coverage (tenant scope, soft delete, encryption).
- **Dependencies**: Todas las tasks anteriores
- **Acceptance**:
  - [ ] Coverage ≥80% líneas (`backend/app/models, repositories, core/security`)
  - [ ] Coverage ≥90% reglas de negocio (tenant scope, soft delete, encryption logic)
  - [ ] Reporte guardado en `backend/coverage/` (htmlcov)

#### Task 6.2 — Lint & Type Checking
- **Description**: Ejecutar `ruff check backend/app` (o `pylint`) + `mypy backend/app --strict`. Fix todos los issues. Verificar que no hay `any` types; type hints completos.
- **Dependencies**: Tasks 1–5
- **Acceptance**:
  - [ ] ruff score 10/10 (no errors/warnings)
  - [ ] mypy strict passes (0 errors)
  - [ ] No `any` types in production code

#### Task 6.3 — Code Review Checklist
- **Description**: Revisar manualmente (o via CI check):
  - [ ] ¿Todo query tiene `tenant_id` en where clause?
  - [ ] ¿Secrets/keys están en env vars, no hardcoded?
  - [ ] ¿Plaintext PII logged? (buscar email, dni, cbu en logs)
  - [ ] ¿Max 500 LOC por archivo?
  - [ ] ¿Soft delete nunca hace hard delete?
  - [ ] ¿Migrations son secuenciales e inmutables?
  - [ ] ¿Tests cubren scenarios + edge cases?
- **Acceptance**:
  - [ ] Checklist manual completado
  - [ ] 0 violations

---

### Phase 7: Verification & Sign-Off (Tasks 7.1 – 7.2)

#### Task 7.1 — Run Full Test Suite
- **Description**: `pytest backend/tests/ -v --cov=backend/app` desde `backend/`. Todos los tests deben pasar. Registrar tiempos de ejecución.
- **Dependencies**: Tasks 1–6
- **Acceptance**:
  - [ ] Todos los tests pasan (pytest exit code 0)
  - [ ] 0 warnings/errors
  - [ ] Coverage ≥80% líneas, ≥90% reglas

#### Task 7.2 — Verify Migration Rollback
- **Description**: Ejecutar `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head`. Verificar que rollback/upgrade cicla sin errors.
- **Dependencies**: Task 3.1, 3.2
- **Acceptance**:
  - [ ] upgrade → downgrade → upgrade ciclo es idempotent
  - [ ] 0 SQL errors
  - [ ] Schema matches after cycle

---

## Summary

| Phase | Tasks | Estimate | Status |
|-------|-------|----------|--------|
| 1 | 1.1–1.4 (Models + Repository) | 3h | ⬜ TODO |
| 2 | 2.1–2.3 (Encryption) | 2h | ⬜ TODO |
| 3 | 3.1–3.2 (Alembic) | 1h | ⬜ TODO |
| 4 | 4.1–4.3 (Integration) | 2h | ⬜ TODO |
| 5 | 5.1–5.2 (E2E) | 1h | ⬜ TODO |
| 6 | 6.1–6.3 (Quality) | 1h | ⬜ TODO |
| 7 | 7.1–7.2 (Sign-off) | 1h | ⬜ TODO |
| **TOTAL** | **20 tasks** | **~11h** | |

---

## Dependencies Map

```
1.1 (BaseMixin)
  ├── 1.2 (Tenant Model)
  │   └── 1.3 (DummyEntity) ──┬─→ 1.4 (BaseRepository)
  │       └── 2.2 (EncryptedDescriptor)
  │           └── 2.3 (Prepare Encrypted Fields)
  │
  └── 2.1 (EncryptionService) ──→ 2.2
  └── 3.1 (Migration 001)
  └── 4.1 (Multi-Tenant Tests)
  └── 4.2 (Soft Delete Tests) ──→ 4.3 (Integration)
  └── 5.1 (Encryption RT) ──→ 5.2 (Full Integration)
  └── 6.1–6.3 (Quality)
  └── 7.1–7.2 (Verification)
```

---

## Notes for Implementation Agent

- **TDD Strict Mode**: RED (failing test) → GREEN (minimal code) → TRIANGULATE (≥2 cases) → REFACTOR (clean up)
- **Tenant Scope**: EVERY query must filter by `tenant_id`. If you see a query without it, it's a bug. Code review will catch it.
- **Soft Delete**: NEVER hard delete. Mark deleted_at and filter `where deleted_at is null` in queries.
- **Encryption**: Never log plaintext. Use env vars for keys. Test round-trip: encrypt → decrypt → verify.
- **Alembic**: One migration per change. Sequential numbering. Immutable once created.
- **Max LOC**: 500 per file (Python). Measure and refactor if exceeded.
- **Coverage**: ≥80% lines, ≥90% business rules. Use `pytest --cov` report to verify.
