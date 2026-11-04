# 2026-11-04 — Server move, first-run provisioning, and built-in TLS (0040)

Owner rulings Q-SM-A…E and Q-SM-G…M were accepted as recommended;
revised Q-SM-F (F-A1…F-L1) and ownership ruling O1 were accepted. This
tranche makes a fresh host usable without developer intervention, adds a
supported maintenance-window move that preserves public names and
numbered `/b/{n}/` URLs, and makes Scriptorium terminate HTTPS itself.

## Decisions

- Decision 0040 records the first-run/move rulings and the built-in TLS
  contract. Binding details live there; this changelog is the change
  summary.
- `scriptorium-admin` gains `setup`, `migrate`, `user create/list`,
  `backup export`, `restore`, `verify`, and the full `tls` lifecycle.
- CLI access is limited to root or the `scriptorium` service user.
- Move restore is strict on public names; the API restore keeps 0039
  auto-suffix. `--force` bypasses only the empty-target guard.
- Every Scriptorium-managed path is `scriptorium:scriptorium` except
  systemd/package metadata (root), external PostgreSQL data (`postgres`),
  and `ca.key` (`root:root 0600`).

## Backend — shared configuration

- New `app/config.py`: one no-shell-evaluation loader for
  `/etc/scriptorium/config.env`; `KEY=VALUE`, comments/blank lines,
  matching quotes, malformed lines fail loud. A real environment
  variable wins, including an empty one; the cache self-invalidates on
  mtime/size.
- Migrated existing env readers in `db.py`, `auth.py`,
  `routers/auth.py`, `limiter.py`, `media.py`, `backup/manifest.py`,
  `sphinx/runner.py`, `worker/celery_app.py`, `routers/backups.py`, and
  `routers/builds.py`. CLI and services now see the same database,
  secret, roots, and TLS paths.

## Backend — CLI first run and move

- `setup`: read-only preflight for config, `SECRET_KEY`, PostgreSQL 18,
  Alembic head/pending, artifact/media/build/backup roots, build Python,
  and TLS; prints next steps and exits non-zero when not ready.
- `migrate`: explicit idempotent Alembic upgrade; refuses PG < 18.
- `user create`/`user list`: TTY prompt or `--password-stdin` (never
  argv); 12–1024 characters, no composition rules, Argon2id; list prints
  id/email/display only. No open registration.
- `backup export`: resolves an Athenaeum by UUID or current public name,
  uses the 0039 export core, supports `editorial|full` and `zip|tar.gz`,
  and needs no web/worker/Redis/Celery.
- `restore`: requires an existing importer, applies the empty-target
  guard, and passes `strict_names=True`; warnings/errors are printed
  with the new Athenaeum identity.
- `verify`: read-only checks for config/`SECRET_KEY`, PG18/Alembic head,
  every Athenaeum's current `public_names` row, `latest`/`stable`
  pointers, artifact directories/manifests/jail, media file size and
  SHA-256, and TLS. Warnings do not fail; errors do.
- `app/backup/restore.py` gained `strict_names`:
  - before staging any file, every current/alias name is checked with
    the same claimability rules as the API;
  - a live name or another owner's tombstone raises `BackupError`
    instead of suffixing/skipping;
  - free or same-user-tombstoned names remain claimable;
  - the API path is unchanged.

## Backend — built-in TLS

- New `app/tls/`:
  - `state.py` — TLS root paths, `state.json`, per-version `meta.json`,
    atomic writes, HSTS defaults;
  - `crypto.py` — local CA/leaf generation, SAN normalization/detection,
    import validation, hardened `create_server_context`;
  - `manager.py` — generate/renew/import/rollback/prune/history/status/
    verify/HSTS, atomic activation, graceful reload with rollback;
  - `worker.py` — `TlsUvicornWorker`, requiring `--certfile`/`--keyfile`,
    disabling proxy headers, installing the hardened context;
  - `redirect.py` — HTTP→HTTPS `308` ASGI app;
  - `middleware.py` — HSTS middleware with an mtime-cached state read.
- Generated profile: ECDSA P-384 CA (SHA-384, 10 years, path length 0,
  root-only key) + ECDSA P-256 leaf (SHA-256, 90 days, `serverAuth`,
  DNS/IP SANs). Leaf keys `0600`, fullchains `0644`, version dirs `0750`.
- TLS 1.2 minimum + TLS 1.3; TLS 1.2 is ECDHE+AEAD only (AES-256-GCM,
  ChaCha20-Poly1305, AES-128-GCM, ECDSA/RSA variants for imported RSA
  certificates); no CBC/RSA-kex/3DES/RC4/NULL, compression,
  renegotiation, or tickets; SHA-256+ signatures.
- Import validates PEM, dates, key strength/match, signature hash,
  `serverAuth` EKU, SAN presence, and chain links; installs atomically
  and rolls back on a failed live reload. Imported certificates never
  auto-renew.
- Daily renewal timer; renew at ≤30 days remaining; keep the newest 5
  versions while protecting the active one; history/rollback/prune;
  HSTS off by default with no preload.
- Version IDs use UTC microseconds + 8 random hex characters, so
  ordering is deterministic.
