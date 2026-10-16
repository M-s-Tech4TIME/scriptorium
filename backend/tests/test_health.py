"""Health/version contract without TestClient (no httpx in M1 — keeps dep set frozen)."""

from __future__ import annotations

from fastapi.routing import APIRoute

from app.main import create_app


def test_health_and_version_routes_present() -> None:
    app = create_app()
    paths = sorted(route.path for route in app.routes if isinstance(route, APIRoute))
    assert "/api/v1/health" in paths
    assert "/api/v1/version" in paths
