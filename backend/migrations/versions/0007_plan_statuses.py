"""A request can wait for plan approval, and can end with an approved plan (D-204)

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-04
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

OLD = ("processing", "needs_clarification", "awaiting_confirmation", "complete", "out_of_scope", "failed", "cancelled",
       "paused")
NEW = OLD + ("awaiting_plan_approval", "planned")


def _check(statuses) -> None:
    op.execute("ALTER TABLE requests DROP CONSTRAINT ck_requests_status_known")
    allowed = ", ".join(f"'{s}'" for s in statuses)
    op.execute(f"ALTER TABLE requests ADD CONSTRAINT ck_requests_status_known CHECK (status IN ({allowed}))")


def upgrade() -> None:
    _check(NEW)


def downgrade() -> None:
    # older code has no plan step, so these requests cannot be continued there
    op.execute("UPDATE requests SET status = 'cancelled' WHERE status IN ('awaiting_plan_approval', 'planned')")
    _check(OLD)
