"""Each site's storage: its schema, role, data contract and the hashes of its keys (D-243, D-247)

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-24
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_storage",
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE",
                                                                  name="fk_site_storage_project_id_projects"),
                  nullable=False),
        sa.Column("schema_name", sa.String(63), nullable=False),
        sa.Column("role_name", sa.String(63), nullable=False),
        sa.Column("contract", JSONB(), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=True),
        sa.Column("preview_key_hash", sa.String(64), nullable=True),
        sa.Column("request_id", sa.String(32), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("project_id", name="pk_site_storage"),
    )
    op.create_index("ix_site_storage_key_hash", "site_storage", ["key_hash"], unique=True)
    op.create_index("ix_site_storage_preview_key_hash", "site_storage", ["preview_key_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("site_storage")
