"""Tests for EncryptedColumn — transparent AES-256 encrypted column type."""




class TestEncryptedColumnType:
    """EncryptedColumn SHOULD transparently encrypt/decrypt values."""

    def test_encrypted_column_importable(self):
        """EncryptedColumn SHOULD be importable from app.core.encryption."""
        from app.core.encryption import EncryptedColumn  # noqa: PLC0415

        assert EncryptedColumn is not None

    def test_encrypted_column_is_type_decorator(self):
        """EncryptedColumn SHOULD subclass TypeDecorator."""
        from app.core.encryption import EncryptedColumn  # noqa: PLC0415
        from sqlalchemy.types import TypeDecorator  # noqa: PLC0415

        assert issubclass(EncryptedColumn, TypeDecorator)

    def test_encrypted_column_stores_text(self):
        """EncryptedColumn SHOULD have impl=Text (stores ciphertext)."""
        from app.core.encryption import EncryptedColumn  # noqa: PLC0415
        from sqlalchemy import Text  # noqa: PLC0415

        ec = EncryptedColumn(key="test_key_32_chars_long_placeholder")
        assert isinstance(ec.impl, Text)

    def test_process_bind_param_encrypts(self):
        """process_bind_param SHOULD return encrypted string."""
        from app.core.encryption import EncryptedColumn  # noqa: PLC0415

        ec = EncryptedColumn(key="test_key_32_chars_long_placeholder")
        result = ec.process_bind_param("secret", dialect=None)
        assert result is not None
        assert result != "secret"
        assert isinstance(result, str)

    def test_process_result_value_decrypts(self):
        """process_result_value SHOULD return decrypted original."""
        from app.core.encryption import EncryptedColumn  # noqa: PLC0415

        ec = EncryptedColumn(key="test_key_32_chars_long_placeholder")
        plaintext = "my_secret_value"
        encrypted = ec.process_bind_param(plaintext, dialect=None)
        decrypted = ec.process_result_value(encrypted, dialect=None)
        assert decrypted == plaintext

    def test_none_values_passthrough(self):
        """None values SHOULD pass through without encryption."""
        from app.core.encryption import EncryptedColumn  # noqa: PLC0415

        ec = EncryptedColumn(key="test_key_32_chars_long_placeholder")
        assert ec.process_bind_param(None, dialect=None) is None
        assert ec.process_result_value(None, dialect=None) is None
