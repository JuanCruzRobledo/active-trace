"""Audit helper — log estructurado de eventos de seguridad (C-03/C-05).

Decisión D9 (design.md): ``record(code, payload)`` escribe un log JSON
con prefijo ``audit.`` y los campos del payload.

**C-05**: Se agregó ``AuditService`` (``app/services/audit_service.py``) como
reemplazo primario con persistencia en DB. Este módulo continúa funcionando
como fallback JSON para backward compatibility — los call sites que quieran
persistencia en DB deben usar ``AuditService.register()`` además de (o en
reemplazo de) ``audit.record()``.

Codes de C-03 (ver ``specs/auth-jwt/spec.md`` y ``two-factor-auth/spec.md``):

- ``LOGIN_OK`` / ``LOGIN_FAIL``
- ``LOGIN_2FA_REQUIRED`` / ``LOGIN_2FA_OK`` / ``LOGIN_2FA_FAIL``
- ``REFRESH_OK`` / ``REFRESH_REUSE_DETECTED``
- ``LOGOUT``
- ``PASSWORD_RESET_REQUEST`` / ``PASSWORD_RESET_OK``
- ``TOTP_ENROLL_STARTED`` / ``TOTP_ENROLL_CONFIRMED``
- ``RATE_LIMIT_HIT``
- ``TOKEN_SIGNATURE_INVALID``

Codes de C-05:

- ``CALIFICACIONES_IMPORTAR`` / ``PADRON_CARGAR``
- ``COMUNICACION_ENVIAR`` / ``ASIGNACION_MODIFICAR``
- ``LIQUIDACION_CERRAR``
- ``IMPERSONACION_INICIAR`` / ``IMPERSONACION_FINALIZAR``
"""

from __future__ import annotations

import logging
from typing import Any

# Logger dedicado de auditoría (separado del logger raíz) para poder
# enviarlo a un sink distinto en producción (C-05).
_audit_logger = logging.getLogger("audit")


def record(code: str, payload: dict[str, Any] | None = None) -> None:
    """Registra un evento de auditoría.

    Emite un log nivel ``INFO`` con prefijo ``audit.`` y los campos del
    payload mergeados. En C-05, este helper además escribirá en la tabla
    ``audit_log`` (sin cambios en los call sites).

    Args:
        code: Código del evento (ver lista arriba). Se valida contra
            una whitelist para evitar typos silenciosos.
        payload: Campos adicionales a loggear (user_id, tenant_id, ip,
            email, motivo, etc.). NUNCA incluir passwords, tokens en
            claro, ni secretos.

    Note:
        No es async — el logging es local (in-memory) y barato.
    """
    if code not in _VALID_CODES:
        # Codes desconocidos se loggean igual con un warning para detectar
        # typos en desarrollo, pero no fallan en runtime.
        _audit_logger.warning(
            "audit.unknown_code",
            extra={"extra": {"audit.code": code, "audit.unknown": True}},
        )

    extra: dict[str, Any] = {"audit.code": code, "audit.payload": payload or {}}
    _audit_logger.info("audit.event", extra={"extra": extra})


# Whitelist de codes conocidos (defense in depth contra typos).
_VALID_CODES: frozenset[str] = frozenset(
    {
        # C-03 (auth)
        "LOGIN_OK",
        "LOGIN_FAIL",
        "LOGIN_2FA_REQUIRED",
        "LOGIN_2FA_OK",
        "LOGIN_2FA_FAIL",
        "REFRESH_OK",
        "REFRESH_REUSE_DETECTED",
        "LOGOUT",
        "PASSWORD_RESET_REQUEST",
        "PASSWORD_RESET_OK",
        "TOTP_ENROLL_STARTED",
        "TOTP_ENROLL_CONFIRMED",
        "RATE_LIMIT_HIT",
        "TOKEN_SIGNATURE_INVALID",
        # C-05 (audit log + impersonation)
        "CALIFICACIONES_IMPORTAR",
        "PADRON_CARGAR",
        "COMUNICACION_ENVIAR",
        "ASIGNACION_MODIFICAR",
        "LIQUIDACION_CERRAR",
        "IMPERSONACION_INICIAR",
        "IMPERSONACION_FINALIZAR",
    }
)
