## Context

C-01 (foundation-setup) y C-02 (core-models-y-tenancy) ya están archivados en producción. El backend tiene:

- `Tenant` con `BaseMixin` (`id` UUID, `tenant_id`, `created_at`, `updated_at`, `deleted_at`).
- `BaseRepository[T]` genérico con scope de tenant obligatorio.
- `EncryptionService` (Fernet AES-128-CBC en su implementación actual — **C-07 lo reemplaza por AES-256 real**; para C-03 se reusa tal cual para tokens opacos).
- Migración 001 aplicada.
- `Settings` con `SECRET_KEY` (≥32 chars), `ENCRYPTION_KEY` (≥32 chars) y `ACCESS_TOKEN_EXPIRE_MINUTES` (default 15).
- `app/core/security.py` es un placeholder de 9 líneas marcado `RESERVADO para C-03`.
- 100 tests passing, 1 skipped, ~80% coverage.

El frontend todavía no existe (llega con C-21). El worker de cola tampoco (C-12). Los cambios de C-03 son **solo backend** y deben dejar una API lista para que C-04 (rbac) enchufe `require_permission` y C-21 (frontend) consuma el flujo.

Stakeholders:
- **Equipo Backend Core** (implementa) — necesita contratos claros y tests contra DB real.
- **Equipo Frontend** (consume en C-21) — necesita saber qué headers/cookies/body espera cada endpoint.
- **Equipo Seguridad** (auditoría) — necesita que el audit log mínimo de `LOGIN_OK`/`LOGIN_FAIL`/`LOGOUT`/`PASSWORD_RESET` ya quede escrito desde este change (la tabla llega en C-05; acá dejamos los **call sites** listos detrás de un helper, sin que el cambio se rompa si la tabla no existe).

## Goals / Non-Goals

**Goals:**
- Login + JWT + refresh rotation + logout funcionales y verificados contra DB real.
- 2FA TOTP opcional end-to-end (enrolar, verificar, gate entre credenciales y sesión).
- Recuperación de contraseña con token de un solo uso.
- Rate limit 5/60s por IP+email en los endpoints sensibles.
- Identidad derivada EXCLUSIVAMENTE del JWT verificado — `get_current_user` es la única puerta de entrada.
- Cobertura ≥80% líneas, ≥90% de las reglas de negocio de auth.
- Cambios aislados al backend; nada en frontend, nada en worker.

**Non-Goals:**
- Catálogo de roles ni permisos (C-04).
- Audit log persistente (C-05): dejamos **call sites** con un helper `_audit(code, payload)` que escribe en `logging` estructurado; cuando C-05 cree la tabla `audit_log`, se conecta sin tocar este código.
- Envío real de emails: `MailSender` con `ConsoleMailSender` que escribe a logs JSON; N8N llega en C-12.
- SSO con Moodle (ADR-001 Fase 2).
- Impersonación (ADR-004).
- Sesiones revocadas individualmente en memoria distribuida (C-03 hace revocación por **token hash + DB row `revoked_at`**; un refresh revocado se detecta en `refresh` comparando hash).

## Decisions

### D1 — `pyjwt` sobre `python-jose`

`python-jose` está sin release desde 2022 y tiene CVEs conocidos. `pyjwt` es mantenida, simple, y cubre HS256/HS512/RS256. Firmamos con **HS256 + `SECRET_KEY`** (el proyecto es single-issuer por ahora). Si en el futuro aparece multi-issuer, se migra a RS256 sin romper el contrato de claims.

**Alternativa descartada:** `authlib`. Es más grande y trae dependencias que no necesitamos (OAuth2/OIDC servers); C-03 no es un IdP.

### D2 — Refresh tokens opacos con hash en DB, NO JWT

Los refresh tokens se generan con `secrets.token_urlsafe(32)` (256 bits de entropía), se devuelven al cliente una sola vez en claro, y se guardan en DB hasheados con SHA-256. Cada `refresh` lee por hash, valida `expires_at` y `revoked_at is None`, y rota creando un nuevo par (`replaced_by_id` apunta al nuevo). **La familia entera se invalida si se detecta reuso** (token ya revocado pero presentado) — esto es el patrón OAuth2 "refresh token rotation with reuse detection".

