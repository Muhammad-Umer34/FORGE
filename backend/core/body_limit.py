# D:\FYP\FORGE-1\backend\core\body_limit.py
"""
Refuses request bodies that are too large before they are read (D-193). Without this, an upload is
received in full and written to a temporary file before any route can check its size, so a few
huge uploads could fill the disk.

Image uploads may be up to MAX_IMAGE_UPLOAD_BYTES; every other request up to MAX_JSON_BODY_BYTES.
The declared Content-Length is checked first; bodies sent without one are counted as they arrive.
"""
import json

from backend.core.config import settings


class _TooLarge(Exception):
    pass


def _limit_for(path: str) -> int:
    return settings.MAX_IMAGE_UPLOAD_BYTES if path.endswith("/image") else settings.MAX_JSON_BODY_BYTES


async def _send_413(send, limit: int) -> None:
    body = json.dumps({"detail": {"code": "too_large", "message": f"This upload is too large. The limit is {limit // 1024} KB."}}).encode()
    await send({"type": "http.response.start", "status": 413,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})


class BodySizeLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] in ("GET", "HEAD", "OPTIONS"):
            return await self.app(scope, receive, send)
        limit = _limit_for(scope["path"])
        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > limit:
            return await _send_413(send, limit)

        received = 0
        too_large = False
        started = False

        async def counted_receive():
            nonlocal received, too_large
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    too_large = True
                    raise _TooLarge()
            return message

        # A route may catch the error itself (FastAPI turns any body error into a 400), so once the
        # body is too large, whatever response the route starts is replaced by the 413.
        async def tracked_send(message):
            nonlocal started
            if too_large:
                if message["type"] == "http.response.start" and not started:
                    started = True
                    await _send_413(send, limit)
                return
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, counted_receive, tracked_send)
        except _TooLarge:
            if not started:
                await _send_413(send, limit)
