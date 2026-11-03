# MODULE-NOTES — backend (planned, M1)

Last updated: 2026-11-01 / Ref: backup/restore phase 0039
- Purpose: FastAPI API + SQLA models + convert/sphinx adapters + Celery worker.
- Key files: `backend/app/{routers,schemas,models,convert,sphinx,serving,worker,backup}/`, `backend/alembic/`.
- Interfaces: REST `/api/v1/*` (RBAC per request); browser `/a/{public_slug}/...` serving; `convert.export(tiptap,format)`; `sphinx.build(snapshot)`; backup export/restore routes.
- Invariants: DB drives toctree/conf.py; TipTap JSON canonical; PG18+ only; -W error.
- Serving: only `ok` + valid `manifest.json` artifacts publish/serve; artifact root jail; strict manifest-derived CSP; private-default visibility; numbered builds immutable.
- URL durability (0036): `PublicName` is the single global namespace (current/alias/tombstone; slug PK; nullable FK `SET NULL`); owner-only `PATCH /athenaeums/{id}/public-slug`; old names permanent `308` aliases after auth; deletion tombstones; reversion allowed; no rebuild; page-path aliases deferred.
- Media (0038): `media_assets` owns bytes under `SC_MEDIA_ROOT`; uploads
  are magic-byte sniffed (PNG/JPEG/GIF/WebP/AVIF), 10 MiB capped, atomic;
  canonical refs are `/_static/media/{uuid}.{ext}`; document saves reject
  external/foreign refs; builds copy referenced files and fail loud on
  missing/unsafe paths.
- History (0038): detail + restore endpoints append a new version; restore
  re-validates media and audits `document_restored`.
- Auth: `GET /auth/me` returns the authenticated identity.
- Backup/restore (0039): `app/backup/` validates the manifest/payload
  inventory before any write; ZIP/`.tar.gz` are auto-detected; Editorial
  streams and Full runs as a Celery job (`SC_BACKUP_DISPATCH`). Restore
  creates a fresh Athenaeum, maps every row to fresh UUIDs, preserves build
  numbers/pointers, rewrites media URLs, reclaims only free/same-user-
  tombstoned public names (migration 0010 adds `public_names.owner_id` and
  `backup_jobs`), nulls unmatched identities, and stages/cleans files.
  Download tokens are HMAC-SHA256 over job id + expiry; single-use enforced
  with `UPDATE … WHERE downloaded_at IS NULL … RETURNING`. Worker app
  discovery (`app/worker/celery.py`) and `include=["app.worker.tasks"]`
  register the three task names; dispatch failure marks the job/build
  failed and returns 503.
- Tests: `backend/tests/` (IDOR, round-trip, build-jailed, serving
  aliases/tombstones, media upload/ownership, history restore, backup
  archive hardening, live-DB backup round-trips).
