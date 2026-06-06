# test-infra-consistency

Specification for test infrastructure consistency — ensures all tests use credential sources consistently and handle rate limiting properly.

## ADDED Requirements

### Requirement: Migration tests use configurable DB credentials

All Alembic migration tests SHALL derive database connection parameters from `_test_db_url()` instead of using hardcoded credentials.

#### Scenario: test_migration.py uses URL-derived credentials
- **WHEN** `_test_db_url()` returns `postgresql+asyncpg://user:pass@host:5432/db`
- **THEN** all asyncpg connections in the test SHALL use `user`, `pass`, `host:5432`, and `db` parsed from that URL

#### Scenario: test_migration_002.py uses URL-derived credentials
- **WHEN** `_test_db_url()` returns `postgresql+asyncpg://user:pass@host:5432/db`
- **THEN** all asyncpg connections in the test SHALL use `user`, `pass`, `host:5432`, and `db` parsed from that URL

### Requirement: Carrera INSERT in test seeds includes estado column

The `_seed_materia_cohorte()` helper SHALL include the `estado` column when inserting into the `carrera` table, matching the model definition which has `estado = Column(nullable=False, default="Activa")`.

#### Scenario: Carrera seed with estado
- **WHEN** `_seed_materia_cohorte()` inserts a carrera row
- **THEN** the INSERT statement SHALL include `estado` with value `'Activa'`
- **AND** the INSERT SHALL NOT raise `NotNullViolationError`

### Requirement: Auth identity tests handle rate limiting

Tests in `test_auth_identity_immutable.py` SHALL handle the rate limit on `/api/auth/login` (5 requests per 60 seconds) so that multiple login calls across different tests do not cause 429 errors.

#### Scenario: Multiple login tests pass without 429
- **WHEN** multiple tests in the auth identity suite call `/api/auth/login`
- **THEN** each test SHALL receive `200 OK` (not `429 Too Many Requests`)
