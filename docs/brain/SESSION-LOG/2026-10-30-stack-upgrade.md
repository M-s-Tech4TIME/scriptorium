# 2026-10-30 — stack upgrade (0037)

- Owner-approved upgrade implemented; no product behavior change.
- Python 3.14.10 bundled via PBS `20261026`; app venv from
  `requirements.prod.lock` + engine-only venv built from locks and
  relocated; Redis 8.10.2 built and bundled with
  `scriptorium-redis.service`; nfpm contents/deps updated; postinst
  seeds Redis config and verifies runtimes.
- Backend pins: FastAPI 0.162.0, Starlette 1.10.0, Pydantic 2.14.1,
  Uvicorn 0.54.0, Gunicorn 26.2.0, SQLAlchemy 2.1.6, Alembic 1.20.1,
  asyncpg 0.32.0, Celery 5.6.3, redis-py 6.4.0, Sphinx 9.2.0, MyST
  5.1.0; docutils 0.22.4.
- Frontend pins: Node 26.13.0 LTS/npm 11.20.0, React 19.3.1, TS 7.0.2,
  TipTap 3.32.1, React Router 8.5.1, TanStack Query 5.105.0, RHF 7.91.0,
  Zod 4.6.7, Vite 8.3.5, Vitest 5.0.5, ESLint 10.13.0, Prettier 3.9.10,
  Playwright 1.64.1.
- Gates: backend 114 passed / 40 skipped; ruff/format/mypy clean;
  pip-audit clean; frontend npm ci/lint/format/audit clean; docutils
  probe 59 passed with Sphinx 9.2.0.
- nfpm 2.48.0 built a 117 MB `.deb`; extracted runtimes/imports and
  `scriptorium-admin --help` verified. Runtime and venvs ship without
  pip/bytecode.
- Known scoped exception: typescript-eslint 8.72.1 excludes TS 7; tsc is
  the type gate.
- Pushed as `9d645e3`; lint-type-test, packaging, and security workflows
  all green.
