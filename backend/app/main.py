"""FastAPI application. Health/version only in M1 (no DB touch so they work pre-migrate)."""

from __future__ import annotations

from fastapi import FastAPI

from app.routers import athenaeums as athenaeums_router
from app.routers import auth as auth_router
from app.routers import categories as categories_router
from app.routers import documents as documents_router
from app.routers import grimoires as grimoires_router
from app.routers import nodes as nodes_router

APP_VERSION = "0.0.0"


def create_app() -> FastAPI:
    app = FastAPI(title="Scriptorium", version=APP_VERSION)
    app.include_router(auth_router.router)
    app.include_router(athenaeums_router.router)
    app.include_router(categories_router.router)
    app.include_router(grimoires_router.router)
    app.include_router(nodes_router.router)
    app.include_router(documents_router.router)

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/version")
    def version() -> dict[str, str]:
        return {"version": APP_VERSION}

    return app


app = create_app()
