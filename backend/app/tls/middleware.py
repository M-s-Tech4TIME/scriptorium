"""HSTS response middleware (decision 0040 F-G1).

HSTS is off by default and enabled by ``scriptorium-admin tls hsts on``
after the operator trusts the local CA. The header is emitted only on
HTTPS responses; plaintext is already redirected by the separate listener.
The state file is cached by mtime/size so a per-request decision does not
re-read JSON.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.tls.state import read_state, state_path


@lru_cache(maxsize=4)
def _cached_hsts(path_text: str, mtime_ns: int, size: int) -> tuple[bool, int]:
    del mtime_ns, size
    state = read_state()
    return state.hsts, state.hsts_max_age


def hsts_settings() -> tuple[bool, int]:
    path = state_path()
    try:
        info = path.stat()
    except OSError:
        return False, 0
    try:
        return _cached_hsts(str(path), info.st_mtime_ns, info.st_size)
    except OSError, ValueError:
        return False, 0


def reset_hsts_cache() -> None:
    """Drop the mtime cache (tests and explicit reloads)."""
    _cached_hsts.cache_clear()


class HstsMiddleware:
    """Add ``Strict-Transport-Security`` to HTTPS responses when enabled."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Any,
        send: Any,
    ) -> None:
        if scope["type"] != "http" or scope.get("scheme") != "https":
            await self.app(scope, receive, send)
            return
        enabled, max_age = hsts_settings()
        if not enabled or max_age <= 0:
            await self.app(scope, receive, send)
            return
        header = (
            b"strict-transport-security",
            f"max-age={max_age}".encode("ascii"),
        )

        async def send_with_hsts(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers = [
                    (key, value)
                    for key, value in headers
                    if key.lower() != b"strict-transport-security"
                ]
                headers.append(header)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_hsts)
