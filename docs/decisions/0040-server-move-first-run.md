# 0040 — Server move, first-run provisioning, and built-in TLS

- **Status:** accepted — owner rulings 2026-11-03; implemented 2026-11-04
- **Owner rulings:** Q-SM-A…E and Q-SM-G…M as recommended; revised
  Q-SM-F (F-A1…F-L1); ownership ruling O1.
- **Scope:** first-run preflight/migration/first account, headless
  server-move export/restore/verify, shared CLI configuration, built-in
  TLS termination and lifecycle, packaging and service contract. Page
  aliases, M5, distribution, and SEO remain separate phases.

## Why

A fresh host could not log in: `scriptorium-admin` only had `setup` and
`migrate`, and there was no supported way to create the first account.
The CLI also did not see the full `/etc/scriptorium/config.env` that
systemd uses, so a manual move could diverge from the services. The
approved requirement is a documented, tested first-run path and a
maintenance-window move that preserves public names and numbered
`/b/{n}/` URLs. The owner also ruled that V1 terminates TLS itself rather
than depending on an external reverse proxy.

## First-run rulings (A–E, G–M)

| ID | Ruling |
|---|---|
| Q-SM-A | **A1:** CLI `scriptorium-admin user create --email --display`, password via TTY prompt or `--password-stdin`; no open registration, no environment secret bootstrap. |
| Q-SM-B | **B1:** `user create` + `user list` only; passwords 12–1024 characters, no composition rules; memberships re-granted through the existing API. |
| Q-SM-C | **C1:** content-only move per Athenaeum; users/memberships/refresh tokens/audit are never exported; the importer owns the restored site; global tombstones for deleted Athenaeums are not carried; raw `pg_dump` + filesystem copy is the documented ops-only full-fidelity fallback. |
| Q-SM-D | **D2:** CLI `backup export` + `restore` alongside the existing API, sharing the 0039 core; headless, no proxy upload limit, no Redis/Celery dependency. |
| Q-SM-E | **E1:** read-only `setup` preflight (config, `SECRET_KEY`, PG18, Alembic head, roots, build Python, TLS) plus next steps; never mutates state. |
| Q-SM-G | **G1:** maintenance-window cutover; stop old web/worker, export, restore, verify, DNS switch; keep the old host for rollback. |
| Q-SM-H | **H1:** generate a new `SECRET_KEY` on the new host; sessions re-authenticate; no secret transfer. |
| Q-SM-I | **I1:** CLI move restore strict-fails on any public-name conflict; the API owner restore keeps 0039 E1 auto-suffix behaviour. |
| Q-SM-J | **J2:** read-only `scriptorium-admin verify` (DB head, names/pointers, artifact manifests/jail, media hashes, TLS) plus the manual checklist. |
| Q-SM-K | **K1:** restore refuses when any Athenaeum exists unless `--force`; `--force` bypasses only the empty-target guard, never name strictness. |
| Q-SM-L | **L1:** implement first-run/move now on current packages; M5 later adds signing/provenance/clean-install and the admin guide. |
| Q-SM-M | **M1:** one shared config loader for `/etc/scriptorium/config.env`, environment wins, no shell evaluation; CLI and services see the same database, secret, roots, and TLS paths. |

## Built-in TLS rulings (Q-SM-F, revised)

| ID | Ruling |
|---|---|
| F-A1 | The app terminates HTTPS natively in Gunicorn/Uvicorn on 443, plus a built-in HTTP→HTTPS `308` listener on 80. No reverse proxy is required and there is no plaintext application listener. |
| F-B1 | Local Scriptorium CA (ECDSA P-384, 10 years, root-only key) plus leaf (ECDSA P-256, 90 days). Trust the CA once; leaf renewal is seamless. |
| F-C1 | Default binds 443/80 via `CAP_NET_BIND_SERVICE`; binds are configurable; IPv4 is the default and IPv6 is configurable. |
| F-D1 | Daily renewal timer; renew at 30 days remaining; keep the last 5 versions with history/rollback/prune; imported certificates are never auto-renewed. |
| F-E1 | TLS 1.2 minimum + TLS 1.3; TLS 1.2 is ECDHE + AEAD only (AES-256-GCM, ChaCha20-Poly1305, AES-128-GCM); no CBC/RSA-kex/3DES/RC4/NULL; SHA-256+; no compression, renegotiation, or session tickets. |
| F-F1 | PEM `fullchain.pem` + `privkey.pem` import with full validation, atomic install, graceful reload, live fingerprint check, and automatic rollback on failure. |
| F-G1 | HSTS off by default; enable with `tls hsts` after CA trust; no preload. |
| F-H1 | Add `cryptography==50.0.2` and `uvicorn-worker==0.4.0`; regenerate both locks; no new OS package. |
| F-I1 | Every app path is `scriptorium:scriptorium`; services are sandboxed with read-only code/config; the CLI runs only as root or `scriptorium`. |
| F-J1 | Full TLS CLI lifecycle: generate, renew, import, rollback, prune, history, status, verify, hsts, ca. |
| F-K1 | Auto-detect SANs plus `--hostname`/`--url`/`--san` overrides; IDNA/IPv6/wildcard normalization. |
| F-L1 | Built-in TLS is the only V1 listener contract; no external plaintext termination; `X-Forwarded-For` remains untrusted; Uvicorn proxy headers are disabled. |

