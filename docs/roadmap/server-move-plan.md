# Server move + first-run provisioning — plan (draft)

Last updated: 2026-11-03 / Ref: draft for owner review; Q-SM-A…M open

Status: **proposal only.** No implementation starts until the owner rules on
Q-SM-A…M (`docs/brain/OPEN-QUESTIONS.md`). This plan reuses the 0039 Full
backup format; it does not change the archive format unless Q-SM-C says so.

## Goal

A fresh host can be installed, configured, migrated, seeded with its first
account, and made usable without developer intervention. An existing
Athenaeum can then be moved to that host with its public name and numbered
`/b/{n}/` URLs preserved, its media and artifacts served, and a tested
rollback path.

## Scope

In scope (subject to rulings):

- first-run preflight, migration sequencing, and first-account creation;
- a CLI path for server-move export/restore that reuses the 0039 core;
- a server-move runbook: freeze, export, transfer, provision, restore,
  verify, DNS cutover, rollback, decommission;
- a supported TLS/reverse-proxy contract (examples, body-size/timeouts,
  forwarded-header trust);
- post-move verification and empty-target safety checks.

Out of scope:

- signed packages, SBOM/provenance, lintian/rpmlint, clean-install matrix
  (M5);
- scheduled/off-site backups, retention, archive encryption as a format
  feature (an operator may wrap the archive with `age`/GPG);
- zero-downtime migration, live replication, dual-write, or a maintenance
  mode inside the app;
- page aliases, M5, and the dedicated SEO phase;
- migrating users, memberships, refresh tokens, or audit rows, unless
  Q-SM-C chooses the identity-bearing or raw-dump path;
- whole-instance backup as one archive, unless Q-SM-C/Q-SM-D choose it.

## Current state and gaps

| Area | Today | Gap for first-run/move |
|---|---|---|
| Account bootstrap | `0018 Q-M3-1=A`: no open registration; users are "seeded by CLI" | `scriptorium-admin` only has `setup`/`migrate`; a fresh install cannot log in |
| Setup | `setup` checks DB reachability/version; `migrate` applies Alembic and refuses PG<18 | No preflight for `SECRET_KEY`, roots, build venv, pending migrations, or CLI config parity |
| Config | systemd uses `EnvironmentFile=/etc/scriptorium/config.env`; only `DATABASE_URL` is read from that file by app code | A manual `scriptorium-admin` run does not see `SC_*`/`SECRET_KEY` from the file |
| Restore | API `POST /backups/restore`; Full is a Celery job; requires an authenticated importer | Needs a running web/worker and an existing account; 8 GiB uploads depend on proxy limits |
| Move export | API Full export job with a 15-minute single-use download | Needs a running web/worker; no headless export if the web tier is down |
| Identities | 0039 D1: users, memberships, refresh tokens, audit never exported; importer owns the restored site | A multi-user move loses memberships and owner distinctions |
| Public-name registry | Per-Athenaeum backup carries that site's current name and aliases | Tombstones for **deleted** Athenaeums (`athenaeum_id NULL`) are not in any per-site archive |
| TLS/proxy | Web unit binds `127.0.0.1:8470`; docs say "behind HTTPS" | No supported proxy example, body-size/timeout guidance, or forwarded-header trust contract |
| Verification | 0039 validates archives before import | No post-move check that live rows, manifests, media hashes, and names still agree |
| Rollback | None documented | Old host must stay intact and DNS must be reversible |

## Proposed first-run flow (recommended)

1. **Host prep.** Install PG 18 (external; 0001/0004), the package, and a
   TLS-terminating reverse proxy. The package never manages PG or migrates.
2. **Configure.** Edit `/etc/scriptorium/config.env` (0600): `DATABASE_URL`,
   a fresh `SECRET_KEY`, `SCRIPTORIUM_COOKIE_SECURE=true`, Redis URLs, and
   the `SC_*` roots. Keep the app bound to loopback.
3. **Preflight.** `sudo -u scriptorium scriptorium-admin setup` performs
   read-only checks and prints the next steps (Q-SM-E).
4. **Schema.** `sudo -u scriptorium scriptorium-admin migrate` (explicit,
   idempotent, PG18-only).
5. **First account.** `sudo -u scriptorium scriptorium-admin user create
   --email owner@example.com --display "Owner"` prompts for the password
   twice; `--password-stdin` is the non-interactive form (Q-SM-A/B).
6. **Start.** `systemctl enable --now scriptorium-redis scriptorium-web
   scriptorium-worker`; verify `/api/v1/health`.
7. **Proxy/TLS.** Install the documented nginx/Caddy example, certificate,
   and forwarded-header/body-size settings (Q-SM-F).
