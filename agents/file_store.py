# D:\FYP\FORGE-1\agents\file_store.py
"""
Where builder steps keep a generated site's files (D-234). Agents stay free of the database (D-133): a builder gets a
FileStore from the run's config and calls only `put` and `read`. The backend passes the PostgreSQL store
(`backend/services/generated_files.py`); tests and scripts use MemoryFileStore. The run's state keeps only the
manifest (FileRef: path, hash, who wrote it).

`put` is an upsert by (request, path) and skips files whose hash is unchanged, so a step repeated after a crash
writes nothing twice (P13).
"""
import hashlib
from typing import Literal, Protocol

from agents.state import FileRef

WrittenBy = Literal["code", "model"]


def sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class FileStore(Protocol):
    def put(self, request_id: str, files: dict[str, str], written_by: WrittenBy,
                  kind: str = "frontend") -> list[FileRef]:
        """Save files (path -> content); returns their manifest entries."""
        ...

    def read(self, request_id: str) -> dict[str, str]:
        """Every file of the request, path -> content."""
        ...


class MemoryFileStore:
    """For tests and scripts. Same rules as the PostgreSQL store."""

    def __init__(self) -> None:
        self.files: dict[tuple[str, str], tuple[str, str, str]] = {}    # (request, path) -> (hash, content, by)
        self.writes = 0                                                 # rows actually written (for tests)

    def put(self, request_id: str, files: dict[str, str], written_by: WrittenBy,
                  kind: str = "frontend") -> list[FileRef]:
        refs = []
        for path, content in files.items():
            digest, key = sha256(content), (request_id, path)
            if self.files.get(key, ("",))[0] != digest:
                self.files[key] = (digest, content, written_by)
                self.writes += 1
            refs.append(FileRef(path=path, sha256=digest, kind=kind, written_by=written_by))
        return refs

    def read(self, request_id: str) -> dict[str, str]:
        return {path: v[1] for (rid, path), v in self.files.items() if rid == request_id}


# The store builder steps use. The API sets the PostgreSQL store at start-up; tests and scripts keep the memory one.
# shortcut: one store per process; fine while FORGE runs as one server process (as the run lock already assumes).
_active: FileStore = MemoryFileStore()


def use_store(store: FileStore) -> None:
    global _active
    _active = store


def active_store() -> FileStore:
    return _active
