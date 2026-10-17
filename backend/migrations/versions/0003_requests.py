"""Website requests belong to a project (ER: PROJECT receives many REQUEST) (D-179)

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

# "processing" while the agent runs; afterwards the API envelope status (backend/models/requests.py)
STATUSES = ("processing", "needs_clarification", "awaiting_confirmation", "complete", "out_of_scope",
            "failed", "cancelled")


def upgrade() -> None:
    op.create_table(
        "requests",
        # Same id as the LangGraph thread that holds the paused run (req_ + 12 hex characters)
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="processing"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN (" + ", ".join(f"'{s}'" for s in STATUSES) + ")", name="status_known"),
    )
    op.create_index("ix_requests_project_id_created_at", "requests", ["project_id", "created_at"])
    op.execute("ALTER TABLE requests ENABLE ROW LEVEL SECURITY")  # hidden from Supabase's REST API


def downgrade() -> None:
    op.drop_index("ix_requests_project_id_created_at", table_name="requests")
    op.drop_table("requests")
