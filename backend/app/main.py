"""FastAPI application. Health/version only in M1 (no DB touch so they work pre-migrate)."""

from __future__ import annotations

from fastapi import FastAPI

APP_VERSION = "0.0.0"


def create_app() -> FastAPI:
    app = FastAPI(title="Scriptorium", version=APP_VERSION)

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/version")
    def version() -> dict[str, str]:
        return {"version": APP_VERSION}

    return app


app = create_app()