8. **Content.** Log in and create an Athenaeum, or run the move restore
   (below) before opening the site.

## Proposed server-move flow (recommended)

1. **Preflight (old host).** Confirm the package/archive format version,
   free disk for the archive, and a recent PG backup. Lower DNS TTL at
   least 24 h ahead.
2. **Freeze writes.** Stop `scriptorium-web` and `scriptorium-worker` on
   the old host. Keep PG and Redis running for the export; no builds,
   uploads, or document saves can occur (Q-SM-G).
3. **Export.** Use the API Full export or the proposed CLI export; choose
   ZIP or `.tar.gz`; record `sha256` and size. Verify the archive opens
   and its manifest is valid.
4. **Transfer.** Download over HTTPS or copy with `scp`/rsync; verify the
   SHA-256 on the new host; store it `0600` under
   `/var/lib/scriptorium/backups/incoming/`.
5. **Provision the new host.** Run the first-run flow through `migrate`
   and `user create`. Generate a **new** `SECRET_KEY` (Q-SM-H); do not
   copy refresh tokens (none are exported).
6. **Restore.** With web/worker still stopped, run the proposed CLI
   restore as the importer (Q-SM-D). It must refuse a non-empty target
   unless forced (Q-SM-K) and strict-fail on public-name conflicts
   (Q-SM-I).
7. **Verify.** Run the proposed `scriptorium-admin verify` and the manual
   checklist: login, public names, aliases, `/b/{n}/`, `latest`/`stable`,
   media, custom CSS, private access, search, build manifests, counts
   (Q-SM-J).
8. **Cut over.** Start services, point DNS at the new host, and monitor.
   Keep the old host and its PG backup intact for rollback.
9. **Rollback.** If verification or early traffic fails, point DNS back
   to the old host; it was never modified after the freeze. Writes made on
   the new host after cutover are lost on rollback; document that window.
10. **Decommission.** After the agreed rollback window, destroy the old
    host and its temporary archive copies.

For a multi-Athenaeum instance, repeat steps 3 and 6 once per Athenaeum
(0039 archives are per-Athenaeum). The importer owns every restored site;
memberships are re-granted through the existing API unless Q-SM-C changes
the identity model. There is no owner-transfer endpoint, so former owners
become members (or are recreated as users) while ownership stays with the
importer.

## Proposed CLI surface (subject to rulings)

```text
scriptorium-admin setup
scriptorium-admin migrate
scriptorium-admin user create --email EMAIL --display NAME [--password-stdin]
scriptorium-admin user list [--json]
scriptorium-admin backup export --athenaeum UUID|PUBLIC_SLUG \
    --mode full --format zip|tar.gz --output PATH
scriptorium-admin restore --archive PATH --email IMPORTER [--force]
scriptorium-admin verify [--json]
```

Micro-defaults (owner-vetoable): emails are stripped/lowercased like login;
`--display` is required; passwords are never accepted as argv; the password
policy applies to CLI-created passwords (existing hashes are not
revalidated); `user list` shows id/email/display/created_at and never a
hash; CLI actions that have an importer write an audit row with that actor
(user creation has no actor); `restore` writes an audit row but does not
create a `BackupJob`; `verify` is read-only and exits non-zero on findings;
`--json` is for automation, human-readable output is the default. The CLI
export/restore/verify paths must not require Redis, Celery, or the web
tier, and `restore` refuses when Alembic is not at head.

## Security and integrity notes

- **Config parity:** the CLI must see the same `/etc/scriptorium/config.env`
  values as systemd, without shell evaluation and without overriding an
  explicit environment (Q-SM-M).
- **Archive handling:** treat the archive as a secret (it contains all
  content and media); `0600`, delete temporary copies after verification,
  and prefer `scp`/HTTPS over plaintext transfer. Optional external
  encryption is allowed; the format itself stays unchanged.
- **Proxy trust:** the proxy must overwrite `X-Forwarded-For`; the app must
  trust forwarded headers only from loopback. This keeps the login limiter
  per-client instead of collapsing every client to `127.0.0.1` (part of
  Q-SM-F).
- **Restore jail:** reuse 0039's validation-before-write, fresh UUIDs,
  artifact/media root jails, and cleanup-on-failure. The CLI must not add
  a second restore implementation.
- **Name integrity:** a move must preserve the current public name and
  numbered URLs exactly; auto-suffixing is acceptable for owner-facing
  restores but not for a move (Q-SM-I). Global tombstones need an explicit
  ruling (Q-SM-C).
