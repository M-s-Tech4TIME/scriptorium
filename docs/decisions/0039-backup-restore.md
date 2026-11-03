# 0039 — Backup and restore (Editorial + Full)

- **Status:** accepted — owner rulings 2026-11-01
- **Owner rulings:** A1 (mode contents / published-only URL durability),
  B3 (both ZIP and `.tar.gz`), C1 (on-demand, no retention; Full async),
  D1 (importer owns; unmatched identities nulled), E1 (fresh Athenaeum;
  reclaim free/own-tombstoned public names, otherwise auto-suffix).
- **Scope:** owner-facing export and restore of one Athenaeum. Server
  move / first-run provisioning, page aliases, M5, and SEO stay separate.

## Why

Scriptorium must let an owner take their library out of the platform and
put it back, without losing public URLs. The approved requirement from
0038 is explicit: **both Editorial and Full modes**, and a restored site
must preserve numbered `/b/{n}/` URLs exactly.

## Mode contents (A1)

Both modes are self-contained archives. A restore always creates a
**fresh Athenaeum** for the importing user; it never mutates or merges
into an existing site.

| Data | Editorial | Full |
|---|---|---|
| Athenaeum title, editor slug, public name, visibility, custom CSS | ✅ | ✅ |
| `public_names` current name + aliases (owner, retired timestamps) | ✅ | ✅ |
| Categories, grimoires (slug/title/source format/theme), nodes | ✅ | ✅ |
| Documents (canonical TipTap + derived source), full `document_history` | ✅ | ✅ |
| Media rows + bytes (all assets in the library) | ✅ | ✅ |
| Build rows for **ever-published, successful** builds | ✅ | ✅ |
| Build rows for unpublished/failed builds | — | ✅ |
| Served artifacts (`html/` + artifact `manifest.json`) for included ok builds | ✅ | ✅ |
| Build logs | — | ✅ |
| `latest` / `stable` pointers | ✅ | ✅ |
| Users, memberships, refresh tokens, audit log | — | — |

Editorial is the portable-content mode that still honors the numbered-URL
guarantee for every build that was ever published (a published build
remains addressable by number after unpublishing, 0035). Full is the
server-move-fidelity mode: it also carries failed builds and logs, and
artifacts for every successful build. Queued/running builds are never
restored as active work (that would permanently block the restored
site); they are omitted.

## Container (B3)

The owner selects **ZIP** or **`.tar.gz`** per export. Restore detects the
container from magic bytes; no extension trust.

Both containers share one payload model:

```
manifest.json          # format, mode, source summary, counts, file inventory
data.json              # all relational rows (identity references stripped)
media/{storage_path}   # asset bytes, e.g. media/ab/ab…png
artifacts/{n}/...      # artifact dir: html/... + manifest.json
logs/{n}.log           # Full only
```

- `manifest.json` is the integrity contract: `format=scriptorium-backup@1`,
  mode, generated timestamp, source athenaeum summary, per-payload
  `sha256` + `bytes`, and counts. Every payload entry is hashed; the
  manifest is the only unsigned entry (it is the root of trust inside the
  archive and is itself validated structurally).
- ZIP uses zip64, deterministic entry order, fixed timestamps, and
  deflate. `.tar.gz` uses PAX with uid/gid 0, empty owner names, and a
  fixed mtime. Determinism is best-effort but ordering and hashes are
  stable.
- Filename: `scriptorium-{public_slug}-{mode}-{UTC}.{zip|tar.gz}`.

## Delivery and retention (C1)

- **Editorial:** generated on demand and streamed synchronously; the
  temporary file is deleted after the response completes.
- **Full:** a Celery job (`SC_BACKUP_DISPATCH=celery|inline`, same
  dispatch contract as builds) generates the archive under
  `SC_BACKUP_ROOT` and returns a job. The owner polls the job and receives
  an **expiring signed download link** (HMAC-SHA256 over job id + expiry,
  15 minutes, no bearer required). The file is deleted after download or
  expiry; there is no server-side backup library/retention.
- Restore follows the same execution split: Editorial is synchronous;
  Full is uploaded to a temporary path and processed as a job.

## Restore semantics (D1/E1)

- **Target:** always a new Athenaeum owned by the authenticated importer.
  Editor slug is suffixed on conflict. No merge, no overwrite.
- **Public names:** the backup's current name is reused when it is free or
  is a tombstone owned by the same user; otherwise it gets the standard
  8-hex suffix. Aliases are re-attached when their names are free or
  owned by the importer; conflicting names are skipped and reported in
  the audit/job result. Other users' names/tombstones are never touched.
  To make “same user's tombstone” checkable after deletion,
  `public_names` gains a nullable `owner_id` (migration 0010), backfilled
  from each live Athenaeum's owner.
- **Identity:** all user references inside content (`document.updated_by`,
  `document_history.author`, `media.created_by`, build trigger/publisher)
  become NULL; the importer owns the new site. Memberships, refresh
  tokens, and audit rows are never exported.
- **IDs:** every restored row gets a fresh UUID; old→new maps keep the
  tree, documents, history, media, and builds consistent. Media URLs in
  documents and history are rewritten from the old asset UUID to the new
  one; artifact HTML is untouched because artifacts are self-contained.
