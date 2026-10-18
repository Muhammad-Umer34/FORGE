"""Email verification and password reset (D-185, D-186)

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True)))
    # Accounts made before verification existed keep working: they count as verified.
    op.execute("UPDATE users SET email_verified_at = created_at")

    op.create_table(
        "auth_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False),
        # SHA-256 of the random token sent by email; the token itself is never stored
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("purpose IN ('verify_email', 'reset_password')", name="purpose_known"),
    )
    op.create_index("ix_auth_tokens_user_purpose_created", "auth_tokens", ["user_id", "purpose", "created_at"])
    op.execute("ALTER TABLE auth_tokens ENABLE ROW LEVEL SECURITY")  # hidden from Supabase's REST API


def downgrade() -> None:
    op.drop_index("ix_auth_tokens_user_purpose_created", table_name="auth_tokens")
    op.drop_table("auth_tokens")
    op.drop_column("users", "email_verified_at")
