# MODULE-NOTES — backend (planned, M1)

Last updated: 2026-10-16 / Ref: uncommitted
- Purpose: FastAPI API + SQLA models + convert/sphinx adapters + Celery worker.
- Key files: `backend/app/{routers,schemas,models,convert,sphinx,worker}/`, `backend/alembic/`.
- Interfaces: REST `/api/v1/*` (RBAC per request); `convert.export(tiptap,format)`; `sphinx.build(snapshot)`.
- Invariants: DB drives toctree/conf.py; TipTap JSON canonical; PG18+ only; -W error.
- Tests: `backend/tests/` (IDOR, round-trip, build-jailed).
