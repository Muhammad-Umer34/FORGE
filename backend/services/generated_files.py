# D:\FYP\FORGE-1\backend\services\generated_files.py
"""The PostgreSQL file store for generated sites (D-234), the one the API sets for runs (agents/file_store.py).
Synchronous on purpose: builder steps are plain graph steps, which the server runs in worker threads."""
from psycopg_pool import ConnectionPool

from agents.file_store import WrittenBy, sha256
from agents.state import FileRef
from backend.db.checkpoints import libpq_url

_UPSERT = """
INSERT INTO generated_files (request_id, path, sha256, content, written_by)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (request_id, path) DO UPDATE
  SET sha256 = EXCLUDED.sha256, content = EXCLUDED.content, written_by = EXCLUDED.written_by, updated_at = now()
  WHERE generated_files.sha256 <> EXCLUDED.sha256
"""


class PostgresFileStore:
    def __init__(self, url: str, max_connections: int = 3) -> None:
        # prepare_threshold=None: Supabase's transaction pooler cannot keep prepared statements
        self.pool = ConnectionPool(libpq_url(url), min_size=0, max_size=max_connections, open=True,
                                   kwargs={"prepare_threshold": None})

    def put(self, request_id: str, files: dict[str, str], written_by: WrittenBy,
            kind: str = "frontend") -> list[FileRef]:
        refs = [FileRef(path=p, sha256=sha256(c), kind=kind, written_by=written_by) for p, c in files.items()]
        with self.pool.connection() as conn, conn.cursor() as cur:   # one transaction: all files or none
            cur.executemany(_UPSERT, [(request_id, r.path, r.sha256, files[r.path], written_by) for r in refs])
        return refs

    def read(self, request_id: str) -> dict[str, str]:
        with self.pool.connection() as conn:
            rows = conn.execute("SELECT path, content FROM generated_files WHERE request_id = %s", (request_id,))
            return dict(rows.fetchall())

    def close(self) -> None:
        self.pool.close()
