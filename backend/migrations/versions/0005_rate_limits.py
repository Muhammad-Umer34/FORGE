"""Rate limits shared by every server process (D-189)

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # One row per key per fixed time window, e.g. ("signup:ip:1.2.3.4", 2026-10-20 14:00, 3)
    op.create_table(
        "rate_limits",
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("key", "window_start", name="pk_rate_limits"),
    )
    op.create_index("ix_rate_limits_window_start", "rate_limits", ["window_start"])
    op.execute("ALTER TABLE rate_limits ENABLE ROW LEVEL SECURITY")  # hidden from Supabase's REST API


def downgrade() -> None:
    op.drop_index("ix_rate_limits_window_start", table_name="rate_limits")
    op.drop_table("rate_limits")
