# 2026-10-30 — Technical-stack upgrade (0037)

Owner-approved upgrade to current LTS/stable pins with bundled runtimes.
No product behavior, schema, URL, or SEO change.

## Runtime and packaging

- Python **3.14.10** bundled from python-build-standalone release
  `20261026` (x86_64 + aarch64 SHA-256 pins) at
  `/opt/scriptorium/runtime/python-3.14`.
- `build-app-venv.sh` builds the app venv from
  `backend/requirements.prod.lock` (runtime-only); `build-venv.sh` builds
  the engine-only venv from `packaging/build-requirements.lock`. Both
  install with `--no-deps`,
  verify pins, and are relocated to `/opt/scriptorium/...`.
- Redis **8.10.2** built from the pinned source tarball (SHA-256
  `b9ffee…c02b3`) as core `redis-server` + `redis-cli`; new
  `scriptorium-redis.service` (`Type=notify`, `scriptorium` user,
  localhost, AOF). Web/worker units now require it.
- `nfpm.yaml` packages the Python runtime, app venv, build venv, Redis
  runtime, both config examples and all three units; distro
  `python3.12`/`redis` dependencies removed. `postinst` seeds
  `/etc/scriptorium/redis.conf` and verifies every runtime.

## Backend

- Python target 3.14; `backend/requirements.lock` regenerated (97 pins):
  FastAPI 0.162.0, Starlette 1.10.0, Pydantic 2.14.1, Uvicorn 0.54.0,
  Gunicorn 26.2.0, SQLAlchemy 2.1.6, Alembic 1.20.1, asyncpg 0.32.0,
  Celery 5.6.3, redis-py 6.4.0, Sphinx 9.2.0, MyST 5.1.0.
- `packaging/build-requirements.lock` regenerated (27 pins) with Sphinx
  9.2.0; docutils stays 0.22.4 (MyST cap).
- Ruff 0.17.3 gate adopted: FastAPI dependencies converted to
  `Annotated[...]` (no blanket B008 suppression), `datetime.UTC`,
  `collections.abc`, `type` aliases, `ClassVar`, import sorting and
  formatting applied. Two scoped noqa comments remain with reasons
  (SQLAlchemy mapper args; build-boundary catch).
- `mypy 2.4.1` strict clean (71 files).

## Frontend

- Node **26.13.0 LTS** / npm 11.20.0; `engines.node` = `26.x`.
- React 19.3.1, TypeScript 7.0.2, TipTap 3.32.1, React Router 8.5.1,
  TanStack Query 5.105.0, RHF 7.91.0, Zod 4.6.7, Radix latest, Tabler
  3.50.0, Vite 8.3.5, Vitest 5.0.5, ESLint 10.13.0, Prettier 3.9.10,
  Playwright 1.64.1, Testing Library 16.3.3, axe-core 4.14.0.
- New `docs/technology/frontend.md` support matrix and
  `frontend/eslint.config.js` (JS/config; TypeScript gated by
  `tsc --noEmit` because typescript-eslint 8.72.1 excludes TS 7).

## CI/security

- Workflows use `checkout@v7`, `setup-python@v7` (3.14.10),
  `setup-node@v7` (26.13.0); frontend lint/format/audit job added.
- Blocking `npm audit --audit-level=high` and
  `pip-audit -r backend/requirements.lock --strict`.
- Packaging contract pins the new scripts, runtime versions/checksums,
  nfpm contents, Redis unit ordering and compose image.
- `docker-compose.yml` uses PostgreSQL 18.6 + Redis 8.10.2 with
  healthchecks and persistent volumes.

## Verification

- Backend: **114 passed, 40 skipped**; ruff check/format and mypy clean.
- `pip-audit`: no known vulnerabilities.
- Frontend: `npm ci`, ESLint, Prettier check, `npm audit`: clean.
- Bundled Python 3.14.10, app/build venvs, and Redis 8.10.2 built
  locally; packaged Redis config answered `PONG`.
- nfpm 2.48.0 built a 117 MB `.deb`; extraction verified runtime/venv
  imports, Redis 8.10.2, and `scriptorium-admin --help`. Runtime and both
  venvs ship without pip/bytecode.
- docutils-0.23 probe with Sphinx 9.2.0: **59 passed**; pin stays 0.22.4
  until MyST lifts its cap and the owner approves.
