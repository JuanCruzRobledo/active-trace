"""AuditService — registro persistente de acciones significativas (C-05).

Reemplaza gradualmente al logger ``core/audit.py``. Persiste en DB via
``AuditLogRepository`` y opcionalmente conserva el log JSON como fallback.

Todos los códigos de acción se validan contra una whitelist antes de
persistir (defense-in-depth contra typos o códigos no estandarizados).
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.core.config import Settings
from app.repositories.audit_log_repository import AuditLogRepository

_logger = logging.getLogger("audit")

# ── Catálogo de códigos de acción estandarizados ─────────────────────────────
# Cada código representa una acción significativa que debe quedar registrada
# en el audit log. La whitelist es defense-in-depth contra typos.

ACCION_CALIFICACIONES_IMPORTAR = "CALIFICACIONES_IMPORTAR"
ACCION_PADRON_CARGAR = "PADRON_CARGAR"
ACCION_PADRON_VACIAR = "PADRON_VACIAR"
ACCION_COMUNICACION_ENVIAR = "COMUNICACION_ENVIAR"
ACCION_ASIGNACION_MODIFICAR = "ASIGNACION_MODIFICAR"
ACCION_LIQUIDACION_CERRAR = "LIQUIDACION_CERRAR"
ACCION_ENCUENTRO_CREAR = "ENCUENTRO_CREAR"
ACCION_ENCUENTRO_MODIFICAR = "ENCUENTRO_MODIFICAR"
ACCION_ENCUENTRO_ELIMINAR = "ENCUENTRO_ELIMINAR"
ACCION_GUARDIA_REGISTRAR = "GUARDIA_REGISTRAR"
ACCION_GUARDIA_MODIFICAR = "GUARDIA_MODIFICAR"
ACCION_IMPERSONACION_INICIAR = "IMPERSONACION_INICIAR"
ACCION_IMPERSONACION_FINALIZAR = "IMPERSONACION_FINALIZAR"

# Códigos heredados de C-03 (auth)
ACCION_LOGIN_OK = "LOGIN_OK"
ACCION_LOGIN_FAIL = "LOGIN_FAIL"
ACCION_LOGIN_2FA_REQUIRED = "LOGIN_2FA_REQUIRED"
ACCION_LOGIN_2FA_OK = "LOGIN_2FA_OK"
ACCION_LOGIN_2FA_FAIL = "LOGIN_2FA_FAIL"
ACCION_REFRESH_OK = "REFRESH_OK"
ACCION_REFRESH_REUSE_DETECTED = "REFRESH_REUSE_DETECTED"
ACCION_LOGOUT = "LOGOUT"
ACCION_PASSWORD_RESET_REQUEST = "PASSWORD_RESET_REQUEST"
ACCION_PASSWORD_RESET_OK = "PASSWORD_RESET_OK"
ACCION_TOTP_ENROLL_STARTED = "TOTP_ENROLL_STARTED"
ACCION_TOTP_ENROLL_CONFIRMED = "TOTP_ENROLL_CONFIRMED"
ACCION_RATE_LIMIT_HIT = "RATE_LIMIT_HIT"
ACCION_TOKEN_SIGNATURE_INVALID = "TOKEN_SIGNATURE_INVALID"

# Whitelist completa (unión de códigos C-03 + C-05)
VALID_ACCION_CODES: frozenset[str] = frozenset({
    ACCION_CALIFICACIONES_IMPORTAR,
    ACCION_PADRON_CARGAR,
    ACCION_PADRON_VACIAR,
    ACCION_COMUNICACION_ENVIAR,
    ACCION_ASIGNACION_MODIFICAR,
    ACCION_LIQUIDACION_CERRAR,
    ACCION_IMPERSONACION_INICIAR,
    ACCION_IMPERSONACION_FINALIZAR,
    ACCION_ENCUENTRO_CREAR,
    ACCION_ENCUENTRO_MODIFICAR,
    ACCION_ENCUENTRO_ELIMINAR,
    ACCION_GUARDIA_REGISTRAR,
    ACCION_GUARDIA_MODIFICAR,
    ACCION_LOGIN_OK,
    ACCION_LOGIN_FAIL,
    ACCION_LOGIN_2FA_REQUIRED,
    ACCION_LOGIN_2FA_OK,
    ACCION_LOGIN_2FA_FAIL,
    ACCION_REFRESH_OK,
    ACCION_REFRESH_REUSE_DETECTED,
    ACCION_LOGOUT,
    ACCION_PASSWORD_RESET_REQUEST,
    ACCION_PASSWORD_RESET_OK,
    ACCION_TOTP_ENROLL_STARTED,
    ACCION_TOTP_ENROLL_CONFIRMED,
    ACCION_RATE_LIMIT_HIT,
    ACCION_TOKEN_SIGNATURE_INVALID,
})


class AuditService:
    """Servicio de auditoría: valida y persiste acciones significativas.

    Args:
        audit_log_repo: Repositorio append-only de auditoría.
        settings: Config del sistema.
    """

    def __init__(
        self,
        audit_log_repo: AuditLogRepository,
        settings: Settings,
    ) -> None:
        self._repo = audit_log_repo
        self._settings = settings

    async def register(
        self,
        accion: str,
        actor_id: UUID,
        tenant_id: UUID,
        *,
        detalle: dict | None = None,
        filas_afectadas: int | None = None,
        materia_id: UUID | None = None,
        impersonado_id: UUID | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Registra una acción en el audit log.

        Valida el código contra la whitelist antes de persistir.
        Opcionalmente emite el log JSON como fallback.

        Args:
            accion: Código estandarizado de la acción.
            actor_id: UUID del usuario que ejecutó la acción.
            tenant_id: UUID del tenant.
            detalle: Contexto adicional JSON (opcional).
            filas_afectadas: Cantidad de registros involucrados (opcional).
            materia_id: UUID de la materia asociada (opcional).
            impersonado_id: UUID del usuario impersonado (opcional).
            ip: Dirección IP del cliente (opcional).
            user_agent: User-Agent del cliente (opcional).

        Raises:
            ValueError: Si el código de acción no está en la whitelist.
        """
        if accion not in VALID_ACCION_CODES:
            _logger.warning(
                "audit.unknown_code",
                extra={"extra": {"audit.code": accion, "audit.unknown": True}},
            )
            raise ValueError(f"Unknown audit action code: {accion}")

        # Persistir en DB
        await self._repo.register(
            tenant_id=tenant_id,
            actor_id=actor_id,
            accion=accion,
            detalle=detalle,
            filas_afectadas=filas_afectadas,
            materia_id=materia_id,
            impersonado_id=impersonado_id,
            ip=ip,
            user_agent=user_agent,
        )

        # Log JSON como fallback/auditoría adicional
        _logger.info(
            "audit.event",
            extra={
                "extra": {
                    "audit.code": accion,
                    "audit.payload": {
                        "actor_id": str(actor_id),
                        "tenant_id": str(tenant_id),
                        "impersonado_id": str(impersonado_id) if impersonado_id else None,
                        "materia_id": str(materia_id) if materia_id else None,
                        "detalle": detalle,
                        "filas_afectadas": filas_afectadas,
                        "ip": ip,
                    },
                }
            },
        )
