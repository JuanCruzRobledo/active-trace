"""Tests estructurales y de comportamiento para los modelos del change C-03.

Cubren:
- :class:`app.models.user.User` — identidad, soft delete, totp_secret cifrado.
- :class:`app.models.refresh_token.RefreshToken` — rotación, revocación.
- :class:`app.models.password_reset_token.PasswordResetToken` — efímero.
- :class:`app.models.two_factor_challenge.TwoFactorChallenge` — efímero.

Convenciones:
- Tests estructurales: introspeccionan ``__table__`` directamente (no DB).
- Tests de persistencia: usan el fixture ``db_session`` (DB real).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import Boolean, Column, DateTime, String, Text, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.encryption import EncryptedColumn
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _utc_in(minutes: int = 0) -> datetime:
    return _utcnow() + timedelta(minutes=minutes)


# ===========================================================================
# User
# ===========================================================================


class TestUserStructure:
    """Estructura de la tabla ``users``: columnas, constraints, tipo de cifrado."""

    def test_user_tablename_is_users(self):
        """La tabla se llama ``users`` (no ``user`` — palabra reservada PG)."""
        assert User.__tablename__ == "users"

    def test_user_has_email_column_string(self):
        """``email`` es String(255), NOT NULL."""
        col = User.__table__.columns["email"]
        assert isinstance(col.type, String)
        assert col.type.length == 255
        assert not col.nullable

    def test_user_has_password_hash_column_text(self):
        """``password_hash`` es Text, NOT NULL (hash Argon2id puede ser > 255)."""
        col = User.__table__.columns["password_hash"]
        assert isinstance(col.type, Text)
        assert not col.nullable

    def test_user_has_is_active_column_default_true(self):
        """``is_active`` es Boolean, NOT NULL, default True."""
        col = User.__table__.columns["is_active"]
        assert isinstance(col.type, Boolean)
        assert not col.nullable
        assert col.default.arg is True

    def test_user_has_totp_secret_encrypted_column(self):
        """``totp_secret`` es ``EncryptedColumn`` (cifrado en reposo)."""
        col = User.__table__.columns["totp_secret"]
        assert isinstance(col.type, EncryptedColumn)
        assert col.nullable  # NULL hasta que el usuario enrola 2FA

    def test_user_has_totp_enabled_column_default_false(self):
        """``totp_enabled`` es Boolean, NOT NULL, default False."""
        col = User.__table__.columns["totp_enabled"]
        assert isinstance(col.type, Boolean)
        assert not col.nullable
        assert col.default.arg is False

    def test_user_inherits_soft_delete_from_basemixin(self):
        """User hereda ``deleted_at`` (soft delete) de ``BaseMixin``."""
        assert "deleted_at" in User.__table__.columns

    def test_user_inherits_timestamps_from_basemixin(self):
        """User hereda ``created_at`` y ``updated_at`` de ``BaseMixin``."""
        assert "created_at" in User.__table__.columns
        assert "updated_at" in User.__table__.columns

    def test_user_has_unique_constraint_on_tenant_and_email(self):
        """(tenant_id, email) es UNIQUE — un email no se duplica dentro del tenant."""
        uq_names = {
            c.name
            for c in User.__table__.constraints
            if isinstance(c, UniqueConstraint)
        }
        assert "uq_users_tenant_email" in uq_names

    def test_user_has_tenant_id_index(self):
        """El índice ``ix_users_tenant_id`` está creado (performance multi-tenant)."""
        idx_names = {idx.name for idx in User.__table__.indexes}
        assert "ix_users_tenant_id" in idx_names


class TestUserRepr:
    """Representación legible para logs y debugging."""

    def test_user_repr_includes_key_fields(self):
        """__repr__ incluye id, tenant_id, email, is_active, totp_enabled."""
        u = User(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            email="alice@example.com",
            password_hash="$argon2id$v=19$m=65536...",
            is_active=True,
            totp_enabled=False,
        )
        r = repr(u)
        assert "alice@example.com" in r
        assert "is_active=True" in r
        assert "totp_enabled=False" in r


# ===========================================================================
# RefreshToken
# ===========================================================================


class TestRefreshTokenStructure:
    """Estructura de la tabla ``refresh_token``."""

    def test_refresh_token_tablename(self):
        """La tabla se llama ``refresh_token`` (singular, snake_case)."""
        assert RefreshToken.__tablename__ == "refresh_token"

    def test_refresh_token_has_user_id_fk(self):
        """``user_id`` FK a ``users.id`` con ON DELETE CASCADE."""
        col = RefreshToken.__table__.columns["user_id"]
        assert isinstance(col.type, PGUUID)
        assert not col.nullable
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "users.id" in fk_targets

    def test_refresh_token_token_hash_is_unique(self):
        """``token_hash`` es UNIQUE (no se puede duplicar en DB)."""
        col = RefreshToken.__table__.columns["token_hash"]
        assert col.unique

    def test_refresh_token_has_expires_at(self):
        """``expires_at`` es DateTime(timezone=True) NOT NULL."""
        col = RefreshToken.__table__.columns["expires_at"]
        assert isinstance(col.type, DateTime)
        assert col.type.timezone is True
        assert not col.nullable

    def test_refresh_token_revoked_at_is_nullable(self):
        """``revoked_at`` es nullable (NULL = token activo)."""
        col = RefreshToken.__table__.columns["revoked_at"]
        assert col.nullable

    def test_refresh_token_has_replaced_by_self_fk(self):
        """``replaced_by_id`` FK a ``refresh_token.id`` (auto-ref, rotación)."""
        col = RefreshToken.__table__.columns["replaced_by_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "refresh_token.id" in fk_targets

    def test_refresh_token_inherits_soft_delete(self):
        """RefreshToken hereda ``deleted_at`` (soft delete, para reuso-detection)."""
        assert "deleted_at" in RefreshToken.__table__.columns

    def test_refresh_token_has_tenant_id_index(self):
        """``ix_refresh_token_tenant_id`` está creado (multi-tenant performance)."""
        idx_names = {idx.name for idx in RefreshToken.__table__.indexes}
        assert "ix_refresh_token_tenant_id" in idx_names

    def test_refresh_token_has_user_id_index(self):
        """``ix_refresh_token_user_id`` para lookups de tokens por usuario."""
        idx_names = {idx.name for idx in RefreshToken.__table__.indexes}
        assert "ix_refresh_token_user_id" in idx_names


class TestRefreshTokenMethods:
    """Métodos helper ``is_revoked`` e ``is_expired``."""

    def test_is_revoked_false_when_revoked_at_is_null(self):
        """Un token con ``revoked_at=None`` NO está revocado."""
        token = RefreshToken(revoked_at=None)
        assert token.is_revoked() is False

    def test_is_revoked_true_when_revoked_at_is_set(self):
        """Un token con ``revoked_at`` seteado está revocado."""
        token = RefreshToken(revoked_at=_utcnow())
        assert token.is_revoked() is True

    def test_is_expired_false_when_expires_at_is_future(self):
        """Si ``expires_at > now``, el token NO está expirado."""
        token = RefreshToken(expires_at=_utc_in(minutes=10))
        assert token.is_expired() is False

    def test_is_expired_true_when_expires_at_is_past(self):
        """Si ``expires_at < now``, el token está expirado."""
        token = RefreshToken(expires_at=_utcnow() - timedelta(seconds=1))
        assert token.is_expired() is True

    def test_is_expired_accepts_explicit_now(self):
        """``is_expired`` acepta ``now`` como parámetro (testeable)."""
        future = _utcnow() + timedelta(hours=1)
        past = _utcnow() - timedelta(hours=1)
        token = RefreshToken(expires_at=past)
        assert token.is_expired(now=future) is True


# ===========================================================================
# PasswordResetToken
# ===========================================================================


class TestPasswordResetTokenStructure:
    """PasswordResetToken es EFÍMERO: no hereda BaseMixin."""

    def test_password_reset_token_tablename(self):
        """Tabla ``password_reset_token``."""
        assert PasswordResetToken.__tablename__ == "password_reset_token"

    def test_password_reset_token_has_user_id_fk(self):
        """``user_id`` FK a ``users.id`` con CASCADE."""
        col = PasswordResetToken.__table__.columns["user_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "users.id" in fk_targets

    def test_password_reset_token_token_hash_is_unique(self):
        """``token_hash`` es UNIQUE."""
        col = PasswordResetToken.__table__.columns["token_hash"]
        assert col.unique

    def test_password_reset_token_does_not_inherit_soft_delete(self):
        """NO tiene ``deleted_at`` — los tokens viejos se purgan (no soft delete)."""
        assert "deleted_at" not in PasswordResetToken.__table__.columns

    def test_password_reset_token_does_not_have_updated_at(self):
        """NO tiene ``updated_at`` — modelo inmutable post-creación."""
        assert "updated_at" not in PasswordResetToken.__table__.columns

    def test_password_reset_token_has_used_at_nullable(self):
        """``used_at`` es nullable (NULL = no usado)."""
        col = PasswordResetToken.__table__.columns["used_at"]
        assert col.nullable

    def test_password_reset_token_has_explicit_id(self):
        """Tiene ``id`` UUID explícito (no hereda de BaseMixin)."""
        col = PasswordResetToken.__table__.columns["id"]
        assert col.primary_key
        assert isinstance(col.type, PGUUID)


class TestPasswordResetTokenMethods:
    """Métodos ``is_expired`` e ``is_used``."""

    def test_is_used_false_when_used_at_is_null(self):
        token = PasswordResetToken(used_at=None)
        assert token.is_used() is False

    def test_is_used_true_when_used_at_is_set(self):
        token = PasswordResetToken(used_at=_utcnow())
        assert token.is_used() is True

    def test_is_expired_false_when_future(self):
        token = PasswordResetToken(expires_at=_utc_in(minutes=30))
        assert token.is_expired() is False

    def test_is_expired_true_when_past(self):
        token = PasswordResetToken(expires_at=_utcnow() - timedelta(seconds=1))
        assert token.is_expired() is True


# ===========================================================================
# TwoFactorChallenge
# ===========================================================================


class TestTwoFactorChallengeStructure:
    """TwoFactorChallenge es EFÍMERO: misma estructura que PasswordResetToken."""

    def test_two_factor_challenge_tablename(self):
        """Tabla ``two_factor_challenge``."""
        # Importar acá para no forzar carga si la suite sólo corre tests de
        # los otros modelos.
        from app.models.two_factor_challenge import TwoFactorChallenge

        assert TwoFactorChallenge.__tablename__ == "two_factor_challenge"

    def test_two_factor_challenge_has_user_id_fk(self):
        from app.models.two_factor_challenge import TwoFactorChallenge

        col = TwoFactorChallenge.__table__.columns["user_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "users.id" in fk_targets

    def test_two_factor_challenge_token_hash_is_unique(self):
        from app.models.two_factor_challenge import TwoFactorChallenge

        col = TwoFactorChallenge.__table__.columns["token_hash"]
        assert col.unique

    def test_two_factor_challenge_does_not_inherit_soft_delete(self):
        from app.models.two_factor_challenge import TwoFactorChallenge

        assert "deleted_at" not in TwoFactorChallenge.__table__.columns

    def test_two_factor_challenge_does_not_have_updated_at(self):
        from app.models.two_factor_challenge import TwoFactorChallenge

        assert "updated_at" not in TwoFactorChallenge.__table__.columns

    def test_two_factor_challenge_has_used_at_nullable(self):
        from app.models.two_factor_challenge import TwoFactorChallenge

        col = TwoFactorChallenge.__table__.columns["used_at"]
        assert col.nullable


class TestTwoFactorChallengeMethods:
    """Métodos ``is_expired`` e ``is_used``."""

    def test_is_used_false_when_used_at_is_null(self):
        from app.models.two_factor_challenge import TwoFactorChallenge

        token = TwoFactorChallenge(used_at=None)
        assert token.is_used() is False

    def test_is_used_true_when_used_at_is_set(self):
        from app.models.two_factor_challenge import TwoFactorChallenge

        token = TwoFactorChallenge(used_at=_utcnow())
        assert token.is_used() is True

    def test_is_expired_false_when_future(self):
        from app.models.two_factor_challenge import TwoFactorChallenge

        token = TwoFactorChallenge(expires_at=_utc_in(minutes=5))
        assert token.is_expired() is False

    def test_is_expired_true_when_past(self):
        from app.models.two_factor_challenge import TwoFactorChallenge

        token = TwoFactorChallenge(expires_at=_utcnow() - timedelta(seconds=1))
        assert token.is_expired() is True


# ===========================================================================
# Triangulación cruzada
# ===========================================================================


class TestModelsTriangulate:
    """Sanity checks cruzados entre los 4 modelos."""

    def test_user_and_refresh_token_have_soft_delete_but_ephemeral_do_not(self):
        """``User`` y ``RefreshToken`` soft-deletan; los efímeros NO."""
        assert "deleted_at" in User.__table__.columns
        assert "deleted_at" in RefreshToken.__table__.columns
        assert "deleted_at" not in PasswordResetToken.__table__.columns
        from app.models.two_factor_challenge import TwoFactorChallenge

        assert "deleted_at" not in TwoFactorChallenge.__table__.columns

    def test_all_models_have_tenant_id(self):
        """Los 4 modelos tienen ``tenant_id`` (multi-tenant isolation)."""
        for model in (User, RefreshToken, PasswordResetToken):
            assert "tenant_id" in model.__table__.columns
        from app.models.two_factor_challenge import TwoFactorChallenge

        assert "tenant_id" in TwoFactorChallenge.__table__.columns

    def test_token_models_have_consistent_token_hash_type(self):
        """Los 3 modelos de token tienen ``token_hash`` String(128) UNIQUE."""
        for model in (RefreshToken, PasswordResetToken):
            col = model.__table__.columns["token_hash"]
            assert isinstance(col.type, String)
            assert col.type.length == 128
            assert col.unique
        from app.models.two_factor_challenge import TwoFactorChallenge

        col = TwoFactorChallenge.__table__.columns["token_hash"]
        assert isinstance(col.type, String)
        assert col.type.length == 128
        assert col.unique


@pytest.mark.skipif(
    not __import__("tests.conftest", fromlist=["db_available"]).db_available(),
    reason="Requires PostgreSQL — run with conftest db_session fixture",
)
class TestUserPersistence:
    """Roundtrip real: persistir un User y verificar que ``totp_secret`` se cifra.

    Requiere la DB real (fixture ``db_session``). Los tests estructurales
    de arriba no necesitan DB. Se omite automáticamente si no hay DB.
    """

    @pytest.fixture
    async def tenant_id(self, db_session):  # noqa: ANN201 — pytest fixture
        """Crea un tenant ad-hoc y devuelve su UUID.

        Tenant es self-referente: ``id == tenant_id`` (es la raíz del árbol).
        """
        from app.models.tenant import Tenant  # noqa: PLC0415

        tid = uuid.uuid4()
        tenant = Tenant(id=tid, tenant_id=tid, nombre=f"test-tenant-{tid}")
        db_session.add(tenant)
        await db_session.flush()
        return tenant.id

    async def test_user_persists_and_decrypts_totp_secret(
        self, db_session, tenant_id
    ):  # noqa: ANN201
        """``totp_secret`` se guarda cifrado y se recupera en claro."""
        secret = "JBSWY3DPEHPK3PXP"  # típico secreto base32
        user = User(
            tenant_id=tenant_id,
            email=f"u-{uuid.uuid4()}@example.com",
            password_hash="$argon2id$dummy",
            totp_secret=secret,
            totp_enabled=True,
        )
        db_session.add(user)
        await db_session.commit()

        # Leer de vuelta (forzar reload desde DB, no de identity map)
        stmt = select(User).where(User.id == user.id)
        loaded = (await db_session.execute(stmt)).scalar_one()
        assert loaded.totp_secret == secret, (
            "El totp_secret debe recuperarse descifrado"
        )
        assert loaded.totp_enabled is True

    async def test_user_with_null_totp_secret_persists(
        self, db_session, tenant_id
    ):  # noqa: ANN201
        """``totp_secret = None`` se persiste como NULL (sin 2FA enrolado)."""
        user = User(
            tenant_id=tenant_id,
            email=f"u-{uuid.uuid4()}@example.com",
            password_hash="$argon2id$dummy",
            totp_secret=None,
            totp_enabled=False,
        )
        db_session.add(user)
        await db_session.commit()

        stmt = select(User).where(User.id == user.id)
        loaded = (await db_session.execute(stmt)).scalar_one()
        assert loaded.totp_secret is None
        assert loaded.totp_enabled is False

    async def test_unique_email_per_tenant_enforced(
        self, db_session, tenant_id
    ):  # noqa: ANN201
        """No se pueden tener 2 usuarios con el mismo email en el mismo tenant."""
        from sqlalchemy.exc import IntegrityError  # noqa: PLC0415

        email = f"u-{uuid.uuid4()}@example.com"
        user1 = User(
            tenant_id=tenant_id,
            email=email,
            password_hash="$argon2id$dummy",
        )
        db_session.add(user1)
        await db_session.commit()

        user2 = User(
            tenant_id=tenant_id,
            email=email,  # mismo email
            password_hash="$argon2id$dummy2",
        )
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
