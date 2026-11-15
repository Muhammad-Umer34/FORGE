# D:\FYP\FORGE-1\agents\preview.py
"""
Live preview of a generated site (D-240): `next dev` on FORGE's server, in a build folder made by the build worker
(template, catalogue, the site's files, a link to the shared packages). The studio shows it in a frame. Files
written later go into the same folder, and the dev server's WebSocket updates the open page, so the owner watches
the site appear page by page. Uses webpack, as in the WebContainers spike (Turbopack refuses the linked packages
in dev). Every file is made by code (no model-written code yet), and the server listens on 127.0.0.1 only.
"""
import socket
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from agents import build_worker as bw

READY_TIMEOUT_SECONDS = 120        # PLACEHOLDER: first start of next dev took about 10-20 s locally
# shortcut: one preview at a time (starting one stops the last); a pool with idle time-outs for several users later.
_running: dict[str, "Preview"] = {}
_lock = threading.Lock()


class PreviewError(Exception):
    """The preview could not start. The run carries on without it."""


@dataclass
class Preview:
    request_id: str
    folder: Path
    port: int
    proc: subprocess.Popen
    log: deque = field(default_factory=lambda: deque(maxlen=60))

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}"

    def write(self, files: dict[str, str]) -> None:
        """Write files into the running site; the dev server picks them up and updates the open page."""
        for rel, content in files.items():
            target = bw._safe_path(self.folder, rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _drain(preview: Preview, ready: threading.Event) -> None:
    """Read the dev server's output for as long as it runs (a full pipe would stop it) and spot 'Ready'."""
    for line in preview.proc.stdout:
        preview.log.append(line.rstrip())
        if "Ready" in line:                  # next dev prints "✓ Ready in 2.1s"
            ready.set()
    ready.set()


def start(request_id: str, files: dict[str, str]) -> Preview:
    """A running preview of these files. Stops any other preview first."""
    stop_all()
    try:
        folder = bw.prepare(files, build_id=f"preview-{request_id[-12:]}")
    except bw.BuildError as error:
        raise PreviewError(str(error)) from error
    port = _free_port()
    proc = subprocess.Popen([bw._tool(folder, "next"), "dev", "--webpack", "-p", str(port), "-H", "127.0.0.1"],
                            cwd=folder, env=bw.build_env(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    preview, ready = Preview(request_id, folder, port, proc), threading.Event()
    threading.Thread(target=_drain, args=(preview, ready), daemon=True).start()
    if not ready.wait(READY_TIMEOUT_SECONDS) or proc.poll() is not None:
        _stop(preview)
        raise PreviewError("the preview server did not start: " + " | ".join(list(preview.log)[-5:]))
    with _lock:
        _running[request_id] = preview
    return preview


def get(request_id: str) -> Preview | None:
    with _lock:
        return _running.get(request_id)


def _stop(preview: Preview) -> None:
    if preview.proc.poll() is None:
        bw._kill_tree(preview.proc)
    time.sleep(0.5)                          # Windows releases the folder's files a moment after the process ends
    try:
        bw.cleanup(preview.folder)
    except OSError:
        pass                                 # a file still held; the next start of this request makes a fresh folder


def stop_all() -> None:
    """Stop every preview (server shutdown, or before a new one starts)."""
    with _lock:
        running = list(_running.values())
        _running.clear()
    for preview in running:
        _stop(preview)