- `scriptorium-web` serves HTTPS on `SC_TLS_BIND` (default
  `0.0.0.0:443`); `scriptorium-redirect` serves HTTP on
  `SC_HTTP_HOST:SC_HTTP_PORT` (default `0.0.0.0:80`) and returns `308`.
  The redirect honors `Host` only when it matches a certificate SAN;
  otherwise `SC_TLS_REDIRECT_HOST`, a certificate SAN, or `400`.
- `app/main.py` wires the HSTS middleware.

## Packaging and services

- `scriptorium-web.service`: `TlsUvicornWorker`, certificate/key paths,
  `CAP_NET_BIND_SERVICE`, graceful `ExecReload`, read-only
  `/opt/scriptorium` and `/etc/scriptorium`, writable data/log/cache.
- `scriptorium-worker.service`: sandboxed with read-only code/config.
- New `scriptorium-redirect.service` (port 80, `app.tls.redirect:app`,
  `--no-proxy-headers`, `CAP_NET_BIND_SERVICE`).
- New `scriptorium-tls-renew.service` + daily `.timer`; renewal runs as
  root because the CA key is root-only.
- `config.env.example` gains `SC_TLS_BIND`, `SC_HTTP_HOST`,
  `SC_HTTP_PORT`, `SC_TLS_ROOT`, optional cert/key/redirect-host/HSTS
  keys.
- `postinst` creates the `scriptorium` group/user and TLS directories,
  applies `scriptorium:scriptorium` recursively, seeds `config.env`
  `0600`, forces `ca.key` to `root:root 0600`, verifies bundled runtimes,
  reloads systemd, and enables the renewal timer. It never migrates or
  generates certificates.
- `prerm` stops/disables the units without touching data or the DB.
- `nfpm.yaml` installs the new units and the `tls.md`, `server-move.md`,
  and `install.md` docs under `/usr/share/doc/scriptorium/`.
- Packaging CI contract checks the new units, config keys, docs, and
  lock pins.

## Dependencies

- Added `cryptography==50.0.2` and `uvicorn-worker==0.4.0`; regenerated
  `backend/requirements.lock` and `backend/requirements.prod.lock`.
- Added the local mypy stub
  `backend/typings/uvicorn_worker/__init__.pyi` and
  `mypy_path = "typings"` because the package ships no `py.typed`.
- No new OS package: the bundled Python runtime supplies both.

## Docs

- Decision 0040; approved/implemented `roadmap/server-move-plan.md`;
  `operations/tls.md`; `operations/server-move.md`; rewritten
  `operations/install.md`.
- Updated architecture overview, threat model, compatibility matrix,
  onboarding getting-started/codebase-map/common-tasks, structure
  layout, roadmap phases, docs index, and this changelog.
- New `docs/history/` with `README.md`, `PROJECT-HISTORY.md`, and
  `ENVIRONMENT-MIGRATION.md`: project-wide timeline/decision/capability
  ledgers, non-regression contracts, and a new-machine handoff.
- Brain files updated for the new phase, decisions, tests, and next
  steps.

## Tests and gates

- New regressions: `tests/test_config.py` (file precedence, malformed
  input, cache invalidation, typed getters), `tests/test_tls.py`
  (generation/validation/SANs/context/renew/rollback/prune/import/HSTS/
  reload rollback), `tests/test_tls_redirect.py` (308/Host fallback/
  HSTS), `tests/test_cli.py` (parser/validation/user creation/export/
  restore/strict names; live tests in CI), and TLS assertions in
  `tests/test_packaging.py`.
- Fixed a test-order bug found by the full local run: a config test used
  `get_setting("SECRET_KEY")`, which was bypassed by the dummy
  `SECRET_KEY` set at import time in `test_auth_api.py`; it now tests
  `load_config()` directly.
- The first CI run found a second test-isolation defect: live CLI tests
  set `SC_BUILD_DISPATCH`/`SC_BACKUP_DISPATCH`/`SC_*_ROOT` directly in
  `os.environ`, and CI's ambient `DATABASE_URL` leaked into config tests.
  The CLI tests now use `monkeypatch.setenv` (auto-restored), and the
  file-parsing config tests clear the specific ambient keys they assert.
- Local gates at implementation: backend **169 passed, 51 skipped**
  (`-W error`; live PG18/Redis unavailable), ruff check/format clean,
  mypy strict clean; packaging contract **12 passed**; frontend
  typecheck/lint/format/19 Vitest tests/build pass and
  `npm audit --audit-level=high` passes (moderate-only advisories);
  docs validator passes; `pip-audit --strict` reports no known
  vulnerabilities.
- Live CLI/backup tests run in CI against PostgreSQL 18.6 and Redis.
- Closeout push and CI ×3 verification are recorded in
  `docs/brain/HANDOFF.md`; do not treat local skips as live coverage.

## Known limits (unchanged or newly explicit)

- No ACME/Let's Encrypt, reverse-proxy termination, HSTS preload, or
  automatic renewal of imported certificates.
- A generated CA that is lost must be replaced and re-trusted unless its
  key was backed up as a root secret.
- Local live PG18/Redis remains unavailable in this development
  environment; live tests are CI-only here.
- TypeScript ESLint remains blocked by the `typescript-eslint` TS <6.1
  peer range; `tsc --noEmit` is the type gate.
- Page aliases, M5, distribution, and the dedicated SEO phase remain
  later; SEO still requires its own plan and owner rulings.
