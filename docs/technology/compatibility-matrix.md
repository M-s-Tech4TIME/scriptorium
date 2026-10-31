# Compatibility matrix (frozen set, verified 2026-10-30)

| Component | Pinned | Latest stable seen | Support | Verified source |
|---|---|---|---|---|
| Python | 3.14.10 (bundled) | 3.14.10 / 3.15 deferred | to Oct 2030 | python.org / python-build-standalone |
| Python runtime | PBS 20261026 | 20261026 | pinned asset + SHA-256 | astral-sh/python-build-standalone |
| Sphinx | 9.2.0 | 9.2.0 | 9.x current | sphinx-doc.org/PyPI |
| docutils | 0.22.4 (0.23 gated) | 0.23 (2026-05-27) | current; probe green 2026-10-30, MyST metadata still caps | PyPI |
| MyST-Parser | 5.1.0 | 5.1.0 (2026-05-13) | current, needs Sphinx ≥8<10 | PyPI/changelog |
| FastAPI | 0.162.0 | 0.162.0 (2026-10) | rolling — pin+lock | PyPI/GitHub |
| Starlette | 1.10.0 | 1.10.0 | current | PyPI |
| Pydantic | 2.14.1 | 2.14.1 | current | PyPI |
| Uvicorn | 0.54.0 | 0.54.0 | current | PyPI |
| Gunicorn | 26.2.0 | 26.2.0 | current | PyPI |
| SQLAlchemy | 2.1.6 | 2.1.6 (2026-10) | needs Py ≥3.11 | PyPI/GitHub |
| Alembic | 1.20.1 | 1.20.1 (2026-09-11) | needs SQLA ≥2.0 | PyPI |
| asyncpg | 0.32.0 | 0.32.0 | current | PyPI |
| Celery | 5.6.3 | 5.6.3 (5.7b1 excluded) | mature | PyPI/changelog |
| redis-py | 6.4.0 | 6.4.0 | Celery/kombu-compatible cap (`<6.5`) | PyPI |
| Redis (broker) | 8.10.2 (bundled) | 8.10.2 | current stable | redis.io |
| argon2-cffi | 25.1.0 | 25.1.0 | current | PyPI |
| PyJWT | 2.15.1 | 2.15.1 | current | PyPI |
| httpx (dev) | 0.28.1 | 0.28.1 | current | PyPI |
| Dramatiq (rejected alt) | 2.2.1 | 2.2.1 (2026-09-02) | active | PyPI |
| Node (build) | 26.13.0 LTS | 26.13.0 LTS | LTS to ~2029 | nodejs.org |
| npm (build) | 11.20.0 (Node-bundled) | 12.2.1 | bundled with Node 26.13.0 | nodejs.org/npm |
| React | 19.3.1 | 19.3.1 | 19 supported, 18 security-only | npm/react.dev |
| React Router | 8.5.1 | 8.5.1 | v8 stable | npm |
| TanStack Query | 5.105.0 | 5.105.0 | v5 stable | npm |
| React Hook Form | 7.91.0 | 7.91.0 | v7 stable | npm |
| Zod | 4.6.7 | 4.6.7 | v4 stable | npm |
| TypeScript | 7.0.2 (owner override 0006) | 7.0.2 (2026-08-20) | current Go rewrite | npm/GitHub |
| TipTap | 3.32.1 | 3.32.1 | v3 stable | npm/tiptap.dev |
| Vite | 8.3.5 | 8.3.5 | current | npm |
| Vitest | 5.0.5 | 5.0.5 | current | npm |
| ESLint | 10.13.0 | 10.13.0 | current | npm |
| Prettier | 3.9.10 | 3.9.10 | current | npm |
| Playwright | 1.64.1 | 1.64.1 | current | npm |
| Testing Library | 16.3.3 | 16.3.3 | current | npm |
| axe-core | 4.14.0 | 4.14.0 | current | npm |
| Tabler icons | 3.50.0 | 3.50.0 | MIT, vendored sprite | npm |
| PostgreSQL | 18.6 exclusive | 18.6 / 19 RC1 excluded | 18 to 2030-11-14 | postgresql.org |
| nfpm | 2.x (validated 2.48.0) | 2.48.0 | current | goreleaser/nfpm |

## Support matrix (frontend runtime)

| Browser | Supported |
|---|---|
| Chrome / Edge | latest 2 stable |
| Firefox | latest 2 stable |
| Safari | latest 2 stable |
| iOS Safari | 18+ |
| Android Chrome | latest stable |
| Internet Explorer | not supported |

## Policy

- Exact pins in `backend/requirements.lock`, `packaging/build-requirements.lock`
  and `frontend/package-lock.json`; lockfiles are committed.
- Weekly Dependabot for npm, pip, GitHub Actions and Docker.
- Blocking `npm audit --audit-level=high` and `pip-audit -r
  backend/requirements.lock --strict`; CycloneDX SBOM and license checks are
  part of the release gate.
- Quarterly upgrade window; security SLA: critical 24h, high 7d, medium 30d,
  low next quarter.
- Known exception: `typescript-eslint` peer range excludes TS 7.0.2, so
  ESLint covers JavaScript/config only; `tsc --noEmit` gates TypeScript.
  Review when typescript-eslint supports `typescript >=7`.
- docutils 0.22.4 remains a time-boxed exception until MyST lifts its
  `<0.23` cap; the manual probe is the bump gate and is reviewed every 90 days.
- Distro check: U24.04/D12/RHEL9/Fedora need only glibc + PostgreSQL client;
  Python 3.14 and Redis 8.10.2 ship inside the package. PG18 comes from PGDG
  or the distro module where available.
- Trio risk: MyST 5.x upper-bounds docutils — 0.23 gated (0003). The
  manual `docutils-0.23-probe` workflow / `scripts/probe-docutils-023.sh`
  is the bump gate; its 2026-10-30 run passed 59 tests with Sphinx 9.2.0,
  but the pin stays 0.22.4 until MyST lifts the metadata cap and the owner
  approves a bump.