- **Version skew:** the new host runs the same or a newer package; apply
  migrations before restore; downgrades are unsupported. An old host that
  predates `scriptorium-backup@1` needs the raw-dump path (Q-SM-C) or an
  intermediate upgrade.

## Owner rulings needed

Full options/trade-offs are in the question rows; recommendations are the
first option.

| ID | Question | Recommendation |
|---|---|---|
| Q-SM-A | First-run account bootstrap: CLI vs one-time web setup vs env bootstrap | A1: CLI `user create`, TTY prompt or `--password-stdin` |
| Q-SM-B | User-management scope and password policy | B1: `user create` + `user list`; min 12 chars, max 1024, no composition |
| Q-SM-C | Move fidelity: content-only per Athenaeum vs identity-bearing bundle vs raw `pg_dump`; global tombstones | C1: content-only, per Athenaeum; document the limitation; raw dump as an ops-only fallback |
| Q-SM-D | Move tooling: API only vs CLI export+restore vs CLI restore only | D2: add CLI export + restore alongside the existing API |
| Q-SM-E | `setup` behavior: preflight vs orchestrator vs current DB-only | E1: read-only preflight + next steps |
| Q-SM-F | TLS/reverse proxy: docs+examples vs bundled proxy vs app TLS | F1: docs + nginx/Caddy examples, loopback app, trusted forwarded headers |
| Q-SM-G | Cutover: maintenance window vs dual-run vs zero-downtime | G1: maintenance window; stop old web/worker; keep old host for rollback |
| Q-SM-H | `SECRET_KEY` on move: new vs reuse vs rotation | H1: generate a new key; sessions re-authenticate |
| Q-SM-I | Public-name conflicts on move: strict fail vs auto-suffix vs flag | I1: CLI move restore strict-fails; API restore keeps 0039 E1 auto-suffix |
| Q-SM-J | Post-move verification: manual vs CLI `verify` vs defer to M5 | J2: read-only `scriptorium-admin verify` + manual checklist |
| Q-SM-K | Empty-target guard: refuse unless `--force` vs additive vs strict empty | K1: refuse if any Athenaeum exists unless `--force` |
| Q-SM-L | Scope vs M5: now on current packages vs M5 first vs merge | L1: implement now; M5 later adds signing/provenance/clean-install and the admin guide |
| Q-SM-M | CLI config parity: shared file loader vs shell sourcing vs `--config` | M1: shared loader, env wins, no shell evaluation |

## Implementation plan (if approved)

1. **Backend/CLI**
   - Add a shared config-file loader (Q-SM-M) used by the CLI and by
     modules that currently read only `os.environ`.
   - Expand `setup` preflight (Q-SM-E): config file, `SECRET_KEY`, PG18,
     roots writable, build venv executable, Alembic head/pending.
   - Add `user create`/`user list` (Q-SM-A/B) with Argon2id, policy,
     normalization, duplicate/exit-code handling.
   - Add `backup export`/`restore`/`verify` (Q-SM-D/J/K/I) reusing
     `app.backup` core; no duplicate restore logic.
   - Add regression tests for parser/validation, config precedence, user
     creation, strict names, empty-target guard, export/restore round-trip,
     verify findings, and failure cleanup.
2. **Packaging**
   - Ship `nginx.conf.example` and `Caddyfile.example` under
     `/usr/share/doc/scriptorium/`; document body-size/timeouts/forwarded
     headers. No new runtime dependency.
   - Keep the web unit loopback-only; set/verify the forwarded-header trust
     setting.
3. **Docs**
   - Expand `docs/operations/install.md` into a first-run walkthrough.
   - Add `docs/operations/server-move.md` (the runbook above).
   - Add the proxy/TLS page or section.
   - Update API/data-model/overview/security/threat-model as needed.
   - Decision record `0040-server-move-first-run.md` after rulings;
     changelog; brain closeout.
4. **Gates**
   - Backend `pytest -W error`, ruff, format, mypy; frontend gates
     unchanged (no UI change expected); docs validation; packaging check;
     CI ×3 green after push.
   - Live-DB tests for CLI restore/verify run in CI (local PG/Redis absent).

## Acceptance

- A clean host can go from package install to first login using only
  documented commands.
- A Full archive from the old host restores into an empty target with the
  same current public name, aliases, `/b/{n}/` URLs, `latest`/`stable`
  pointers, media, custom CSS, and private/public state.
- The move runbook has a tested rollback that does not require touching
  the old host after the freeze.
- No 0039 behavior regresses; the API restore path and archive format
  remain compatible.

## Open questions

See Q-SM-A…M in `docs/brain/OPEN-QUESTIONS.md`. Implementation is blocked
until the owner rules.
