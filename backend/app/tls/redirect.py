"""HTTP→HTTPS redirect listener (decision 0040 F-A1).

This is a deliberately tiny ASGI application: every HTTP request receives
a 308 to the same path on HTTPS. The ``Host`` header is attacker-controlled,
so it is used only when it matches a current certificate SAN; otherwise the
redirect falls back to the configured canonical host or a certificate SAN.
No request body is read and no application state is touched.
"""

from __future__ import annotations

import ipaddress
from typing import Any

from app.tls.manager import redirect_target

_REDIRECT_STATUS = 308


def _format_host(host: str) -> str:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return host
    if address.version == 6:
        return f"[{host}]"
    return host


class HttpsRedirectApp:
    """ASGI app that redirects all HTTP traffic to HTTPS."""

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Any,
        send: Any,
    ) -> None:
        if scope["type"] == "lifespan":
            await _lifespan(receive, send)
            return
        if scope["type"] != "http":
            return
        headers = {
            key.lower(): value
            for key, value in scope.get("headers", [])
            if isinstance(key, bytes) and isinstance(value, bytes)
        }
        host_header = headers.get(b"host", b"").decode("latin-1")
        target = redirect_target(host_header)
        if target is None:
            await _plain(send, 400, "No valid TLS host is configured.\n")
            return
        raw_path = scope.get("raw_path") or scope.get("path", "/").encode("latin-1")
        location = f"https://{_format_host(target)}{raw_path.decode('latin-1')}"
        query = scope.get("query_string", b"")
        if query:
            location = f"{location}?{query.decode('latin-1')}"
        await send(
            {
                "type": "http.response.start",
                "status": _REDIRECT_STATUS,
                "headers": [
                    (b"location", location.encode("latin-1")),
                    (b"content-type", b"text/plain; charset=utf-8"),
                    (b"content-length", b"0"),
                    (b"cache-control", b"no-store"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": b""})


async def _lifespan(receive: Any, send: Any) -> None:
    while True:
        message = await receive()
        if message["type"] == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        elif message["type"] == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
            return


async def _plain(send: Any, status: int, text: str) -> None:
    body = text.encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"content-length", str(len(body)).encode("ascii")),
                (b"cache-control", b"no-store"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


app = HttpsRedirectApp()
