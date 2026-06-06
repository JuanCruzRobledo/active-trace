## 1. Fix migration test credentials

- [x] 1.1 Fix `test_migration.py`: parse credentials from `_test_db_url()` for asyncpg connections instead of hardcoding `postgres:nikolan`
- [x] 1.2 Fix `test_migration_002.py`: parse credentials from `_test_db_url()` for asyncpg connections instead of hardcoding `postgres:nikolan`

## 2. Fix padron API test

- [x] 2.1 Add `estado` column to carrera INSERT in `_seed_materia_cohorte()` with value `'Activa'`

## 3. Fix auth identity rate limiting

- [x] 3.1 Investigate and fix rate limiting issue in `test_auth_identity_immutable.py`: ensure `_reset_rate_limiter_storage` properly resets between tests, or add monkeypatch for rate limit in the test class

## 4. Verify all fixes

- [x] 4.1 Run the 4 previously-failing tests individually to confirm each passes (auth 7/7 pass, padron cascaded to different pre-existing issue, migration tests need PG)
- [ ] 4.2 Run the full test suite to confirm no regressions
