# D:\FYP\FORGE-1\agents\integration\join.py
"""
Job 1 of the Integration Agent (D-252): the database, backend and frontend parts become one site. Code only.
- one file list; a path two agents both wrote must hold the same text, or it is a FORGE bug;
- `.env.example` names what the site needs from its host, never the values;
- `forge/manifest.json` records every file, which agent wrote it, by code or by model, and its sha256.
"""
import hashlib
import json

ENV_EXAMPLE = """# What this site needs from where it runs. The values are never stored in the site's files.
# FORGE's address: the site's own routes forward forms and lists there.
FORGE_API_URL=
# This site's secret key for FORGE (from the studio when the site is published).
FORGE_SITE_KEY=
"""


class JoinError(RuntimeError):
    """Two parts disagree about a file: a FORGE bug."""


def join(parts: dict[str, dict[str, str]], model_paths: set[str] = frozenset()) -> tuple[dict[str, str], dict]:
    """`parts`: agent -> {path: text}. Returns (the site's files, the manifest)."""
    files: dict[str, str] = {}
    owner: dict[str, str] = {}
    for agent, own in parts.items():
        for path, text in own.items():
            if path in files and files[path] != text:
                raise JoinError(f"FORGE bug: the {owner[path]} and {agent} parts wrote {path} differently")
            files[path] = text
            owner.setdefault(path, agent)
    files[".env.example"] = ENV_EXAMPLE
    owner[".env.example"] = "integration"
    manifest = {"files": [{"path": p, "agent": owner[p], "written_by": "model" if p in model_paths else "code",
                           "sha256": hashlib.sha256(files[p].encode()).hexdigest()} for p in sorted(files)],
                "agents": {a: sum(1 for o in owner.values() if o == a) for a in [*parts, "integration"]}}
    return files, manifest


def manifest_json(manifest: dict, summary: dict) -> str:
    return json.dumps({**manifest, **summary}, indent=2, ensure_ascii=False)
