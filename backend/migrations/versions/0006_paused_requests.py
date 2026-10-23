"""A request can be paused: it stopped mid-way and can be continued (persistence plan)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-22
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

OLD = ("processing", "needs_clarification", "awaiting_confirmation", "complete", "out_of_scope", "failed", "cancelled")
NEW = OLD + ("paused",)


def _check(statuses) -> None:
    op.execute("ALTER TABLE requests DROP CONSTRAINT ck_requests_status_known")
    allowed = ", ".join(f"'{s}'" for s in statuses)
    op.execute(f"ALTER TABLE requests ADD CONSTRAINT ck_requests_status_known CHECK (status IN ({allowed}))")


def upgrade() -> None:
    _check(NEW)


def downgrade() -> None:
    op.execute("UPDATE requests SET status = 'failed' WHERE status = 'paused'")   # older code cannot resume them
    _check(OLD)
