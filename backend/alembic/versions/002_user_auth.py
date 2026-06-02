"""002 — Create users, refresh_token, password_reset_token, two_factor_challenge tables

Revision ID: 002
Revises: 001
Create Date: 2026-06-02

C-03 auth-jwt-2fa: sienta las bases de identidad (User), sesión
(refresh_token con rotación y reuso-detection) y los flujos de
recuperación de contraseña y 2FA TOTP.

Nota: la tabla de usuarios se llama ``users`` (no ``user``) porque
``user`` es palabra reservada de PostgreSQL y producía corrupción de
catálogo en Postgres 18 con quoted identifiers. El nombre ``users`` es
la convención estándar de la industria.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users, refresh_token, password_reset_token, two_factor_challenge."""
    # ── users ─────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("totp_secret", sa.Text(), nullable=True),
        sa.Column(
            "totp_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    # ── refresh_token ─────────────────────────────────────────────────────
    op.create_table(
        "refresh_token",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "replaced_by_id",
            UUID(as_uuid=True),
            sa.ForeignKey("refresh_token.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_ip", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("token_hash", name="uq_refresh_token_token_hash"),
    )
    op.create_index("ix_refresh_token_tenant_id", "refresh_token", ["tenant_id"])
    op.create_index("ix_refresh_token_user_id", "refresh_token", ["user_id"])

    # ── password_reset_token ──────────────────────────────────────────────
    # Efímero: no tiene soft delete (deleted_at).
    op.create_table(
        "password_reset_token",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "token_hash", name="uq_password_reset_token_token_hash"
        ),
    )
    op.create_index(
        "ix_password_reset_token_tenant_id",
        "password_reset_token",
        ["tenant_id"],
    )
    op.create_index(
        "ix_password_reset_token_user_id",
        "password_reset_token",
        ["user_id"],
    )

    # ── two_factor_challenge ──────────────────────────────────────────────
    # Efímero: no tiene soft delete (deleted_at).
    op.create_table(
        "two_factor_challenge",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "token_hash", name="uq_two_factor_challenge_token_hash"
        ),
    )
    op.create_index(
        "ix_two_factor_challenge_tenant_id",
        "two_factor_challenge",
        ["tenant_id"],
    )
    op.create_index(
        "ix_two_factor_challenge_user_id",
        "two_factor_challenge",
        ["user_id"],
    )


def downgrade() -> None:
    """Drop the four auth tables in reverse order."""
    op.drop_index(
        "ix_two_factor_challenge_user_id", table_name="two_factor_challenge"
    )
    op.drop_index(
        "ix_two_factor_challenge_tenant_id", table_name="two_factor_challenge"
    )
    op.drop_table("two_factor_challenge")

    op.drop_index(
        "ix_password_reset_token_user_id", table_name="password_reset_token"
    )
    op.drop_index(
        "ix_password_reset_token_tenant_id", table_name="password_reset_token"
    )
    op.drop_table("password_reset_token")

    op.drop_index("ix_refresh_token_user_id", table_name="refresh_token")
    op.drop_index("ix_refresh_token_tenant_id", table_name="refresh_token")
    op.drop_table("refresh_token")

    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_table("users")