## Ownership ruling (O1)

Every Scriptorium-managed file and directory is owned by
`scriptorium:scriptorium`. Accepted exceptions:

- systemd unit files and package metadata remain root-owned;
- the external PostgreSQL data directory remains `postgres`-owned;
- the local CA private key is `root:root 0600`.

`postinst` applies the recursive ownership and then restores the CA key's
root ownership/mode. Services run as `scriptorium` under
`ProtectSystem=strict`, with `/opt/scriptorium` and `/etc/scriptorium`
read-only and only data/log/cache paths writable.

## Implementation

### Shared configuration (M1)

`backend/app/config.py` parses the systemd-style `KEY=VALUE` file with
optional matching quotes, ignores blank lines/comments, rejects malformed
lines, and does no shell evaluation. A present environment variable wins,
including an empty one (so `SECRET_KEY=` fails loud). The file cache is
invalidated by mtime/size. Existing environment readers in `db.py`,
`auth.py`, `routers/auth.py`, `limiter.py`, `media.py`,
`backup/manifest.py`, `sphinx/runner.py`, `worker/celery_app.py`,
`routers/backups.py`, and `routers/builds.py` were migrated to it.

### CLI

`backend/app/cli.py` now provides:

```text
setup
migrate
verify
user create --email EMAIL --display NAME [--password-stdin]
user list
backup export --athenaeum UUID|PUBLIC_SLUG --mode editorial|full
              --format zip|tar.gz --output PATH
restore --archive PATH --owner-email EMAIL [--force]
tls generate|renew|import|rollback|prune|history|status|verify|hsts|ca
```

- The CLI refuses to run as any account other than root or the
  `scriptorium` service user (F-I1).
- `setup` and `verify` are read-only; `migrate` refuses PG < 18.
- `restore` requires an existing importer, applies the K1 empty-target
  guard, and passes `strict_names=True` to the 0039 restore core.
- `backup export` resolves an Athenaeum by UUID or current public name and
  uses the same export core as the API.
- `verify` checks the database, names/pointers, artifacts/manifests/jail,
  media size/SHA-256, config, and TLS findings.
- TLS commands are thin wrappers over `app.tls`; `--no-reload` is for
  offline/staging use.

### TLS core

`backend/app/tls/`:

- `state.py` — paths, state/metadata, atomic writes, HSTS defaults;
- `crypto.py` — CA/leaf generation, SAN normalization, validation, and the
  hardened server context;
- `manager.py` — generate/renew/import/rollback/prune/history/status/
  verify/HSTS, atomic activation, reload with automatic rollback;
- `worker.py` — `TlsUvicornWorker`, which requires `--certfile`/
  `--keyfile`, disables proxy headers, and installs the hardened context;
- `redirect.py` — the HTTP→HTTPS `308` ASGI app with Host/SAN checking;
- `middleware.py` — HSTS response middleware with an mtime-cached state
  read.

Version IDs include UTC microseconds plus 8 random hex characters, so
history ordering is deterministic. Activation writes a complete version
directory, validates it, swaps the `current` symlink and state, then
gracefully reloads; a failed reload restores the previous symlink and
state. `prune` protects the active version and the newest `keep` versions.
Generated renewal reuses the active certificate's SANs and the same CA.

### Strict-name restore

The 0039 restore core gained `strict_names`:

