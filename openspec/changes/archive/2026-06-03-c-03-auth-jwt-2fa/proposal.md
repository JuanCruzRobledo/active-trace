## Why

Hoy el backend expone solo `/health`. C-01 (foundation) y C-02 (core-models-y-tenancy) ya están en producción archivada: tenemos `Tenant`, `BaseMixin`, `BaseRepository` con scope tenant, `EncryptionService` (Fernet AES) y la Migración 001 aplicada. Pero **no existe ninguna forma de iniciar sesión**: ningún endpoint, ningún modelo de `User`, ninguna dependencia que resuelva identidad. C-04 (rbac), C-06 (estructura académica), C-12 (comunicaciones) y todos los cambios posteriores dependen de poder autenticar a un usuario y emitir una sesión. **Este change es la base no negociable de toda la plataforma.**

## What Changes

- **Modelos nuevos**: `User` (pertenece a un `tenant`, con `email` único por tenant, `password_hash` Argon2id, `totp_secret` opcional, `totp_enabled`, `is_active`), `RefreshToken` (token hasheado, `expires_at`, `revoked_at`, `replaced_by_id` para rotación), `PasswordResetToken` (token hasheado, `expires_at`, `used_at`).
- **Endpoints nuevos** en `routers/auth.py`:
  - `POST /api/auth/login` — email + password → access (15 min) + refresh. Si 2FA activo → respuesta intermedia `2fa_required` con `challenge_token` opaco.
  - `POST /api/auth/2fa/verify` — challenge_token + código TOTP → emite access + refresh.
  - `POST /api/auth/refresh` — rota refresh (el usado se marca `revoked_at` + `replaced_by_id`), emite par nuevo.
  - `POST /api/auth/logout` — revoca el refresh presentado.
  - `POST /api/auth/forgot` — genera token de un solo uso, lo entrega al servicio de mail (interfaz, implementación mock en este change).
  - `POST /api/auth/reset` — token + nueva contraseña.
  - `POST /api/auth/2fa/enroll` — genera secret TOTP, devuelve QR/URI; el usuario lo confirma con un código.
  - `POST /api/auth/2fa/confirm` — confirma secret con un código válido → `totp_enabled = true`.
- **Servicio de mail**: interfaz `MailSender` con un `ConsoleMailSender` (escribe en log estructurado) para no acoplar el cambio a N8N. La implementación real llega con C-12.
- **Rate limiting**: 5 intentos fallidos por IP+email en 60 s en `/login`, `/2fa/verify`, `/forgot`, `/reset`. Implementación en memoria con `slowapi` (suficiente para un solo proceso; el cambio a Redis queda para cuando aparezca multi-replica).
- **Dependencia `get_current_user`**: resuelve el usuario + tenant desde el JWT access verificado, lo expone al resto de los endpoints.
- **Migración Alembic `002_user_auth`**: crea `user`, `refresh_token`, `password_reset_token` con índices por `(tenant_id, email)`.
- **Tests**: login OK/KO, refresh rotation (reuso invalida la familia), 2FA enrolar + verificar, recuperación token único, rate limit, identidad inmutable (un query string con `?user_id=` no afecta la identidad resuelta).

## Capabilities

### New Capabilities

- `auth-jwt`: autenticación con email + password (Argon2id), emisión de access JWT (15 min, claims `sub`/`tenant_id`/`roles`/`exp`) + refresh con rotación, revocación, logout, dependency `get_current_user` que extrae identidad exclusivamente del JWT verificado. Regla de oro: ningún parámetro de la petición puede alterar la identidad.
- `password-recovery`: solicitud de recuperación por email con token de un solo uso, expiración corta (≤30 min) y endpoint de reset que invalida tokens anteriores. Rate limit por IP+email.
- `two-factor-auth`: TOTP opcional por usuario (RFC 6238), enrolamiento que devuelve secret + URI otpauth, verificación con código de 6 dígitos, gate entre validación de credenciales y emisión de sesión.

### Modified Capabilities

- *(vacío — C-03 no modifica los requisitos de capabilities existentes; C-01/C-02 ya están archivados y sus specs no cambian con este change.)*

## Impact

- **Backend (afectado)**: `app/core/security.py` (placeholder → JWT + Argon2id), nuevo `app/core/rate_limit.py`, nuevo `app/core/mail.py` (interfaz + ConsoleMailSender), nuevo `app/api/v1/routers/auth.py`, `app/api/v1/routers/__init__.py` (registra `auth`), `app/main.py` (state de `slowapi` si aplica), `app/core/dependencies.py` (suma `get_current_user`).
- **Modelos**: nuevos archivos `app/models/user.py`, `app/models/refresh_token.py`, `app/models/password_reset_token.py`; `app/models/__init__.py` los reexporta.
- **Schemas**: nuevos `app/schemas/auth.py` (LoginRequest/Response, RefreshRequest/Response, ChallengeTokenResponse, TOTPRequest, ForgotRequest, ResetRequest, UserMeResponse, TokenPair).
- **Services**: nuevos `app/services/auth_service.py`, `app/services/token_service.py`, `app/services/password_service.py`, `app/services/totp_service.py`, `app/services/rate_limit_service.py`, `app/services/mail_service.py`.
- **Repositories**: nuevos `app/repositories/user_repository.py`, `app/repositories/refresh_token_repository.py`, `app/repositories/password_reset_token_repository.py`.
- **Migración**: `backend/alembic/versions/002_user_auth.py` (tablas + índices + FKs).
- **Dependencias nuevas**: `argon2-cffi` (passwords), `python-jose[cryptography]` o `pyjwt` (JWT), `pyotp` (TOTP), `qrcode[pil]` (URI otpauth), `slowapi` (rate limit), `email-validator` (validar email). Ya están en `requirements.txt`; falta confirmar pinned versions.
- **Tests**: nueva `tests/unit/test_security.py`, `tests/unit/test_auth_service.py`, `tests/unit/test_token_service.py`, `tests/unit/test_totp_service.py`, `tests/unit/test_rate_limit_service.py`, `tests/unit/test_password_reset.py`; `tests/integration/test_auth_login.py`, `test_auth_refresh.py`, `test_auth_2fa.py`, `test_auth_recovery.py`, `test_auth_rate_limit.py`, `test_auth_identity_immutable.py`; ampliar `tests/conftest.py` con `user_factory` y `token_factory` que usan DB real.
- **Config**: `Settings` ya tiene `SECRET_KEY`, `ENCRYPTION_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`; agregar `REFRESH_TOKEN_EXPIRE_DAYS` (default 7), `PASSWORD_RESET_EXPIRE_MINUTES` (default 30), `LOGIN_RATE_LIMIT` (default "5/60s"), `TOTP_ISSUER` (default "activia-trace").
- **No afectado**: frontend (se construye en C-21), worker (C-12), integraciones Moodle (C-09).
