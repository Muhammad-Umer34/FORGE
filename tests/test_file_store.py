"""Generated files are kept outside the run's state, and writing them twice is safe (D-234, P13)."""
import asyncio
import uuid

import pytest

from agents.file_store import MemoryFileStore, sha256
from pg_support import migrate_test_database, new_engine, requires_db

FILES = {"app/page.tsx": "export default function P() { return null }\n", "app/layout.tsx": "layout\n"}


def test_memory_store_writes_a_file_once_and_returns_its_manifest():
    store = MemoryFileStore()
    refs = store.put("r1", FILES, "code")
    assert [(r.path, r.sha256, r.written_by) for r in refs] == [(p, sha256(c), "code") for p, c in FILES.items()]
    store.put("r1", FILES, "code")                       # a repeated step after a crash
    assert store.writes == 2                                         # nothing written the second time
    store.put("r1", {"app/page.tsx": "changed\n"}, "model")
    assert store.writes == 3 and store.read("r1")["app/page.tsx"] == "changed\n"
    assert store.read("other") == {}


@requires_db
def test_postgres_store_upserts_by_request_and_path():
    from sqlalchemy import text

    from backend.core.config import settings
    from backend.services.generated_files import PostgresFileStore

    migrate_test_database()
    rid, email = f"req_test_{uuid.uuid4().hex[:8]}", f"{uuid.uuid4().hex[:8]}@example.com"

    async def rows(sql, **values):
        engine = new_engine()
        try:
            async with engine.begin() as conn:
                return (await conn.execute(text(sql), values)).scalar()
        finally:
            await engine.dispose()

    owner = asyncio.run(rows("INSERT INTO users (email, password_hash, display_name) VALUES (:e, 'x', 'T') RETURNING id",
                             e=email))
    project = asyncio.run(rows("INSERT INTO projects (owner_id, name) VALUES (:o, 'P') RETURNING id", o=owner))
    asyncio.run(rows("INSERT INTO requests (id, project_id, prompt) VALUES (:r, :p, 'x') RETURNING id", r=rid, p=project))
    store = PostgresFileStore(settings.TEST_DATABASE_URL)
    try:
        store.put(rid, FILES, "code")
        store.put(rid, {"app/page.tsx": "changed\n"}, "model")
        store.put(rid, {"app/page.tsx": "changed\n"}, "model")           # unchanged: not rewritten
        assert store.read(rid) == {**FILES, "app/page.tsx": "changed\n"}
    finally:
        store.close()
        asyncio.run(rows("DELETE FROM users WHERE email = :e RETURNING id", e=email))     # cascades to the files
