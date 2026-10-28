# MODULE-NOTES — backend (planned, M1)

Last updated: 2026-10-28 / Ref: URL-durability phase 0036
- Purpose: FastAPI API + SQLA models + convert/sphinx adapters + Celery worker.
- Key files: `backend/app/{routers,schemas,models,convert,sphinx,serving,worker}/`, `backend/alembic/`.
- Interfaces: REST `/api/v1/*` (RBAC per request); browser `/a/{public_slug}/...` serving; `convert.export(tiptap,format)`; `sphinx.build(snapshot)`.
- Invariants: DB drives toctree/conf.py; TipTap JSON canonical; PG18+ only; -W error.
- Serving: only `ok` + valid `manifest.json` artifacts publish/serve; artifact root jail; strict manifest-derived CSP; private-default visibility; numbered builds immutable.
- URL durability (0036): `PublicName` is the single global namespace (current/alias/tombstone; slug PK; nullable FK `SET NULL`); owner-only `PATCH /athenaeums/{id}/public-slug`; old names permanent `308` aliases after auth; deletion tombstones; reversion allowed; no rebuild; page-path aliases deferred.
- Tests: `backend/tests/` (IDOR, round-trip, build-jailed, serving aliases/tombstones).
