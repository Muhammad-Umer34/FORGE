# D:\FYP\FORGE-1\agents\database_generator\provision.py
"""
A site's own storage (D-243): the schema "site_<project>" in FORGE's database and a role "site_<project>_role"
(NOLOGIN) that may use only that schema. FORGE's backend runs every query of a site inside
`SET LOCAL ROLE site_<project>_role`, so a bug cannot read another site's data.

Rebuilds recreate the schema. A schema holding real (non-sample) rows is never dropped: it is renamed
site_<project>_old_<time> and kept.
shortcut: no migrations between plan versions yet; add them when sites are published with live data (FYP-2).
"""
import hashlib
import re
import secrets
import uuid
from datetime import datetime, timezone

import psycopg
from psycopg.types.json import Jsonb

from agents.database_generator.compile import compile_schema, ident, literal
from agents.database_generator.seed import seed_sql
from agents.state import DataEntity


def plain_url(url: str) -> str:
    """psycopg wants postgresql://; the app's URLs may name the asyncpg driver."""
    return re.sub(r"^postgres(ql)?(\+\w+)?://", "postgresql://", url)


def connect(url: str):
    # No server-side prepared statements: FORGE's database sits behind Supabase's transaction pooler.
    return psycopg.connect(plain_url(url), connect_timeout=15, prepare_threshold=None)


def schema_for(project_id: str) -> str:
    """'site_' + 12 hex characters of the project id (any other id, e.g. in tests, is hashed to the same form)."""
    try:
        key = uuid.UUID(str(project_id))
    except ValueError:
        key = uuid.uuid5(uuid.NAMESPACE_URL, f"forge-project/{project_id}")
    return "site_" + key.hex[:12]


def role_for(schema: str) -> str:
    return f"{schema}_role"


def _real_rows(conn, schema: str) -> int:
    tables = conn.execute("SELECT table_name FROM information_schema.columns WHERE table_schema = %s "
                          "AND column_name = 'is_sample'", (schema,)).fetchall()
    return sum(conn.execute(f"SELECT count(*) FROM {ident(schema)}.{ident(t)} WHERE NOT is_sample").fetchone()[0]
               for (t,) in tables)


def provision(entities: list[DataEntity], url: str, project_id: str, tz: str = "Asia/Karachi") -> dict:
    """Create (or recreate) the site's schema with its tables, rules and sample rows, in one transaction."""
    schema = schema_for(project_id)
    role = role_for(schema)
    kept = None
    with connect(url) as conn:
        gist = bool(conn.execute("SELECT 1 FROM pg_available_extensions WHERE name = 'btree_gist'").fetchone())
        compiled = compile_schema(entities, schema, tz, gist=gist)
        with conn.transaction():
            conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (schema,))   # one rebuild at a time
            if conn.execute("SELECT 1 FROM pg_namespace WHERE nspname = %s", (schema,)).fetchone():
                if _real_rows(conn, schema):
                    kept = f"{schema}_old_{datetime.now(timezone.utc):%Y%m%d%H%M%S}"
                    conn.execute(f"ALTER SCHEMA {ident(schema)} RENAME TO {ident(kept)}")
                else:
                    conn.execute(f"DROP SCHEMA {ident(schema)} CASCADE")
            conn.execute(compiled.schema_sql)
            conn.execute(seed_sql(entities, schema, tz))
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone():
                conn.execute(f"CREATE ROLE {ident(role)} NOLOGIN")
            conn.execute(f"GRANT {ident(role)} TO current_user")             # so FORGE can SET LOCAL ROLE to it
            conn.execute(f"GRANT USAGE ON SCHEMA {ident(schema)} TO {ident(role)}")
            conn.execute(f"GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA {ident(schema)} TO {ident(role)}")
            for e in entities:                           # the owner may remove rows of their own lists (D-249)
                if e.role in ("catalogue", "setting"):
                    conn.execute(f"GRANT DELETE ON {ident(schema)}.{ident(e.name)} TO {ident(role)}")
            conn.execute(f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {ident(schema)} TO {ident(role)}")
            conn.execute(f"COMMENT ON SCHEMA {ident(schema)} IS {literal('FORGE site storage for project ' + str(project_id))}")
    return {"schema": schema, "role": role, "kept_old_schema": kept, "files": compiled.files(),
            "contract": compiled.schema_json,
            "seed": seed_sql(entities, schema, tz), "rules": compiled.rules}


def new_key() -> tuple[str, str]:
    """(key, its SHA-256): the key goes to the site's server only; FORGE keeps the hash (D-247)."""
    key = "fsk_" + secrets.token_urlsafe(32)
    return key, hashlib.sha256(key.encode()).hexdigest()


def register(app_url: str, project_id: str, made: dict, request_id: str) -> str | None:
    """Record the site's storage in FORGE's own database and return a fresh preview key, or None when the project
    is not a real one (tests, evaluations)."""
    try:
        project = uuid.UUID(str(project_id))
    except ValueError:
        return None
    key, digest = new_key()
    with connect(app_url) as conn, conn.transaction():
        if not conn.execute("SELECT 1 FROM projects WHERE id = %s", (project,)).fetchone():
            return None
        conn.execute(
            "INSERT INTO site_storage (project_id, schema_name, role_name, contract, preview_key_hash, request_id) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (project_id) DO UPDATE SET schema_name = EXCLUDED.schema_name, "
            "role_name = EXCLUDED.role_name, contract = EXCLUDED.contract, preview_key_hash = EXCLUDED.preview_key_hash, "
            "request_id = EXCLUDED.request_id, updated_at = now()",
            (project, made["schema"], made["role"], Jsonb(made["contract"]), digest, request_id[:32]))
    return key


def new_preview_key(app_url: str, project_id: str) -> str | None:
    """A fresh preview key for a project that has storage (reopening a project starts a new preview)."""
    key, digest = new_key()
    with connect(app_url) as conn, conn.transaction():
        done = conn.execute("UPDATE site_storage SET preview_key_hash = %s, updated_at = now() WHERE project_id = %s",
                            (digest, uuid.UUID(str(project_id)))).rowcount
    return key if done else None


def drop(url: str, project_id: str) -> None:
    """Remove a site's storage when its project is deleted (renamed old copies stay for the owner)."""
    schema = schema_for(project_id)
    with connect(url) as conn, conn.transaction():
        conn.execute(f"DROP SCHEMA IF EXISTS {ident(schema)} CASCADE")
        if not conn.execute("SELECT 1 FROM pg_namespace WHERE nspname LIKE %s", (f"{schema}_old_%",)).fetchone():
            conn.execute(f"DROP ROLE IF EXISTS {ident(role_for(schema))}")
