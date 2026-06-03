## 1. Configuración y dependencias

- [ ] 1.1 Agregar a `backend/requirements.txt` las deps nuevas: `argon2-cffi`, `pyjwt`, `pyotp`, `qrcode[pil]`, `slowapi`, `email-validator`. Pinear versiones compatibles con Python 3.13
- [ ] 1.2 Agregar a `backend/requirements-dev.txt` las deps de testing necesarias (ya están todas si 1.1 cubre runtime)
- [ ] 1.3 Extender `backend/app/core/config.py` con `REFRESH_TOKEN_EXPIRE_DAYS` (default 7), `PASSWORD_RESET_EXPIRE_MINUTES` (default 30), `TWO_FA_CHALLENGE_EXPIRE_MINUTES` (default 5), `LOGIN_RATE_LIMIT` (default "5/60s"), `TOTP_ISSUER` (default "activia-trace")
- [ ] 1.4 Actualizar `backend/.env.example` con las nuevas variables y valores por defecto (incluido `MAILER_MODE=console`)

## 2. Migración Alembic 002

- [ ] 2.1 Crear `backend/alembic/versions/002_user_auth.py` con la creación de las tablas `user`, `refresh_token`, `password_reset_token`, `two_factor_challenge` (ver `design.md` §D8)
- [ ] 2.2 Verificar que la migración aplica limpia sobre la DB de test (`alembic upgrade head` + `alembic downgrade base` round-trip)
- [ ] 2.3 Test de Alembic round-trip: `tests/unit/test_migration_002.py` que ejecuta `upgrade` → `downgrade` → `upgrade` y compara el schema con `inspect()`

## 3. Modelos ORM

- [ ] 3.1 Crear `backend/app/models/user.py` con `User` (`id` UUID, `tenant_id` FK, `email` str, `password_hash` str, `is_active` bool, `totp_secret` str|None cifrado, `totp_enabled` bool, mixin `BaseMixin` con timestamps y soft delete, UNIQUE `(tenant_id, email)`)
- [ ] 3.2 Crear `backend/app/models/refresh_token.py` con `RefreshToken` (`id`, `tenant_id`, `user_id`, `token_hash` UNIQUE, `expires_at`, `revoked_at`, `replaced_by_id` FK nullable, `user_agent`, `created_ip`, mixin con soft delete)
- [ ] 3.3 Crear `backend/app/models/password_reset_token.py` con `PasswordResetToken` (`id`, `tenant_id`, `user_id`, `token_hash` UNIQUE, `expires_at`, `used_at`, sin soft delete — fila efímera)
- [ ] 3.4 Crear `backend/app/models/two_factor_challenge.py` con `TwoFactorChallenge` (`id`, `tenant_id`, `user_id`, `token_hash` UNIQUE, `expires_at`, `used_at`, sin soft delete)
- [ ] 3.5 Actualizar `backend/app/models/__init__.py` para reexportar los 4 modelos nuevos
- [ ] 3.6 Tests unitarios: `tests/unit/test_user_model.py` (constraints, soft delete, encrypted TOTP secret round-trip), `tests/unit/test_token_models.py` (constraints, expira/revocado)

## 4. Schemas Pydantic (DTOs)

- [ ] 4.1 Crear `backend/app/schemas/auth.py` con `LoginRequest`, `TokenPair`, `RefreshRequest`, `LogoutRequest`, `UserMeResponse`, `TwoFactorChallengeResponse`, `TwoFactorEnrollResponse`, `TOTPConfirmRequest`, `TOTPVerifyRequest`, `ForgotRequest`, `ResetRequest`, `PasswordResetRequest` (todos con `extra='forbid'`)
- [ ] 4.2 Crear validador reutilizable `StrongPassword` (min 12, 1 mayúscula, 1 minúscula, 1 dígito) usado en `ResetRequest.new_password`
- [ ] 4.3 Tests unitarios: `tests/unit/test_auth_schemas.py` que valida `extra='forbid'`, validador de password fuerte, formatos de email

## 5. Core: security, rate limit, mail, audit

- [ ] 5.1 Implementar `backend/app/core/security.py`: `hash_password(plain)`, `verify_password(plain, hashed)` con Argon2id; `create_access_token(user_id, tenant_id, roles)` y `decode_access_token(token)` con PyJWT HS256; `hash_opaque_token(token) -> str` y `generate_opaque_token() -> str` (SHA-256 + `secrets.token_urlsafe(32)`)
- [ ] 5.2 Crear `backend/app/core/rate_limit.py` con `RateLimiter` que envuelve `slowapi` y expone `check(key: tuple[str, str], action: str) -> None | raises HTTPException(429)`. Usar `LOGIN_RATE_LIMIT` del config
- [ ] 5.3 Crear `backend/app/core/mail.py` con interfaz `MailSender` (`send_reset_link(email, link)`) y `ConsoleMailSender` que escribe un log JSON estructurado con `mail.to`, `mail.subject`, `mail.link`
- [ ] 5.4 Crear `backend/app/core/audit.py` con `record(code: str, payload: dict)` que emite un log JSON con prefijo `audit.` (call site listo para C-05; tabla llega después)
- [ ] 5.5 Tests unitarios: `tests/unit/test_security.py` (hash determinístico, verify OK/KO, JWT sign/verify/expire, opaque token entropy ≥256 bits), `tests/unit/test_rate_limit.py` (5 OK → 6ª 429, IPs distintas no comparten, reset tras 60s), `tests/unit/test_mail.py` (ConsoleMailSender loggea link), `tests/unit/test_audit.py` (record emite log con code y payload)

