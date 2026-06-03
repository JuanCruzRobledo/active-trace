"""Tests para ``app.core.audit`` (C-03): log estructurado de eventos de seguridad."""

from __future__ import annotations

import logging
import re

import pytest


# ===========================================================================
# record() básico
# ===========================================================================


class TestRecordBasic:
    """``record(code, payload)`` emite un log con los campos correctos."""

    def test_record_does_not_raise(self):
        from app.core.audit import record

        # No debe levantar ni con payload vacío
        record("LOGIN_OK")
        record("LOGIN_OK", {"user_id": "abc"})

    def test_record_emits_audit_event_log(self, caplog):
        from app.core.audit import record

        caplog.set_level(logging.INFO, logger="audit")
        record("LOGIN_OK", {"user_id": "u-1", "tenant_id": "t-1"})

        # Buscar el log emitido
        audit_records = [r for r in caplog.records if r.name == "audit"]
        assert len(audit_records) >= 1
        rec = audit_records[0]
        assert "audit.event" in rec.getMessage()

    def test_record_payload_appears_in_log(self, caplog):
        from app.core.audit import record

        caplog.set_level(logging.INFO, logger="audit")
        record("LOGIN_OK", {"user_id": "u-42", "tenant_id": "t-99"})

        # Verificar que el payload está en los extras del log record
        rec = next(r for r in caplog.records if r.name == "audit")
        assert rec.extra is not None
        assert rec.extra["audit.code"] == "LOGIN_OK"
        assert rec.extra["audit.payload"]["user_id"] == "u-42"
        assert rec.extra["audit.payload"]["tenant_id"] == "t-99"

    def test_record_empty_payload(self, caplog):
        from app.core.audit import record

        caplog.set_level(logging.INFO, logger="audit")
        record("LOGIN_OK")  # sin payload

        rec = next(r for r in caplog.records if r.name == "audit")
        assert rec.extra["audit.code"] == "LOGIN_OK"
        assert rec.extra["audit.payload"] == {}


# ===========================================================================
# Códigos conocidos vs desconocidos
# ===========================================================================


class TestAuditCodes:
    """Códigos conocidos pasan; desconocidos también pero con warning."""

    def test_known_codes_emit_no_warning(self, caplog):
        from app.core.audit import record

        caplog.set_level(logging.INFO, logger="audit")
        record("LOGIN_OK", {"user_id": "u"})
        record("LOGIN_FAIL", {"reason": "bad_password"})
        record("REFRESH_OK", {"user_id": "u"})
        record("LOGOUT", {"user_id": "u"})
        record("PASSWORD_RESET_REQUEST", {"user_id": "u"})

        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) == 0

    def test_unknown_code_emits_warning(self, caplog):
        from app.core.audit import record

        caplog.set_level(logging.INFO, logger="audit")
        record("TYPO_CODE", {"foo": "bar"})

        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) >= 1
        assert "audit.unknown_code" in warnings[0].getMessage()

    def test_unknown_code_still_works(self, caplog):
        """Aunque el code sea desconocido, el record funciona (no falla)."""
        from app.core.audit import record

        caplog.set_level(logging.INFO, logger="audit")
        record("WEIRD_CODE_42", {"data": "x"})

        # El log se emite igual
        rec = next(r for r in caplog.records if r.name == "audit")
        assert rec.extra["audit.code"] == "WEIRD_CODE_42"


# ===========================================================================
# Códigos del spec (whitelist)
# ===========================================================================


class TestSpecCodes:
    """Códigos del design D9 / specs."""

    @pytest.mark.parametrize(
        "code",
        [
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
        ],
    )
    def test_all_spec_codes_accepted(self, code):
        from app.core.audit import record

        # No debe levantar con ningún code del spec
        record(code, {"x": 1})


# ===========================================================================
# Triangulación
# ===========================================================================


class TestAuditTriangulate:
    """Sanity checks cruzados."""

    def test_payload_with_sensitive_keys_does_not_crash(self, caplog):
        """El helper no es responsable de scrubbing; pasa cualquier payload."""
        from app.core.audit import record

        caplog.set_level(logging.INFO, logger="audit")
        # El caller es responsable de no pasar passwords — el helper no
        # los filtra (defensa en profundidad vive en el caller).
        record("LOGIN_FAIL", {"reason": "bad_password"})

        rec = next(r for r in caplog.records if r.name == "audit")
        assert rec.extra["audit.payload"]["reason"] == "bad_password"

    def test_nested_payload_preserved(self, caplog):
        """Payloads anidados se preservan en el log (no se aplanan)."""
        from app.core.audit import record

        caplog.set_level(logging.INFO, logger="audit")
        payload = {
            "user_id": "u-1",
            "details": {"ip": "127.0.0.1", "user_agent": "Mozilla/5.0"},
        }
        record("LOGIN_OK", payload)

        rec = next(r for r in caplog.records if r.name == "audit")
        assert rec.extra["audit.payload"]["details"]["ip"] == "127.0.0.1"
