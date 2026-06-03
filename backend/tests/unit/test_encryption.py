"""Tests for EncryptionService — AES-256 Fernet-based encryption at rest."""

import os
import base64
from unittest.mock import patch

import pytest


class TestEncryptionServiceStructure:
    """EncryptionService SHOULD provide encrypt and decrypt methods."""

    def test_service_is_importable(self):
        """EncryptionService SHOULD be importable from app.core.encryption."""
        from app.core.encryption import EncryptionService  # noqa: PLC0415

        assert EncryptionService is not None

    def test_service_has_encrypt_method(self):
        """EncryptionService SHOULD have an 'encrypt' method."""
        from app.core.encryption import EncryptionService  # noqa: PLC0415

        assert hasattr(EncryptionService, "encrypt")
        assert callable(EncryptionService.encrypt)

    def test_service_has_decrypt_method(self):
        """EncryptionService SHOULD have a 'decrypt' method."""
        from app.core.encryption import EncryptionService  # noqa: PLC0415

        assert hasattr(EncryptionService, "decrypt")
        assert callable(EncryptionService.decrypt)


class TestEncryptionRoundTrip:
    """encrypt SHOULD produce reversible ciphertext."""

    def _make_key(self) -> str:
        """Generate a valid Fernet key for testing."""
        return base64.urlsafe_b64encode(os.urandom(32)).decode()

    def test_encrypt_decrypt_round_trip(self):
        """encrypt(plaintext) SHOULD produce ciphertext that decrypt() recovers."""
        from app.core.encryption import EncryptionService  # noqa: PLC0415

        key = self._make_key()
        svc = EncryptionService(key=key)
        plaintext = "Sensitive Data 123!@#"
        ciphertext = svc.encrypt(plaintext)
        assert ciphertext != plaintext  # Ciphertext differs from plaintext
        decrypted = svc.decrypt(ciphertext)
        assert decrypted == plaintext

    def test_encrypt_produces_different_output_each_time(self):
        """Encrypting the same plaintext twice SHOULD produce different ciphertext."""
        from app.core.encryption import EncryptionService  # noqa: PLC0415

        key = self._make_key()
        svc = EncryptionService(key=key)
        plaintext = "Same input"
        c1 = svc.encrypt(plaintext)
        c2 = svc.encrypt(plaintext)
        assert c1 != c2  # Fernet includes a random IV

    def test_encrypt_empty_string(self):
        """Encrypting an empty string SHOULD work (edge case)."""
        from app.core.encryption import EncryptionService  # noqa: PLC0415

        key = self._make_key()
        svc = EncryptionService(key=key)
        ciphertext = svc.encrypt("")
        assert svc.decrypt(ciphertext) == ""

    def test_encrypt_unicode(self):
        """Encryption SHOULD handle Unicode characters."""
        from app.core.encryption import EncryptionService  # noqa: PLC0415

        key = self._make_key()
        svc = EncryptionService(key=key)
        plaintext = "ñandú — 日本 — émoji 🎉"
        ciphertext = svc.encrypt(plaintext)
        assert svc.decrypt(ciphertext) == plaintext

    def test_encrypt_long_text(self):
        """Encryption SHOULD handle long texts (e.g., JSON serialized)."""
        from app.core.encryption import EncryptionService  # noqa: PLC0415

        key = self._make_key()
        svc = EncryptionService(key=key)
        plaintext = "x" * 10000  # 10k chars
        ciphertext = svc.encrypt(plaintext)
        assert svc.decrypt(ciphertext) == plaintext


class TestEncryptionKeyManagement:
    """EncryptionService SHOULD validate and manage its key."""

    def test_default_key_from_env(self):
        """EncryptionService SHOULD read ENCRYPTION_KEY from env by default."""
        from app.core.encryption import EncryptionService  # noqa: PLC0415

        key = self._make_key()
        with patch.dict(os.environ, {"ENCRYPTION_KEY": key}):
            svc = EncryptionService()
            plaintext = "env key test"
            ct = svc.encrypt(plaintext)
            assert svc.decrypt(ct) == plaintext

    def test_missing_key_raises_error(self):
        """EncryptionService WITHOUT env key SHOULD raise ValueError."""
        from app.core.encryption import EncryptionService  # noqa: PLC0415

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
                EncryptionService()

    def test_tampered_ciphertext_raises_error(self):
        """Tampering with ciphertext SHOULD make decryption fail."""
        from app.core.encryption import EncryptionService  # noqa: PLC0415

        key = self._make_key()
        svc = EncryptionService(key=key)
        ciphertext = svc.encrypt("secret")
        # Tamper with the ciphertext
        tampered = ciphertext[:-1] + ("X" if ciphertext[-1] != "X" else "Y")
        with pytest.raises(Exception):
            svc.decrypt(tampered)

    def _make_key(self) -> str:
        return base64.urlsafe_b64encode(os.urandom(32)).decode()
