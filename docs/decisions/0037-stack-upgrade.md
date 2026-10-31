# 0037 — Technical-stack upgrade: bundled Python 3.14, Node 26 LTS, current dependency set

- **Status:** accepted and implemented
- **Decided:** 2026-10-30 (owner approved the stack-upgrade plan)
- **Amends:** 0003 (Python line and version-set lock), 0005 (Redis server
  version), 0019 (redis-py driver), 0026 (build-venv runtime), and the
  technology docs/matrix.
- **Scope:** toolchain and dependency upgrade. No product behavior, URL,
  schema, SEO, or editorial-semantics change.

## Owner rulings carried into this record

- Use formal LTS where upstream offers it; otherwise latest stable with
  active maintenance, an explicit security policy, exact pins, lockfiles,
  and a defined upgrade/security-patch cadence.
- Upgrade every stack item; add a frontend support matrix and dependency/
  security checks.
- Bundle Python 3.14 via `python-build-standalone` (Option A) and bundle
  Redis 8.10.2 with a `scriptorium-redis.service` (Option 1).
- No docutils bump and no new asset-injecting Sphinx extension without
  approval.
- The SEO phase remains last and starts only after its own plan/rulings.

## Resolved versions

| Area | Version |
|---|---|
| Python | 3.14.10 (PBS release 20261026, SHA-256 per arch) |
| PostgreSQL | 18.6 |
| Redis server | 8.10.2 (built from source; SHA-256 pinned) |
| redis-py | 6.4.0 (`kombu 5.6.2` requires `redis<6.5`) |
| Sphinx | 9.2.0 |
| docutils | 0.22.4 (time-boxed exception; MyST cap) |
| MyST-Parser | 5.1.0 |
| FastAPI | 0.162.0 |
| Starlette | 1.10.0 |
| Pydantic | 2.14.1 |
| Uvicorn | 0.54.0 |
| Gunicorn | 26.2.0 |
| SQLAlchemy | 2.1.6 |
| Alembic | 1.20.1 |
| asyncpg | 0.32.0 |
| Celery | 5.6.3 |
| Node | 26.13.0 LTS (npm 11.20.0, Node-bundled) |
| React / React DOM | 19.3.1 |
| TypeScript | 7.0.2 (owner override 0006) |
| TipTap | 3.32.1 |
| React Router | 8.5.1 |
| TanStack Query | 5.105.0 |
| React Hook Form | 7.91.0 |
| Zod | 4.6.7 |
| Vite | 8.3.5 |
| Vitest | 5.0.5 |
| ESLint | 10.13.0 |
| Prettier | 3.9.10 |
| Playwright | 1.64.1 |
| Testing Library | 16.3.3 |
| axe-core | 4.14.0 |
| Tabler icons | 3.50.0 (public theme sprite remains 3.36.0) |

## Packaging changes

- `packaging/scripts/fetch-python.sh` downloads and verifies the pinned
  Python 3.14.10 standalone runtime for x86_64/aarch64.
- `build-app-venv.sh` builds the application venv from
  `backend/requirements.prod.lock` (runtime-only; dev tools stay out of
  the package); `build-venv.sh` builds the engine-only venv from
  `packaging/build-requirements.lock`. Both use the bundled runtime,
  install with `--no-deps`, verify their pins, and are relocated to
  `/opt/scriptorium/...`; the installed host never runs pip.
- `build-redis.sh` verifies and builds Redis 8.10.2 core
  (`redis-server` + `redis-cli`); `scriptorium-redis.service` runs it as
  the `scriptorium` user; web/worker units require that unit.
- `nfpm.yaml` packages the runtime, app venv, build venv, Redis runtime,
  both config examples, and all three units. Distro Python/Redis
  dependencies are gone.
- `postinst` seeds `/etc/scriptorium/redis.conf` and fails loud if any
  bundled runtime is missing.

## CI and security

- Backend CI uses Python 3.14.10; frontend CI uses Node 26.13.0; action
  versions are current (`checkout@v7`, `setup-python@v7`,
  `setup-node@v7`).
- Blocking `npm audit --audit-level=high` and
  `pip-audit -r backend/requirements.lock --strict`.
- Weekly Dependabot (npm/pip/Actions/Docker), quarterly upgrade window,
  SLA critical 24h / high 7d / medium 30d / low next quarter.
- Known scoped exception: `typescript-eslint 8.72.1` declares
  `typescript <6.1.0`, so ESLint covers JavaScript/config only;
  `tsc --noEmit` is the TypeScript gate until upstream widens the peer
  range.

## Verification

- Backend offline suite: **114 passed, 40 skipped**.
- Ruff 0.17.3 check + format: clean; mypy strict: 71 files clean.
- `pip-audit -r backend/requirements.lock`: no known vulnerabilities.
- `npm ci`, ESLint, Prettier check, `npm audit --audit-level=high`:
  clean (0 vulnerabilities).
- Bundled Python 3.14.10 runtime, app venv, build venv, and Redis 8.10.2
  were built locally; the packaged Redis config answered `PONG`.
- nfpm 2.48.0 produced a 117 MB `.deb`; extraction verified the
  runtime/venv imports, Redis 8.10.2, and `scriptorium-admin --help`.
- docutils-0.23 probe with Sphinx 9.2.0: **59 passed**; pin stays 0.22.4
  until MyST lifts its cap and the owner approves a bump.
