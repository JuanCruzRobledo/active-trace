"""Tests unitarios para PII masking utility (C-07)."""

from __future__ import annotations

from app.core.pii import (
    mask_email,
    mask_dni,
    mask_cuil,
    mask_cbu,
    mask_alias_cbu,
)


class TestMaskEmail:
    def test_mask_short_email(self) -> None:
        assert mask_email("a@b.co") == "a***@b.co"

    def test_mask_typical_email(self) -> None:
        assert mask_email("juan.perez@example.com") == "j***@example.com"

    def test_mask_single_char_local(self) -> None:
        assert mask_email("j@dominio.com") == "j***@dominio.com"

    def test_mask_raises_on_empty(self) -> None:
        import pytest
        with pytest.raises(ValueError):
            mask_email("")


class TestMaskDni:
    def test_mask_dni_8_digits(self) -> None:
        assert mask_dni("12345678") == "*****5678"

    def test_mask_dni_7_digits(self) -> None:
        assert mask_dni("1234567") == "*****4567"

    def test_mask_dni_none(self) -> None:
        assert mask_dni(None) is None

    def test_mask_dni_empty(self) -> None:
        assert mask_dni("") == ""


class TestMaskCuil:
    def test_mask_cuil_full(self) -> None:
        assert mask_cuil("20-12345678-9") == "*****5678-9"

    def test_mask_cuil_simple(self) -> None:
        assert mask_cuil("20123456789") == "*****56789"

    def test_mask_cuil_none(self) -> None:
        assert mask_cuil(None) is None


class TestMaskCbu:
    def test_mask_cbu_full(self) -> None:
        assert mask_cbu("0000003100012345678901") == "*****8901"

    def test_mask_cbu_short(self) -> None:
        assert mask_cbu("1234") == "*****1234"

    def test_mask_cbu_none(self) -> None:
        assert mask_cbu(None) is None


class TestMaskAliasCbu:
    def test_mask_alias_short(self) -> None:
        assert mask_alias_cbu("ab") == "a***"

    def test_mask_alias_long(self) -> None:
        assert mask_alias_cbu("juan.banco") == "j***"

    def test_mask_alias_none(self) -> None:
        assert mask_alias_cbu(None) is None