- **Build numbers:** preserved exactly for every imported build; artifacts
  are re-homed under `{SC_ARTIFACT_ROOT}/{new_athenaeum_id}/{n}/`. This is
  what keeps `/a/{name}/b/{n}/` byte-identical after a Full or Editorial
  restore.
- **Pointers:** `latest`/`stable` map by build number to the new rows.
- **Atomicity:** validation and extraction happen before any DB write;
  filesystem writes are staged and cleaned on failure; the DB import is
  one transaction. A failed restore leaves no new Athenaeum.

## Security (Rule 2)

Archives are untrusted input. Restore rejects: absolute/traversal paths,
backslash tricks, symlinks/hardlinks/devices, duplicate entries, encrypted
ZIP entries, missing/extra entries versus the manifest, hash/size
mismatches, unknown format versions, invalid JSON, dangling FK references,
node cycles, and media/build files that do not match their rows. Limits:
8 GiB archive, 16 GiB expanded, 200,000 entries, 512 MiB per entry, and a
15-minute download token. Full-job files live outside the web root and are
served only through the owner-scoped job/download routes.

## API

| Route | Access | Notes |
|---|---|---|
| POST `/api/v1/athenaeums/{id}/backups` `{mode,format}` | owner | Editorial → streamed archive; Full → `202` job |
| GET `/api/v1/backup-jobs/{job_id}` | requester | status, error, result site, signed download URL while valid |
| GET `/api/v1/backup-jobs/{job_id}/download?token=…` | signed token | streams the Full archive; deletes it after send |
| POST `/api/v1/backups/restore` (raw archive body) | authenticated | auto-detects container+mode; Editorial → `201` new site, Full → `202` job |

Audit actions: `backup_exported`, `backup_export_failed`,
`backup_restored`, `backup_restore_failed`.

## Schema (migration 0010)

- `public_names.owner_id UUID NULL FK users ON DELETE SET NULL` —
  backfilled from live Athenaeums; preserved through deletion so a user's
  own tombstones can be reclaimed on restore.
- `backup_jobs(id UUID PK, kind export|restore, athenaeum_id FK NULL,
  result_athenaeum_id FK NULL, requested_by FK NULL, mode, format, status
  queued|running|ok|failed, path, size_bytes, sha256, error, created_at,
  started_at, finished_at, expires_at, downloaded_at)`.

## Disclosed micro-defaults

- 15-minute signed download window; 8 GiB archive / 16 GiB expanded /
  200k entries / 512 MiB per-entry caps.
- Editorial exports include all ever-published successful builds, not
  only the current pointers.
- Full restore omits queued/running builds (imported terminal builds keep
  their numbers; gaps are valid).
- Restore aliases that collide with another owner's live name are skipped,
  not suffixed (a site has one canonical current name; aliases are
  optional historical names).
- Backup files are deleted after download/expiry; a restart may leave an
  orphan temp file, which the next job/status request sweeps.

## Implementation note (2026-11-01)

- **Backend:** `app/backup/` (`manifest`, `archive`, `snapshot`, `export`,
  `restore`, `execute`, `tokens`), `app/routers/backups.py`,
  `app/serving/names.py` (shared name allocation/reclaim), migration
  `0010backup`, and `BackupJob`/`PublicName.owner_id` models.
- **Worker:** `app/worker/celery.py` (discovery for `-A app.worker`),
  `include=["app.worker.tasks"]`, and the three `@shared_task` names.
  This also fixed three latent production-only defects: the app could not
  be resolved by the unit, tasks were never registered, and the builds
  router never dispatched in `celery` mode. Dispatch failures now mark the
  build failed with a crash log and return `503`.
- **Frontend:** `BackupPanel` on the Athenaeum page (mode/container
  selection, Editorial stream download, Full job polling + single-use
  download, restore upload, result/warnings, cache invalidation) plus
  shared `authorizedFetch`, `lib/download.ts`, and client tests.
- **Packaging:** `SC_BACKUP_DISPATCH`, `SC_BACKUP_ROOT`, commented
  `SC_BACKUP_*` overrides in `config.env.example`; `backups/` created by
  `postinst`.
- **Hardening:** corrupt ZIP/tar.gz containers normalize to `BackupError`;
  file/directory path collisions are rejected before extraction; tests
  cover both. Archive tests: 23; live-DB backup tests: 4.
- **CI-discovered build fix:** the live round-trip exposed that
  `runner._materialize` required a `_static/media/` prefix while content
  stores canonical `/_static/media/...` URLs. Staging now strips the
  leading slash (Sphinx resolves `/` against the source dir) and keeps
  the traversal/backslash jail; tests cover canonical staging and a full
  offline Sphinx build with media.
- **Gates:** backend 141 passed / 48 skipped locally (live tests run in CI
  against PG18/Redis); ruff/format/mypy clean; frontend typecheck, lint,
  format, 19 tests, production build clean.

## Out of scope

Server move/first-run provisioning, scheduled backups, off-site
destinations, distribution, page aliases, M5, and SEO. A Full backup is
an input to a server move, not the move itself.
