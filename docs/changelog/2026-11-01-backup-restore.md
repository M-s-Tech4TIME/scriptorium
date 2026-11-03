# 2026-11-01 — Backup and restore (0039)

Owner-facing export/restore of one Athenaeum in Editorial or Full mode,
with durable numbered `/b/{n}/` URLs after restore. Server move/first-run
provisioning, page aliases, M5, and SEO remain later phases.

## Decisions

- Owner rulings 0039: A1 (mode contents), B3 (ZIP + `.tar.gz`), C1
  (on-demand, no retention; Full async), D1 (importer owns; identities
  nulled), E1 (fresh Athenaeum; reclaim free/own-tombstoned names,
  otherwise suffix).
- Migration `0010backup`: `public_names.owner_id` (backfilled) and
  `backup_jobs`.
- Limits: 8 GiB archive, 16 GiB expanded, 200,000 entries, 512 MiB per
  entry, 15-minute single-use download.

## Backend

- `app/backup/`:
  - `manifest.py` — format/version, mode/format/status vocabularies,
    payload inventory, safe relative paths, environment limits;
  - `archive.py` — ZIP and `.tar.gz` writers plus secure extraction with
    traversal/symlink/duplicate/encryption/inventory/hash/size checks;
    corrupt containers normalize to `BackupError`;
  - `snapshot.py` — repeatable-read snapshot, media hash verification,
    artifact/log collection, portable `data.json`;
  - `export.py` — archive build with fresh media paths and manifest;
  - `restore.py` — full validation before writes, fresh UUID mapping,
    media URL rewrite in TipTap/source/history, build-number/pointer
    preservation, public-name reclaim/suffix, identity nulling, staged
    filesystem cleanup, one-transaction import;
  - `execute.py` — shared Celery/inline Full export and restore jobs;
  - `tokens.py` — HMAC-SHA256 job/expiry download tokens.
- Routes: `POST /athenaeums/{id}/backups`,
  `GET /backup-jobs/{id}`,
  `GET /backup-jobs/{id}/download`,
  `POST /backups/restore` (raw archive; auto-detected container/mode).
- Editorial export streams `FileResponse` with SHA-256/size headers;
  Full export/restore return `202` jobs. Full download is single-use,
  deleted after send or expiry.
- `public_names.owner_id` lets restore distinguish the importer's own
  tombstones from another user's; other names are never touched.
- Audit actions: `backup_exported`, `backup_export_failed`,
  `backup_restored`, `backup_restore_failed`; Full-restore alias
  collisions are recorded in the audit meta.
- Worker repair: `app/worker/celery.py` resolves `-A app.worker`,
  `include=["app.worker.tasks"]` registers all tasks, and build dispatch
  now works in `celery` mode. Dispatch failures mark the build failed
  with a crash log and return `503`.
- Archive hardening: corrupt ZIP/tar.gz containers and file/directory
  path collisions are rejected as `BackupError`.
- CI-discovered build fix: `runner._materialize` now stages canonical
  `/_static/media/{uuid}.{ext}` content URLs by stripping the leading
  slash (Sphinx resolves a leading `/` against the source dir). The
  `_static/media/` jail, traversal, and backslash checks still apply.
  Regression tests cover canonical staging plus a full offline Sphinx
  build with media.

## Frontend

- `BackupPanel` on the Athenaeum page:
  - Editorial/Full and ZIP/`.tar.gz` selection;
  - Editorial streamed download with filename/size/SHA-256;
  - Full job polling and single-use signed download;
  - restore upload with job polling, result link, warnings, and cache
    invalidation.
- Shared `authorizedFetch` and `lib/download.ts`.
- Client tests cover Editorial blob metadata, Full job responses, and
  restore job/result distinction.

## Packaging

- `SC_BACKUP_DISPATCH=celery`, `SC_BACKUP_ROOT=/var/lib/scriptorium/backups`,
  and commented limit/TTL overrides in `config.env.example`.
- `postinst` creates `/var/lib/scriptorium/backups`.

## Tests and gates

- Backend: `141 passed, 48 skipped` locally; archive suite 23 passed;
  live-DB backup suite (4 tests) runs in CI against PG18/Redis. Ruff,
  format, and mypy clean.
- Frontend: typecheck, lint, format check, 19 Vitest tests, production
  build, and high-severity audit gate pass.
- Live local PG/Redis unavailable (Docker socket denied), so the new
  live tests are CI-only.

## Docs

Decision 0039; API, data model, overview, operations/install, security
threat model, Celery technology note, brain, and this changelog.
