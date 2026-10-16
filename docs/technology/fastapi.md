# Technology — FastAPI 0.143.0 (+ Starlette, Pydantic, Uvicorn, Gunicorn)

- Versions (locked `backend/requirements.lock`): FastAPI 0.143.0 (2026-10-08),
  Starlette 1.8.0, Pydantic 2.11.7, Uvicorn 0.34.0, Gunicorn 23.0.0.
- Why: async-native API, Pydantic v2 validation, auto-OpenAPI (decision 0005).
  Rolling 0.x line — mitigated by exact pin + lock + quarterly upgrades (Rule 5.5).
- Used: `backend/app/routers/`; served via gunicorn+UvicornWorker (`packaging/systemd/`).
- Verified: 2026-10-16 (PyPI/GitHub; lock resolved 2026-10-16).