**Por qué no JWT para refresh:** los JWT no se pueden revocar sin blacklist. La rotación + DB row ya implementa revocación instantánea sin estado extra.

### D3 — Argon2id (no bcrypt, no scrypt)

`argon2-cffi` con parámetros por defecto (mem=64MB, t=3, p=4). Cubre la guía NIST SP 800-63B. El password nunca aparece en logs ni en responses (ni siquiera hasheado en responses de error).

### D4 — TOTP con `pyotp`, secret cifrado en DB

`pyotp` con `totp.TOTP(secret).verify(code, valid_window=1)`. El secret TOTP se guarda cifrado con `EncryptionService` (Fernet) en `user.totp_secret`. El `is_active` del usuario y `totp_enabled` son condiciones independientes: un usuario inactivo (`is_active=False`) no puede loguear aunque tenga 2FA; un usuario con `totp_enabled=True` DEBE completar el gate.

**Alternativa descartada:** SMS/email OTP. SMS no aplica; email se cubre con `MailSender` mock hasta C-12.

### D5 — Rate limit con `slowapi` en memoria

`slowapi` aplica un decorador `@limiter.limit("5/60s", key_func=lambda r: (r.client.host, r.json()["email"]))`. Suficiente para un solo proceso de API. Cuando el deploy pase a multi-replica (Easypanel lo permite), se cambia el backend de `slowapi` a Redis en un change dedicado (no es bloqueante para C-03).

**Por qué no en DB:** una query por cada `login` añade latencia innecesaria. El rate limit es por-IP-y-email — la IP es efímera y aceptar la imprecisión cross-replica durante el MVP es la decisión correcta.

### D6 — Challenge token para 2FA: opaco, no JWT

El flujo 2FA es:
1. `POST /login` con credenciales válidas + `totp_enabled=True` → respuesta **sin tokens** con `{"2fa_required": true, "challenge_token": "<opaque>"}`. El `challenge_token` es un string `secrets.token_urlsafe(32)`, hasheado en una mini-tabla `two_factor_challenge` (TTL 5 min, un solo uso).
2. Cliente pide TOTP, hace `POST /2fa/verify { challenge_token, code }` → si OK, emite par access+refresh y borra el challenge.

**Por qué no JWT en el challenge:** un JWT con `sub=user_id` filtraría el id del usuario en un log intermedio. El challenge token es opaco y se valida por hash.

### D7 — `get_current_user` como ÚNICA puerta de entrada a la identidad

```python
async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    session: AsyncSession = Depends(get_session),
) -> UserContext:
    payload = jwt.decode(creds.credentials, settings.SECRET_KEY, algorithms=["HS256"])
    user_id = UUID(payload["sub"])
    tenant_id = UUID(payload["tenant_id"])
    return UserContext(user_id=user_id, tenant_id=tenant_id, roles=payload.get("roles", []))
```

Los routers de C-04 en adelante declararán `Depends(get_current_user)`. C-03 NO usa `?user_id=` en query string como selector — la KB dice que un id en la request es **dato de negocio a validar contra permisos**, nunca identidad.

### D8 — Migración Alembic 002, no editar la 001

Una migración por cambio de schema (regla dura). La 002 crea:
- `user (id UUID PK, tenant_id UUID FK → tenant.id, email TEXT, password_hash TEXT, is_active BOOL, totp_secret TEXT NULL, totp_enabled BOOL, created_at, updated_at, deleted_at)` con UNIQUE `(tenant_id, email)`.
- `refresh_token (id UUID PK, tenant_id UUID FK, user_id UUID FK, token_hash TEXT UNIQUE, expires_at TIMESTAMP, revoked_at TIMESTAMP NULL, replaced_by_id UUID NULL FK → refresh_token.id, created_at, deleted_at)`.
- `password_reset_token (id UUID PK, tenant_id UUID FK, user_id UUID FK, token_hash TEXT UNIQUE, expires_at TIMESTAMP, used_at TIMESTAMP NULL, created_at)`.
- `two_factor_challenge (id UUID PK, tenant_id UUID FK, user_id UUID FK, token_hash TEXT UNIQUE, expires_at TIMESTAMP, used_at TIMESTAMP NULL)`.