## 6. Repositorios

- [ ] 6.1 Crear `backend/app/repositories/user_repository.py` con `get_by_email(tenant_id, email)`, `get_by_id(tenant_id, id)`, `create(...)`, `update_password(...)`, `enable_totp(...)`, `disable_totp(...)`. Hereda de `BaseRepository[User]`, scope de tenant obligatorio
- [ ] 6.2 Crear `backend/app/repositories/refresh_token_repository.py` con `create(...)`, `get_by_token_hash(...)`, `revoke(token_id)`, `revoke_all_for_user(user_id)` (familia), `count_active_for_user(user_id)`
- [ ] 6.3 Crear `backend/app/repositories/password_reset_token_repository.py` con `create(...)`, `get_by_token_hash(...)`, `mark_used(token_id)`, `invalidate_all_pending_for_user(user_id)`
- [ ] 6.4 Crear `backend/app/repositories/two_factor_challenge_repository.py` con `create(...)`, `get_by_token_hash(...)`, `mark_used(token_id)`, `cleanup_expired()`
- [ ] 6.5 Tests de integración contra DB real: `tests/integration/test_user_repository.py`, `test_refresh_token_repository.py`, etc. (12 tests mínimo entre los 4)

## 7. Services

- [ ] 7.1 Crear `backend/app/services/token_service.py` con `issue_token_pair(user) -> TokenPair` y `rotate_refresh(refresh_token) -> TokenPair` (reusa el reuso-detection del design)
- [ ] 7.2 Crear `backend/app/services/password_service.py` con `request_reset(email, tenant_id, mailer) -> None`, `confirm_reset(token, new_password) -> None` (revoca familia refresh)
- [ ] 7.3 Crear `backend/app/services/totp_service.py` con `enroll(user) -> TwoFactorEnrollResponse` y `verify(user, code) -> bool` (usa `pyotp`, `valid_window=1`)
- [ ] 7.4 Crear `backend/app/services/auth_service.py` orquestador: `login(email, password, tenant_id, client_ip) -> TokenPair | TwoFactorChallengeResponse` (rate-limited, audit, 2FA gate), `verify_2fa(challenge_token, code) -> TokenPair`, `logout(refresh_token, user_id) -> None`
- [ ] 7.5 Tests unitarios: `tests/unit/test_auth_service.py`, `test_token_service.py`, `test_password_service.py`, `test_totp_service.py` (con repos mockeados por sesión DB; sin mock de DB, sí repos reales en fixtures)

## 8. Dependencias FastAPI

- [ ] 8.1 Crear/extender `backend/app/core/dependencies.py` con `get_current_user(creds: HTTPAuthorizationCredentials = Depends(HTTPBearer()))` que retorna `UserContext(user_id, tenant_id, roles)` desde el JWT. Errores: 401 con detalle específico (sin token, expirado, firma inválida)
- [ ] 8.2 Tests: `tests/unit/test_get_current_user.py` (token válido, expirado, malformado, firma inválida, query string con `?user_id=` no afecta la identidad)

## 9. Routers

- [ ] 9.1 Crear `backend/app/api/v1/routers/auth.py` con los endpoints:
  - `POST /login` (rate-limited, no auth)
  - `POST /2fa/verify` (rate-limited, no auth)
  - `POST /refresh` (rate-limited, no auth)
  - `POST /logout` (auth + `get_current_user`, recibe refresh en body)
  - `POST /forgot` (rate-limited, no auth)
  - `POST /reset` (rate-limited, no auth)
  - `POST /2fa/enroll` (auth + `get_current_user`)
  - `POST /2fa/confirm` (auth + `get_current_user`)
  - `GET /me` (auth + `get_current_user`, retorna `UserMeResponse`) — útil para C-21 frontend
- [ ] 9.2 Registrar el router en `backend/app/api/v1/routers/__init__.py` y en `backend/app/main.py`
- [ ] 9.3 Manejo de errores estandarizado: `HTTPException` con códigos 400/401/403/404/409/422/429/500 según matriz de `docs/ARQUITECTURA.md` §3
- [ ] 9.4 Tests de integración E2E: `tests/integration/test_auth_login.py`, `test_auth_refresh.py`, `test_auth_2fa.py`, `test_auth_recovery.py`, `test_auth_rate_limit.py`, `test_auth_identity_immutable.py`

## 10. Verify y cobertura

- [ ] 10.1 Correr `pytest -v` y verificar 0 failures, 0 errors. Skipped permitidos solo los que ya existían
- [ ] 10.2 Correr `pytest --cov=app --cov-report=term-missing` y verificar ≥80% líneas globales y ≥90% en `app/services/auth_service.py`, `app/services/token_service.py`, `app/services/totp_service.py`, `app/services/password_service.py`
- [ ] 10.3 Verificar que `openspec status --change c-03-auth-jwt-2fa` muestre todas las tasks completas
- [ ] 10.4 Sanity check: levantar la app (`uvicorn app.main:app`), hacer un login con curl, verificar que el JWT se puede decodificar con el `SECRET_KEY` del `.env` y que `GET /me` con el token responde 200

## 11. Documentación

- [ ] 11.1 Actualizar `CHANGES.md`: marcar C-03 como completado (NO todavía — eso lo hace `openspec archive`)
- [ ] 11.2 Actualizar `backend/.env.example` con todas las variables nuevas y valores por defecto
- [ ] 11.3 Actualizar `docs/ARQUITECTURA.md` con un §5.1.1 "C-03 implementación" que referencie los archivos clave (no es bloqueante)
