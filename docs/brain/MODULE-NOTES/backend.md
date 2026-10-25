# MODULE-NOTES — backend (planned, M1)

Last updated: 2026-10-25 / Ref: serving phase 0035
- Purpose: FastAPI API + SQLA models + convert/sphinx adapters + Celery worker.
- Key files: `backend/app/{routers,schemas,models,convert,sphinx,serving,worker}/`, `backend/alembic/`.
- Interfaces: REST `/api/v1/*` (RBAC per request); browser `/a/{public_slug}/...` serving; `convert.export(tiptap,format)`; `sphinx.build(snapshot)`.
- Invariants: DB drives toctree/conf.py; TipTap JSON canonical; PG18+ only; -W error.
- Serving: only `ok` + valid `manifest.json` artifacts publish/serve; artifact root jail; strict manifest-derived CSP; private-default visibility; immutable public slug/numbered builds.
- Tests: `backend/tests/` (IDOR, round-trip, build-jailed).