Todas las tablas con `tenant_id` + índice. Soft delete solo en `user` y `refresh_token` (los reset tokens y challenges son efímeros y se purgan).

### D9 — Auditoría: helper + log estructurado, no tabla

`app/core/audit.py` con `record(code: str, payload: dict) → None` que emite un log JSON con `audit.code`, `audit.tenant_id`, `audit.user_id`, `audit.payload`. En C-05 el helper pasa a escribir en `audit_log` además de loggear; cero cambios en los call sites.

**Codes de C-03:** `LOGIN_OK`, `LOGIN_FAIL`, `LOGIN_2FA_REQUIRED`, `LOGIN_2FA_OK`, `LOGIN_2FA_FAIL`, `REFRESH_OK`, `REFRESH_REUSE_DETECTED`, `LOGOUT`, `PASSWORD_RESET_REQUEST`, `PASSWORD_RESET_OK`, `TOTP_ENROLL_STARTED`, `TOTP_ENROLL_CONFIRMED`, `RATE_LIMIT_HIT`.

### D10 — `extra='forbid'` en todos los schemas

Regla dura #5. LoginRequest, RefreshRequest, ResetRequest, TOTPRequest, ForgotRequest, TokenPair, etc. — todos `model_config = ConfigDict(extra='forbid')`.

## Risks / Trade-offs

- **Rate limit in-memory no escala multi-replica** → Aceptado para MVP. Cambio a Redis en un change dedicado cuando aparezca la necesidad. *Mitigation:* documentar en `CHANGES.md` como deuda técnica.
- **ConsoleMailSender filtra el link de reset en logs** → En producción, los logs van a stdout/JSON, no accesibles a usuarios; en desarrollo, es la única forma de probar el flujo. *Mitigation:* marcar el `MAILER_MODE=console` en `.env.example` con warning.
- **Argon2id con 64MB de memoria puede ser lento en CI con recursos limitados** → Aceptable: el login es una operación humana, 100-300ms está dentro de SLA. *Mitigation:* parametrizar el costo por env var (`ARGON2_TIME_COST`, default 3) si CI muestra timeouts.
- **Reuso de refresh token revocado invalida la familia entera** → Decisión correcta de seguridad (mitiga token theft) pero un usuario que se loguea desde un device nuevo verá revocada la sesión del device viejo. *Mitigation:* documentar en la respuesta del endpoint y en tests.
- **`SECRET_KEY` rotada invalida TODAS las sesiones activas** → Decisión correcta (compromiso = rotación inmediata). *Mitigation:* nadie debería estar rotando esta key sin un runbook; C-05 documenta la rotación.
- **2FA challenge token en memoria de proceso si la tabla `two_factor_challenge` no persiste** → La tabla es parte de la migración 002, así que persiste. Tests confirman round-trip.

## Migration Plan

1. Branch: `nikoc3-auth` (siguiendo convención del proyecto: `nikoc<N>-<slug>`).
2. Aplicar la migración 002 con `alembic upgrade head` sobre la DB de dev y la de test.
3. Seed mínimo: un script `scripts/seed_admin.py` (NO parte de este change) que cree el primer `tenant` + `user admin` para QA manual; en este change, los tests crean el seed.
4. Rollback: `alembic downgrade -1` borra las 3 tablas. Ningún dato de C-01/C-02 se ve afectado.
5. C-04 enchufa `require_permission` reutilizando `get_current_user` sin cambios.

## Open Questions

- ¿`TOTP_ISSUER` debe ser por tenant o global? **Decisión actual:** global (el nombre del producto, configurable vía env). Si dos tenants quieren nombres distintos, se pasa a `Tenant.issuer_name` en C-07.
- ¿`refresh_token` debe tener `user_agent` / `ip` para el panel "dispositivos activos" de F11? **Decisión actual:** sí, columnas `user_agent` y `created_ip`, ambas opcionales. El panel UI llega en C-20.
- ¿Cuándo se considera "vencido" un challenge 2FA? **Decisión actual:** 5 minutos desde creación, sin ventana de reuso.
