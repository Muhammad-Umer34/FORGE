"""Users and projects, with the 3-projects-per-user limit (D-172, D-174, D-175)

Revision ID: 0001
Revises:
Create Date: 2026-10-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Copied, not imported: a migration is a frozen snapshot. Must equal MAX_PROJECTS_PER_USER in
# backend/services/projects.py (a test checks that they agree).
PROJECT_LIMIT = 3

# Safety net under the API (D-175). A CHECK constraint cannot count rows of a table, so a trigger
# does it. It takes the same row lock on the owner as the API does, so two inserts for one user
# can never both see "2 projects" and both pass. Under REPEATABLE READ the count would come from an
# older snapshot and could miss a project that was just committed, so that level is refused
# (SERIALIZABLE is safe: PostgreSQL itself aborts one of two conflicting transactions).
LIMIT_TRIGGER_FUNCTION = f"""
CREATE FUNCTION forge_enforce_project_limit() RETURNS trigger
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
    existing integer;
BEGIN
    IF current_setting('transaction_isolation') = 'repeatable read' THEN
        RAISE EXCEPTION 'project creation needs READ COMMITTED or SERIALIZABLE isolation'
            USING ERRCODE = 'FG002';
    END IF;

    PERFORM 1 FROM users WHERE id = NEW.owner_id FOR UPDATE;
    IF NOT FOUND THEN
        RETURN NEW;  -- the foreign key rejects the row
    END IF;

    SELECT count(*) INTO existing FROM projects WHERE owner_id = NEW.owner_id AND id <> NEW.id;
    IF existing >= {PROJECT_LIMIT} THEN
        RAISE EXCEPTION 'user % already has % projects', NEW.owner_id, existing
            USING ERRCODE = 'FG001', HINT = 'project_limit_reached';
    END IF;
    RETURN NEW;
END;
$$;
"""


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.String(80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("failed_logins", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("email = btrim(email) AND position('@' in email) > 1", name="email_shape"),
        sa.CheckConstraint("char_length(btrim(display_name)) > 0", name="display_name_not_blank"),
        sa.CheckConstraint("failed_logins >= 0", name="failed_logins_not_negative"),
    )
    op.create_index("uq_users_email_lower", "users", [sa.text("lower(email)")], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("char_length(btrim(name)) between 1 and 60", name="name_length"),
        sa.CheckConstraint("description IS NULL OR char_length(description) <= 500", name="description_length"),
    )
    # One name per owner, ignoring case. Also serves "list my projects" lookups by owner_id.
    op.create_index("uq_projects_owner_name_lower", "projects", ["owner_id", sa.text("lower(name)")], unique=True)

    op.execute(LIMIT_TRIGGER_FUNCTION)
    op.execute(
        "CREATE TRIGGER projects_limit_per_user BEFORE INSERT OR UPDATE OF owner_id ON projects "
        "FOR EACH ROW EXECUTE FUNCTION forge_enforce_project_limit()"
    )

    # Supabase publishes the public schema through its REST API. FORGE talks to the database only
    # from its own backend (the table owner, which bypasses RLS), so with RLS on and no policies
    # nobody can read users or projects through that API.
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE projects ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE alembic_version ENABLE ROW LEVEL SECURITY")  # Alembic's own bookkeeping table


def downgrade() -> None:
    op.execute("ALTER TABLE alembic_version DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TRIGGER IF EXISTS projects_limit_per_user ON projects")
    op.execute("DROP FUNCTION IF EXISTS forge_enforce_project_limit()")
    op.drop_index("uq_projects_owner_name_lower", table_name="projects")
    op.drop_table("projects")
    op.drop_index("uq_users_email_lower", table_name="users")
    op.drop_table("users")
