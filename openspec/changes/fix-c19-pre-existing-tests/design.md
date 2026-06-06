## Context

Cuatro tests preexistentes fallan consistentemente en la suite de tests del backend. Fueron detectados durante la regresión de C-19 pero no son causados por C-19. Son bugs en los tests mismos, no en el código de producción.

## Goals / Non-Goals

**Goals:**
- Los 4 tests pasan en el entorno de desarrollo local
- No se altera la lógica de negocio ni los modelos
- Las soluciones son mínimas y focalizadas

**Non-Goals:**
- No se rediseña la infraestructura de tests
- No se modifica la configuración de rate limiting
- No se agregan nuevas dependencias

## Decisions

1. **test_migration.py y test_migration_002.py**: Extraer credenciales desde `_test_db_url()` en lugar de hardcodear. Los helpers asyncpg parsean la URL para obtener user, password, database, host y port. La URL de test es configurable vía `DATABASE_URL_TEST` o `DATABASE_URL`, con fallback a `postgresql+asyncpg://trace:trace@localhost:5432/trace_test` (el mismo default que usa conftest.py).

2. **test_padron_api.py**: Agregar `estado` al INSERT raw de `carrera` en `_seed_materia_cohorte()`. El modelo define `estado = Column(String(20), nullable=False, default="Activa")`, pero el INSERT raw no incluye la columna, causando `NotNullViolationError`. Se agrega con valor `'Activa'`.

3. **test_auth_identity_immutable.py**: No hay un fix único. El `_reset_rate_limiter_storage` fixture autouse ya existe en conftest.py y debería resetear el storage entre tests. Si persiste, se puede (a) reordenar tests para minimizar login calls, (b) hacer los login tests use un fixture compartido que haga login una vez, o (c) rate-limit las 5 llamadas. La estrategia: primero verificar que `_reset_rate_limiter_storage` funcione correctamente; si el rate limiter usa un singleton Limiter cuyo storage no se resetea bien, se corrige el fixture.

## Risks / Trade-offs

- **Riesgo**: Los migration tests mutan la BD real (`trace_test`). Si la BD no está disponible, se skipean (ya tienen `skipif`). El fix solo cambia las credenciales, no la dependencia de BD.
- **Riesgo**: El rate limiting podría seguir fallando si el storage del limiter no se resetea adecuadamente. En ese caso, se puede deshabilitar el rate limit en tests vía monkeypatch o feature flag.