- before staging any file, every current/alias name is checked with the
  same claimability rules as the API;
- a conflict raises `BackupError` instead of suffixing or skipping;
- the API path keeps its approved auto-suffix/skip behaviour;
- `--force` only bypasses the CLI's non-empty-target guard.

### Packaging

- `scriptorium-web.service`: `TlsUvicornWorker`, 443 bind, cert/key paths,
  `CAP_NET_BIND_SERVICE`, graceful `ExecReload`, read-only code/config,
  writable data/log/cache.
- `scriptorium-worker.service`: sandboxed with read-only code/config.
- New `scriptorium-redirect.service` (port 80, `app.tls.redirect:app`,
  no proxy headers).
- New `scriptorium-tls-renew.service` + daily `.timer`; renewal runs as
  root because the CA key is root-only.
- `config.env.example` gains TLS keys; `postinst` creates the group/TLS
  directories, applies `scriptorium:scriptorium`, seeds config as
  `0600 scriptorium:scriptorium`, forces `ca.key` to `root:root 0600`,
  verifies runtimes, and enables the renewal timer; `prerm` stops/disables
  units without touching data or the DB.
- `nfpm.yaml` installs the new units and the `tls.md`/`server-move.md`/
  `install.md` docs under `/usr/share/doc/scriptorium/`.
- `cryptography==50.0.2` and `uvicorn-worker==0.4.0` were added and both
  locks regenerated. A tiny local mypy stub covers `uvicorn_worker`
  because the package ships no `py.typed`.

## Security properties

- No plaintext application listener; HTTP only redirects.
- TLS 1.2/1.3 with ECDHE+AEAD; no CBC/RSA-kex/3DES/RC4/NULL, compression,
  renegotiation, or tickets.
- The CA key is root-only; leaf keys are `0600`; fullchains `0644`.
- Imported chains are fully validated for dates, key strength/match,
  signature hash, EKU, SANs, and chain links before atomic installation.
- The redirect listener never reflects an arbitrary `Host`; it uses the
  Host only when it matches a certificate SAN, otherwise a configured
  canonical host or a certificate SAN, otherwise `400`.
- HSTS is opt-in after trust; no preload.
- CLI access is limited to root/`scriptorium`; archives and Full
  downloads remain 0039-hardened.
- `X-Forwarded-For` is untrusted and Uvicorn proxy headers are disabled.

## Tests and gates

- New regressions: `backend/tests/test_config.py` (file precedence,
  malformed input, cache invalidation, typed getters),
  `test_tls.py` (generation/validation/SANs/context/renew/rollback/prune/
  import/HSTS/reload rollback), `test_tls_redirect.py` (308/Host fallback/
  HSTS), `test_cli.py` (parser/validation/user creation/export/restore/
  strict names; live tests in CI), and TLS assertions in
  `test_packaging.py`.
- Live-DB CLI tests run in CI against PG18/Redis; local Docker/PG/Redis is
  unavailable in the development environment.
- Final gates: backend pytest `-W error`, ruff check/format, mypy strict,
  frontend typecheck/lint/format/Vitest/build/audit, docs validator,
  packaging contract, `pip-audit`, CI ×3 green after push.

## Disclosed micro-defaults

- Password policy is length-only (12–1024), per B1; no composition or
  breach-list check.
- `user list` prints id/email/display, never hashes.
- CLI `restore` writes the 0039 audit action with the importer as actor;
  it does not create a `BackupJob`.
- `verify` warnings do not fail the command; errors do.
- `tls status` warns inside the 30-day renewal window.
- HSTS default max-age is one year; `--max-age`/`SC_TLS_HSTS_MAX_AGE`
  override it; non-positive values are rejected.
- `tls prune` protects the active version even when it is older than the
  newest `--keep` versions.
- Imported certificates are validated but their external root is not
  added to the system trust store.
- Reusing the old local CA across a move is an operator choice requiring
  secure transfer of `ca.key`; generating a new CA is the default
  recommendation.

## Out of scope

ACME/Let's Encrypt automation, reverse-proxy termination, HSTS preload,
automatic renewal of imported certificates, identity-bearing move
bundles, owner-transfer endpoints, zero-downtime migration, page aliases,
M5 signing/provenance/clean-install, distribution, and SEO. The dedicated
SEO phase still requires its own plan and owner rulings; no SEO
implementation is authorized by this decision.
