"""Sharing the studio through a tunnel (D-256): while scripts/share.py runs, previews use its fixed port and the
studio shows the public address; FORGE's own live check keeps the local one; without the file nothing changes."""
import json
import subprocess

from agents import preview


def _preview(port):
    return preview.Preview("req_share", preview.bw.ROOT, port, subprocess.Popen.__new__(subprocess.Popen))


def test_without_sharing_previews_stay_private(tmp_path, monkeypatch):
    monkeypatch.setattr(preview, "SHARE_FILE", tmp_path / "none.json")
    assert preview.sharing() == {}
    assert _preview(54321).url == "http://localhost:54321" and preview._free_port() != 3100


def test_while_sharing_the_preview_has_a_fixed_port_and_a_public_address(tmp_path, monkeypatch):
    share = tmp_path / ".forge_share.json"
    share.write_text(json.dumps({"preview_url": "https://abc.trycloudflare.com", "preview_port": 3100}))
    monkeypatch.setattr(preview, "SHARE_FILE", share)
    assert preview._free_port() == 3100
    live = _preview(3100)
    assert live.url == "https://abc.trycloudflare.com" and live.local_url == "http://localhost:3100"
    assert _preview(54321).url == "http://localhost:54321"        # an older preview keeps its own address
