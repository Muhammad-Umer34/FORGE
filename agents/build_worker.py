# D:\FYP\FORGE-1\agents\build_worker.py
"""
The build worker (Phase 3 Group 1, D-231): builds a generated site on FORGE's own server and reports exactly what
broke. Each build gets its own folder under builds/: the site template (site_template/, without its packages), the
49 catalogue components, the site's own files, and a link to the template's node_modules, which is installed once
and shared (no install per build, P9). Then the gate ladder runs: `tsc --noEmit`, and only if that passes,
`next build` with Turbopack (P7). Tool output is turned into file, line and message, so a fix step can act on it.

Safety (P8, P14): a time limit per step, after which the whole process tree is killed; the build's environment
holds only the system variables Node needs, never FORGE's secrets; files may be written only inside the build folder
and never over the template's or the catalogue's files; at most MAX_PARALLEL builds at once and one per user.
shortcut: no network blocking yet (only allowed packages, already installed, so nothing is downloaded); Docker adds
it before real users (plan §3, "What is not in Phase 3").
"""
import asyncio
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "site_template"
CATALOGUE = ROOT / "components"
BUILDS = ROOT / "builds"

STEP_TIMEOUT_SECONDS = 300         # PLACEHOLDER: a real build of a 6-section page took 40 s (spike, 2026-11-14)
MAX_PARALLEL = 2                   # PLACEHOLDER: builds at the same time on one server
_NOT_COPIED = {"node_modules", ".next", "next-env.d.ts", "tsconfig.tsbuildinfo", "package-lock.json"}
# Windows needs SYSTEMROOT and friends or Node cannot even start (found in the spike); nothing else is passed on.
_KEPT_ENV = {"PATH", "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "TEMP", "TMP", "HOME", "USERPROFILE", "APPDATA",
             "LOCALAPPDATA", "PATHEXT", "COMSPEC", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "PROGRAMDATA",
             "HOMEDRIVE", "HOMEPATH", "LANG"}


class BuildError(Exception):
    """The build could not be set up (bad file path, template not installed). Not a site error."""


@dataclass
class Issue:
    file: str                      # relative to the site root, with forward slashes
    line: int
    column: int
    message: str
    code: str = ""                 # e.g. "TS2304"


@dataclass
class Step:
    name: str                      # "typecheck" or "build"
    ok: bool
    seconds: float
    issues: list[Issue] = field(default_factory=list)
    output: str = ""               # the last part of the tool's output, for the log
    timed_out: bool = False


@dataclass
class BuildResult:
    ok: bool
    steps: list[Step]
    seconds: float

    @property
    def issues(self) -> list[Issue]:
        """The first failing step's problems: what a fix round is given (P7)."""
        failed = next((s for s in self.steps if not s.ok), None)
        return failed.issues if failed else []


# ---------------------------------------------------------------- reading tool output
_TSC = re.compile(r"^(?P<file>[^\s(][^(]*)\((?P<line>\d+),(?P<col>\d+)\): error (?P<code>TS\d+): (?P<msg>.+)$")
_LOCATION = re.compile(r"^\.?/?(?P<file>[\w@./\[\]()-]+\.(?:tsx|ts|jsx|js|css|mjs)):(?P<line>\d+):(?P<col>\d+)")


def _rel(path: str) -> str:
    return path.strip().replace("\\", "/").removeprefix("./")


def parse_tsc(output: str) -> list[Issue]:
    """`file(line,col): error TSxxxx: message` lines from `tsc --pretty false`."""
    issues = []
    for raw in output.splitlines():
        m = _TSC.match(raw.strip())
        if m:
            issues.append(Issue(_rel(m["file"]), int(m["line"]), int(m["col"]), m["msg"].strip(), m["code"]))
    return issues


def parse_next(output: str) -> list[Issue]:
    """`./app/page.tsx:3:1` followed by the message on the next non-empty line (Turbopack and webpack)."""
    lines, issues = output.splitlines(), []
    for i, raw in enumerate(lines):
        m = _LOCATION.match(raw.strip())
        if not m:
            continue
        message = next((l.strip() for l in lines[i + 1:i + 4] if l.strip() and not l.strip()[0].isdigit()
                        and not l.strip().startswith(("|", ">"))), "build error")
        issues.append(Issue(_rel(m["file"]), int(m["line"]), int(m["col"]), message))
    if not issues and output.strip():
        tail = [l.strip() for l in output.splitlines() if l.strip()]
        issues.append(Issue("", 0, 0, tail[-1][:300] if tail else "build failed"))
    return issues


