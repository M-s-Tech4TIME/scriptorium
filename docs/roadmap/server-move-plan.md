# Server move + first-run provisioning — approved plan

Last updated: 2026-11-04 / Ref: decision 0040; implemented and gated

Status: **approved and implemented.** Owner rulings Q-SM-A…E and
Q-SM-G…M were accepted as recommended; Q-SM-F was approved in its revised
built-in-TLS form (F-A1…F-L1); ownership ruling O1 was accepted. The
binding record is `docs/decisions/0040-server-move-first-run.md`. The
operator runbooks are `docs/operations/server-move.md` and
`docs/operations/tls.md`.

## Goal

A fresh host can be installed, configured, migrated, seeded with its first
account, and made usable without developer intervention. An existing
Athenaeum can then be moved to that host with its public name and numbered
`/b/{n}/` URLs preserved, its media and artifacts served, and a tested
rollback path.

## Approved scope

In scope:

- first-run preflight, migration sequencing, and first-account creation;
- a CLI path for server-move export/restore that reuses the 0039 core;
- a server-move runbook: freeze, export, transfer, provision, restore,
  verify, DNS cutover, rollback, decommission;
- built-in TLS termination, certificate lifecycle, import, renewal,
  rollback, HSTS, and a local CA;
- post-move verification and empty-target safety checks;
- shared config loading so the CLI and services see the same settings.

Out of scope (unchanged):

- signed packages, SBOM/provenance, lintian/rpmlint, clean-install matrix
  (M5);
- scheduled/off-site backups, retention, archive encryption as a format
  feature;
- zero-downtime migration, live replication, dual-write, or in-app
  maintenance mode;
- page aliases, M5, distribution, and the dedicated SEO phase;
- migrating users, memberships, refresh tokens, or audit rows through the
  supported archive path (raw dump is the ops-only fallback);
- whole-instance backup as one archive;
- reverse-proxy termination, ACME, or HSTS preload.

## Final first-run flow

1. **Host prep.** Install PG 18 (external; 0001/0004) and the package.
2. **Configure.** Edit `/etc/scriptorium/config.env` (0600
   `scriptorium:scriptorium`): `DATABASE_URL`, a fresh `SECRET_KEY`,
   `SCRIPTORIUM_COOKIE_SECURE=true`, Redis URLs, `SC_*` roots, and the
   TLS bind/root keys.
3. **TLS.** `sudo scriptorium-admin tls generate --hostname <public-host>`
   or `tls import --cert fullchain.pem --key privkey.pem`; then
   `tls verify`.
4. **Preflight.** `sudo scriptorium-admin setup` — read-only checks for
   config, `SECRET_KEY`, PG18, Alembic head/pending, roots, build Python,
   and TLS, plus next steps.
5. **Schema.** `sudo scriptorium-admin migrate` (explicit, idempotent,
   PG18-only).
6. **First account.** `sudo scriptorium-admin user create --email … \
   --display …`; TTY prompt or `--password-stdin`; 12–1024 characters,
   Argon2id, no open registration.
7. **Start.** `systemctl enable --now scriptorium-redis
   scriptorium-redirect scriptorium-web scriptorium-worker` and the
   renewal timer; verify HTTPS and the HTTP `308`.
8. **Content.** Log in and create an Athenaeum, or restore a move archive
   before opening the site.

## Final server-move flow

1. **Preflight (old host).** Confirm package/archive version, free disk,
   a recent PG backup, and lower DNS TTL at least 24 h ahead.
2. **Freeze writes.** Stop `scriptorium-web` and `scriptorium-worker`; keep
   PG and Redis running for the export.
3. **Export.** `scriptorium-admin backup export --athenaeum … --mode full
   --format zip|tar.gz --output …`; record SHA-256 and size. The CLI needs
   no web/worker/Redis/Celery and shares the 0039 core.
4. **Transfer.** SSH/HTTPS only; verify SHA-256 on the new host; store
   `0600` under `/var/lib/scriptorium/backups/incoming/`.
5. **Provision.** Complete first-run through `migrate` and `user create`;
   generate a **new** `SECRET_KEY`; choose generated, imported, or reused
   local-CA TLS (reuse requires secure `ca.key` transfer).
6. **Restore.** With web/worker stopped, run `scriptorium-admin restore
   --archive … --owner-email …`. It refuses a non-empty target unless
   `--force` (which does not relax name strictness) and strict-fails on
   public-name conflicts.
7. **Verify.** `scriptorium-admin verify` + `tls verify` + the manual
   checklist: login, public names, aliases, `/b/{n}/`, `latest`/`stable`,
   media, custom CSS, private access, search, manifests, counts.
8. **Cut over.** Start services, point DNS at the new host, monitor.
9. **Rollback.** Point DNS back to the untouched old host; writes on the
   new host after cutover are lost; record the window.
10. **Decommission.** After the agreed window, destroy the old host and
    temporary archive copies.

For a multi-Athenaeum instance, repeat export/restore once per Athenaeum.
The importer owns every restored site; memberships are re-granted through
the existing API. Former owners become members or are recreated as users.
There is no owner-transfer endpoint.

## Final CLI surface

