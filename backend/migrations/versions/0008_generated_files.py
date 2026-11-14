"""Files of generated sites, kept outside the run's saved state (D-234)

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-14
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generated_files",
        sa.Column("request_id", sa.String(32), sa.ForeignKey("requests.id", ondelete="CASCADE",
                                                             name="fk_generated_files_request_id_requests"),
                  nullable=False),
        sa.Column("path", sa.String(300), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("written_by", sa.String(10), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("request_id", "path", name="pk_generated_files"),
        sa.CheckConstraint("written_by IN ('code', 'model')", name="ck_generated_files_written_by_known"),
    )


def downgrade() -> None:
    op.drop_table("generated_files")
