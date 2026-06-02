# Proposal: Core Models & Multi-Tenant Foundation (C-02)

## Intent

Establecer el fundamento técnico de multi-tenancy row-level y el modelo de datos base del sistema. Sin esta capa, toda consulta a la BD corre riesgo de cruzar datos entre tenants, y no existe contrato de aislamiento auditado.

## Scope

### In Scope
- Modelo `Tenant` como raíz de aislamiento
- Base Mixin (`id`, `tenant_id`, `created_at`, `updated_at`, `deleted_at`)
- Repository genérico con scope de tenant **siempre activo** (ADR-002 row-level)
- Utilidad AES-256 para cifrado en reposo de PII (DNI, CUIL, CBU, email)
- Migration Alembic 001: tabla tenant + convención de una migración por cambio de schema
- Tests: aislamiento multi-tenant, soft delete, encryption round-trip, timestamps

### Out of Scope
- Implementación de usuarios (E-04) — llega en C-03 con auth JWT
- Roles y permisos (E-05 Asignación) — cae en C-04 rbac
- Integraciones con Moodle — C-08
- Frontend UI — C-21

## Capabilities

### New Capabilities
- `tenant-isolation`: Row-level multi-tenancy with automatic tenant_id scoping in all queries
- `soft-delete`: Append-only audit trail via soft delete mixin
- `encryption-at-rest`: AES-256 encryption/decryption for PII fields (DNI, CUIL, CBU, email)
- `base-models`: Reusable base mixin with audit timestamps and tenant awareness

### Modified Capabilities
None (this is foundational; no prior specs to modify)

## Approach

1. **Tenant Model** — raíz del árbol de datos. Tabla simple + fixture para tests.
2. **BaseMixin** — herencia SQLAlchemy. Toda entidad futura lo heredará → soft delete + timestamps automáticos.
3. **Repository[T]** — genérico con constraint `tenant_id` en where by default. Unsafe query sin scope → falla en review.
4. **Encryption Utility** (`core/security.py`) — encrypt/decrypt helper, FERNET compatible, claves de env.
5. **Alembic Setup** — migración 001 crea tabla tenant; establece patrón para futuras (una per schema change).

**Stack**: SQLAlchemy 2.0 async + Alembic + cryptography lib (FERNET). Tests con pytest + real DB en contenedor.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/models/` | New | Base mixin, Tenant model |
| `backend/app/repositories/` | New | Generic repository base class with tenant scope |
| `backend/app/core/security.py` | Modified | Add AES-256 encrypt/decrypt helpers |
| `backend/alembic/versions/` | New | Migration 001: create tenant table |
| `backend/tests/` | New | Multi-tenant isolation, soft delete, encryption tests |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Repository generics not enforcing tenant scope at type-level | Med | Code review + integration tests prove every query filters tenant_id |
| Encryption key hardcoded or exposed in logs | High | Use env var ENCRYPTION_KEY; never log plaintext; run on secure test DB |
| Soft delete logic inverted (physically deletes instead of soft) | Low | Tests verify deleted records still exist in DB with deleted_at ≠ NULL |
| Migration rollback broken | Med | Test rollback locally before merge |

## Rollback Plan

1. **Git**: revert commit + force-push to `niko-c2-core`
2. **Alembic**: run `alembic downgrade -1` to drop tenant table
3. **Code**: revert models/, repositories/, core/security.py changes
4. **Tests**: confirm old test suite passes again

## Dependencies

- C-01 foundation-setup (✅ complete) — FastAPI scaffold + DB init + Alembic ready

## Success Criteria

- [x] Tenant model instantiates; records persist in DB
- [x] BaseMixin applies to test fixture entity (e.g., DummyEntity)
- [x] Repository filters by tenant by default; queries from tenant A do NOT return tenant B data
- [x] AES-256 round-trip: encrypt(plaintext) → decrypt() == plaintext
- [x] Soft delete: deleted record exists in DB; queries exclude it by default
- [x] ≥80% line coverage + ≥90% business rule coverage in tests