```text
scriptorium-admin setup
scriptorium-admin migrate
scriptorium-admin verify
scriptorium-admin user create --email EMAIL --display NAME [--password-stdin]
scriptorium-admin user list
scriptorium-admin backup export --athenaeum UUID|PUBLIC_SLUG \
    --mode editorial|full --format zip|tar.gz --output PATH
scriptorium-admin restore --archive PATH --owner-email EMAIL [--force]
scriptorium-admin tls generate [--hostname H] [--url U] [--san S] [--no-reload]
scriptorium-admin tls renew [--force] [--no-reload]
scriptorium-admin tls import --cert PEM --key PEM [--no-reload]
scriptorium-admin tls rollback [VERSION] [--no-reload]
scriptorium-admin tls prune [--keep N]
scriptorium-admin tls history [--json]
scriptorium-admin tls status [--json]
scriptorium-admin tls verify [--json]
scriptorium-admin tls hsts on|off [--max-age N]
scriptorium-admin tls ca [--export PATH]
```

The CLI runs only as root or `scriptorium`; `setup`/`verify` are read-only;
`migrate` refuses PG < 18. The config file is parsed without shell
evaluation, and a real environment variable wins.

## Final TLS contract

- **Termination:** Gunicorn/Uvicorn on 443 with `TlsUvicornWorker`; a
  separate HTTP listener on 80 returns `308`. No plaintext app listener.
- **CA/leaf:** local ECDSA P-384 CA (10 years, root-only key) + ECDSA
  P-256 leaf (90 days, serverAuth, DNS/IP SANs). Trust the CA once.
- **Binds:** `0.0.0.0:443` / `0.0.0.0:80` defaults via
  `CAP_NET_BIND_SERVICE`; configurable, IPv4 default, IPv6 configurable.
- **Renewal:** daily timer; at 30 days remaining; keep the last 5 versions;
  history/rollback/prune; imported certificates never auto-renew.
- **Ciphers:** TLS 1.2 minimum + TLS 1.3; TLS 1.2 is ECDHE+AEAD only; no
  CBC/RSA-kex/3DES/RC4/NULL, compression, renegotiation, or tickets;
  SHA-256+.
- **Import:** PEM fullchain + unencrypted key; dates/strength/match/hash/
  EKU/SAN/chain validation; atomic install; graceful reload; automatic
  rollback on failure.
- **HSTS:** off by default; enable after CA trust; no preload.
- **Redirect safety:** `Host` is honored only when it matches a current
  certificate SAN; otherwise `SC_TLS_REDIRECT_HOST` or a certificate SAN,
  otherwise `400`.
- **Proxy posture:** `X-Forwarded-For` is untrusted; Uvicorn proxy headers
  are disabled.

## Security and integrity notes

- **Config parity:** one loader for CLI and services; no `source`
  semantics; malformed lines fail loud.
- **Archive handling:** treat archives as secrets; `0600`; SSH/HTTPS
  transfer; verify SHA-256; delete temporary copies.
- **Restore jail:** reuse 0039 validation-before-write, fresh UUIDs,
  artifact/media root jails, and cleanup-on-failure. There is no second
  restore implementation.
- **Name integrity:** CLI move is strict (I1); API owner restore keeps
  0039 E1 auto-suffix. `--force` only bypasses the empty-target guard.
- **Version skew:** new host runs the same or newer package; migrate before
  restore; downgrades unsupported.
- **Ownership:** all app paths `scriptorium:scriptorium`; exceptions are
  systemd/package metadata (root), external PG data (`postgres`), and
  `ca.key` (`root:root 0600`).

## Implementation map

| Area | Files |
|---|---|
| Shared config | `backend/app/config.py`; migrated readers across `app/` |
| CLI | `backend/app/cli.py` |
| TLS | `backend/app/tls/{state,crypto,manager,worker,redirect,middleware}.py` |
| HSTS wiring | `backend/app/main.py` |
| Strict move restore | `backend/app/backup/restore.py` (`strict_names`) |
| Packaging | `packaging/systemd/scriptorium-{web,worker,redirect,tls-renew}.service`, `scriptorium-tls-renew.timer`, `scripts/postinst.sh`, `scripts/prerm.sh`, `config.env.example`, `nfpm.yaml` |
| Dependencies | `backend/pyproject.toml`, both lockfiles, `backend/typings/uvicorn_worker/__init__.pyi` |
| Tests | `backend/tests/test_config.py`, `test_tls.py`, `test_tls_redirect.py`, `test_cli.py`, `test_packaging.py` |
| Docs | decision 0040, `operations/tls.md`, `operations/server-move.md`, install/threat/compatibility/architecture/onboarding, changelog, history, brain |

## Acceptance evidence

- A clean host reaches first login using only documented commands.
- A Full archive restores into an empty target with the same current public
  name, aliases, numbered `/b/{n}/` URLs, `latest`/`stable` pointers,
  media, custom CSS, and private/public state.
- The move runbook has a tested rollback that does not require touching the
  old host after the freeze.
- TLS generation/import/renew/rollback/prune/HSTS/redirect behaviours are
  regression-tested; the hardened context is test-pinned.
- No 0039 API/archive behaviour regresses; API restore keeps auto-suffix,
  CLI move uses strict names.
- Final gates and CI are recorded in the changelog and brain closeout.

## Open items (not blockers)

- Live PG18/Redis is unavailable in the current development environment;
  the live CLI/backup tests run in CI.
- TypeScript ESLint remains blocked by `typescript-eslint`'s TS `<6.1`
  peer range; `tsc --noEmit` is the type gate.
- Page aliases, M5, distribution, and the dedicated SEO phase remain later
  phases; SEO still requires its own plan and owner rulings.
