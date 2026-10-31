# Technology — FastAPI 0.162.0 (+ Starlette, Pydantic, Uvicorn, Gunicorn)

- Versions (locked `backend/requirements.lock`): FastAPI 0.162.0 (2026-10),
  Starlette 1.10.0, Pydantic 2.14.1, Uvicorn 0.54.0, Gunicorn 26.2.0.
- Why: async-native API, Pydantic v2 validation, auto-OpenAPI (decision 0005).
  Rolling 0.x line — mitigated by exact pin + lock + quarterly upgrades (Rule 5.5).
- Used: `backend/app/routers/`; served via gunicorn+UvicornWorker (`packaging/systemd/`).
  FastAPI dependency defaults now use `Annotated[...]` so Ruff's B008 gate is
  clean without suppressions.
- Verified: 2026-10-30 (PyPI/GitHub; lock resolved 2026-10-30). Backend suite
  `114 passed, 40 skipped`; ruff/format/mypy clean.