# ---------------------------------------------------------------- the build folder
def _safe_path(folder: Path, rel: str) -> Path:
    """Where a site file goes. Only inside the build folder, and never over the template or the catalogue (P6)."""
    rel = rel.replace("\\", "/").lstrip("/")
    target = (folder / rel).resolve()
    if folder.resolve() not in target.parents:
        raise BuildError(f"file outside the site: {rel}")
    protected = {f"components/{p.name}" for p in CATALOGUE.glob("*.tsx")}
    protected |= {p.relative_to(TEMPLATE).as_posix() for p in (TEMPLATE / "components" / "ui").glob("*")}
    protected |= {"package.json", "lib/utils.ts", "next.config.ts", "postcss.config.mjs", "tsconfig.json"}
    if rel in protected or rel.startswith("node_modules/"):
        raise BuildError(f"file is part of the template or the catalogue and may not be replaced: {rel}")
    return target


def _link(target: Path, link: Path) -> None:
    if sys.platform == "win32":
        import _winapi
        _winapi.CreateJunction(str(target), str(link))       # no admin rights needed, unlike a symlink
    else:
        link.symlink_to(target, target_is_directory=True)


def prepare(files: dict[str, str], build_id: str | None = None) -> Path:
    """A fresh build folder: template + catalogue + the site's files + a link to the shared packages."""
    if not (TEMPLATE / "node_modules" / "next").is_dir():
        raise BuildError("the site template's packages are not installed: run `npm install` in site_template/")
    folder = BUILDS / (build_id or uuid.uuid4().hex[:12])
    if folder.exists():
        cleanup(folder)
    folder.mkdir(parents=True)
    for item in TEMPLATE.iterdir():
        if item.name not in _NOT_COPIED:
            (shutil.copytree if item.is_dir() else shutil.copy2)(item, folder / item.name)
    for tsx in CATALOGUE.glob("*.tsx"):
        shutil.copy2(tsx, folder / "components" / tsx.name)
    _link(TEMPLATE / "node_modules", folder / "node_modules")
    for rel, content in files.items():
        target = _safe_path(folder, rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return folder


def cleanup(folder: Path) -> None:
    """Delete a build folder. The node_modules link is removed first, so the shared packages are never touched."""
    link = folder / "node_modules"
    if link.is_junction() if hasattr(link, "is_junction") else False:
        os.rmdir(link)
    elif link.is_symlink():
        link.unlink()
    shutil.rmtree(folder, ignore_errors=True)


# ---------------------------------------------------------------- running the tools
def build_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k.upper() in _KEPT_ENV}
    env["NEXT_TELEMETRY_DISABLED"] = "1"
    env["FORGE_TURBOPACK_ROOT"] = str(ROOT)     # the shared packages live outside the build folder (spike finding)
    return env


def _tool(folder: Path, name: str) -> str:
    return str(folder / "node_modules" / ".bin" / (f"{name}.cmd" if sys.platform == "win32" else name))


def _kill_tree(proc: subprocess.Popen) -> None:
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        proc.kill()


def run_step(folder: Path, name: str, command: list[str], parser, timeout: float = STEP_TIMEOUT_SECONDS) -> Step:
    started = time.perf_counter()
    proc = subprocess.Popen(command, cwd=folder, env=build_env(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    try:
        output, _ = proc.communicate(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        output, _ = proc.communicate()
        timed_out = True
    seconds = round(time.perf_counter() - started, 1)
    ok = proc.returncode == 0 and not timed_out
    issues = [] if ok else ([Issue("", 0, 0, f"{name} took longer than {timeout:.0f} s and was stopped")]
                            if timed_out else parser(output))
    return Step(name, ok, seconds, issues, output[-4000:], timed_out)


def build(files: dict[str, str], build_id: str | None = None, keep: bool = False) -> BuildResult:
    """Build one site: type check, then `next build`. The folder is deleted afterwards unless `keep`."""
    started = time.perf_counter()
    folder = prepare(files, build_id)
    try:
        steps = [run_step(folder, "typecheck", [_tool(folder, "tsc"), "--noEmit", "--pretty", "false"], parse_tsc)]
        if steps[0].ok:
            steps.append(run_step(folder, "build", [_tool(folder, "next"), "build"], parse_next))
    finally:
        if not keep:
            cleanup(folder)
    return BuildResult(all(s.ok for s in steps), steps, round(time.perf_counter() - started, 1))


# ---------------------------------------------------------------- the queue
_slots = asyncio.Semaphore(MAX_PARALLEL)
_per_user: dict[str, asyncio.Lock] = {}


async def build_queued(user_id: str, files: dict[str, str], build_id: str | None = None) -> BuildResult:
    """At most MAX_PARALLEL builds at once and one per user; the others wait their turn."""
    lock = _per_user.setdefault(user_id, asyncio.Lock())
    async with lock, _slots:
        return await asyncio.to_thread(build, files, build_id)
