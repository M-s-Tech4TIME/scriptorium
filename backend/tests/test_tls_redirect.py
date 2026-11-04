"""HTTP→HTTPS redirect and HSTS middleware regressions (decision 0040)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from app.tls import generate, hsts
from app.tls.middleware import HstsMiddleware, hsts_settings, reset_hsts_cache
from app.tls.redirect import HttpsRedirectApp


@pytest.fixture(autouse=True)
def _tls_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SC_TLS_ROOT", str(tmp_path / "tls"))
    monkeypatch.delenv("SC_TLS_REDIRECT_HOST", raising=False)
    monkeypatch.delenv("SC_TLS_HSTS_MAX_AGE", raising=False)


async def _call(app: Any, scope: dict[str, Any]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    await app(scope, receive, send)
    return messages


def _scope(*, scheme: str = "http", host: str = "example.test") -> dict[str, Any]:
    return {
        "type": "http",
        "scheme": scheme,
        "method": "GET",
        "path": "/docs/page",
        "raw_path": b"/docs/page",
        "query_string": b"a=1",
        "headers": [(b"host", host.encode("latin-1"))],
    }


def test_redirects_known_host_with_308() -> None:
    generate(hostnames=["example.test"], reload_service=False)
    messages = asyncio.run(_call(HttpsRedirectApp(), _scope()))
    start = messages[0]
    assert start["status"] == 308
    headers = dict(start["headers"])
    assert headers[b"location"] == b"https://example.test/docs/page?a=1"
    assert messages[1]["body"] == b""


def test_redirect_falls_back_to_certificate_san() -> None:
    generate(hostnames=["example.test"], reload_service=False)
    messages = asyncio.run(_call(HttpsRedirectApp(), _scope(host="attacker.invalid")))
    headers = dict(messages[0]["headers"])
    assert headers[b"location"].startswith(b"https://example.test/")


def test_redirect_without_certificate_is_a_clear_400() -> None:
    messages = asyncio.run(_call(HttpsRedirectApp(), _scope()))
    assert messages[0]["status"] == 400
    assert b"No valid TLS host" in messages[1]["body"]


def test_hsts_header_only_on_https_when_enabled() -> None:
    generate(hostnames=["example.test"], reload_service=False)
    hsts(True, max_age=123)
    reset_hsts_cache()

    async def inner(scope: dict[str, Any], receive: Any, send: Any) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = HstsMiddleware(inner)
    https_messages = asyncio.run(_call(middleware, _scope(scheme="https")))
    https_headers = dict(https_messages[0]["headers"])
    assert https_headers[b"strict-transport-security"] == b"max-age=123"

    http_messages = asyncio.run(_call(middleware, _scope(scheme="http")))
    http_headers = dict(http_messages[0]["headers"])
    assert b"strict-transport-security" not in http_headers


def test_hsts_off_by_default() -> None:
    generate(hostnames=["example.test"], reload_service=False)
    reset_hsts_cache()
    enabled, max_age = hsts_settings()
    assert enabled is False
    assert max_age == 31_536_000
