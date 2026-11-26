# D:\FYP\FORGE-1\scripts\share.py
"""
Share the studio running on this laptop with someone else, such as a supervisor, for as long as this script runs
(D-256).

    python scripts/share.py

Start FORGE's backend (8000) and studio (3000) first. This starts two free Cloudflare quick tunnels (no account):
one for the studio and one for the live preview (fixed at port 3100 while sharing), and writes .forge_share.json
so FORGE shows the preview's public address in the studio. Press Ctrl+C to stop sharing; the file is removed and
previews go back to private local ports.

Needs cloudflared:  winget install --id Cloudflare.cloudflared
The links change every time this script starts. Anyone with the studio link can open the sign-in page.
"""
import json
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARE_FILE = ROOT / ".forge_share.json"
STUDIO_PORT, PREVIEW_PORT = 3000, 3100
_URL = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def tunnel(port: int) -> tuple[subprocess.Popen, str]:
    """Start a quick tunnel to localhost:port and return it with its public address."""
    proc = subprocess.Popen([CLOUDFLARED, "tunnel", "--no-autoupdate", "--url", f"http://localhost:{port}"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                            errors="replace")
    found: list[str] = []

    def read():                                    # keep draining: a full pipe would stop cloudflared
        for line in proc.stdout:
            if not found and (m := _URL.search(line)):
                found.append(m.group(0))
    threading.Thread(target=read, daemon=True).start()
    for _ in range(300):
        if found or proc.poll() is not None:
            break
        time.sleep(0.1)
    if not found:
        proc.kill()
        raise SystemExit(f"cloudflared did not give an address for port {port}. Is the internet connection up?")
    return proc, found[0]


if __name__ == "__main__":
    CLOUDFLARED = shutil.which("cloudflared")
    if not CLOUDFLARED:
        raise SystemExit("cloudflared is not installed. Install it with:\n  winget install --id Cloudflare.cloudflared\n"
                         "then open a new terminal and run this again.")
    studio, studio_url = tunnel(STUDIO_PORT)
    preview, preview_url = tunnel(PREVIEW_PORT)
    SHARE_FILE.write_text(json.dumps({"preview_url": preview_url, "preview_port": PREVIEW_PORT}), encoding="utf-8")
    print(f"\nShare this link:  {studio_url}\n")
    print(f"(The live preview is served at {preview_url}; the studio shows it by itself.)")
    print("Open a project again (or start a build) so its preview moves to the shared port.")
    print("Keep this window open. Press Ctrl+C to stop sharing.\n")
    try:
        while studio.poll() is None and preview.poll() is None:
            time.sleep(1)
        print("A tunnel stopped; sharing ended.", file=sys.stderr)
    except KeyboardInterrupt:
        pass
    finally:
        SHARE_FILE.unlink(missing_ok=True)
        for p in (studio, preview):
            p.terminate()
        print("Sharing stopped. Previews are private again.")
