# Project history — Scriptorium from bootstrap to 2026-11-04

Last updated: 2026-11-04 / Ref: server-move/first-run + built-in TLS (0040)

This is the long-form, project-wide record. It complements, and never
replaces, the numbered decisions, changelogs, and the brain. When this
page and a decision disagree, the decision wins; when this page and the
code disagree, the code plus its tests win and this page is corrected.

## 1. What Scriptorium is

Scriptorium is a self-hosted documentation platform. An owner writes in a
browser WYSIWYG editor (TipTap), the server stores canonical TipTap JSON,
converts it to valid Sphinx source (RST by default, MyST opt-in), builds a
portable static site in an isolated Sphinx environment, and serves the
result at durable public URLs.

The product hierarchy is:

```text
user → Athenaeums (libraries) → categories (sections) → grimoires (books)
     → chapters/folios (tree nodes) → documents (TipTap JSON + history)
```

An Athenaeum is the publication and sharing unit. Each successful build
is an immutable numbered artifact; owners publish it to `latest` and/or
`stable`, and every ever-published build keeps its numbered URL.

V1 is deliberately bounded: images/GIF only (no video/audio/attachments),
no page-level path aliases yet, no distribution, no SEO implementation
until a dedicated plan and owner rulings, and no reverse proxy in the
built-in TLS contract.

## 2. Source-of-truth hierarchy

1. `docs/decisions/0001-*.md` … `0040-*.md` — binding owner rulings.
2. `docs/brain/DECISIONS-INDEX.md` — one-line index and status.
3. `docs/changelog/*.md` — what each tranche changed.
4. `docs/brain/CURRENT-STATE.md` + `HANDOFF.md` — live resume state.
5. `docs/technology/` + `docs/architecture/` — current technical contracts.
6. `docs/operations/` — install, TLS, server-move runbooks.
7. This history — narrative and migration context.

## 3. Timeline

| Date | Tranche | Decision(s) | Representative commits | Outcome |
|---|---|---|---|---|
| 2026-10-16 | M0 foundation | 0001–0011 | `9d82519`, `d21dbc8` | Monorepo, AGENTS/docs/brain, pins/locks, CI skeleton, nfpm skeleton, dev compose |
| 2026-10-16 | Repo bootstrap / re-root | 0012–0016 | `03f9466`, `deb5eb1`, `394405f` | Repo rooted at `scriptorium/`, proprietary NOTICE, public-for-CI, ff-only `main`/`dev`, authorship, Rule 7 |
| 2026-10-16 | M1 schema + auth | 0008/0009 | `5ba2fdd`, `2539391` | Migrations, Argon2id, JWT, RBAC, IDOR tests, audit |
| 2026-10-19/20 | M2 conversion + refresh store | 0017 | `ba153e9`, `d5fb5cc`, `be1a220` | TipTap↔RST/MyST round-trip, refresh-token families with reuse burn |
| 2026-10-20 | M3 auth API + rate limit | 0018/0019 | `d9640c8`, `f0092f6` | Login/refresh/logout, Redis fixed-window login limiting (fail-closed) |
| 2026-10-20/21 | M3 hierarchy + slugs | 0018/0020/0021/0022 | `4b57c82`, `9fe1280`, `ab688dc` | Athenaeums, categories, grimoires, members, renamable slugs, folio/chapter vocabulary |
| 2026-10-21 | M3 tree/documents/duplication | 0023/0024/0025 | `3fbe4f8`, `5d8d08f`, `5b5dee1` | Tree CRUD/reorder, document versioning/history/import, deep grimoire copy |
| 2026-10-21/24 | M4 build design → C4 | 0026 | `2aed3ef`, `3a15b52`, `c6c407d`, `1add6c8` | Per-Athenaeum numbered builds, deterministic sourcegen, sandboxed Sphinx/Celery, isolated build venv |
| 2026-10-22/24 | Theme | 0027–0034 | `52a2124`, `556bbce`, `b15446f`, `2680738` | Own from-scratch theme, design baseline, four feedback passes, Standing Rule 8 |
| 2026-10-25 | Serving | 0035 | `6169696` | Immutable numbered artifacts, `latest`/`stable`, private default, manifest CSP, custom CSS |
| 2026-10-28 | URL durability | 0036 | `be5af83` | Owner-renamable public names, permanent aliases/tombstones, `308` after auth |
| 2026-10-30 | Stack upgrade | 0037 | `9d645e3` | Python 3.14.10 bundled, Node 26.13.0 LTS, Sphinx 9.2.0, Redis 8.10.2, current pins |
| 2026-10-31 | Editor/content completion | 0038 | `476dfff` | V1 React app, TipTap surface, tree/history/import, image/GIF media, build media copy |
| 2026-11-01 | Backup/restore | 0039 | `31ac99d`, `55276ff` | Editorial/Full ZIP/`.tar.gz`, validated restore, numbered URL preservation, Full jobs |
| 2026-11-03 | Server-move plan | Q-SM-A…M | `6e53875` | Plan + questions only; no implementation before rulings |
| 2026-11-04 | Server move/first-run + built-in TLS | 0040 | this tranche | CLI first-run/move/verify, shared config, native HTTPS + redirect, local CA lifecycle, ownership/sandbox, runbooks |

Every tranche above was committed with docs/brain updates and, from
Rule 7 onward, verified green in all three CI workflows before the next
tranche stacked on it.

## 4. Decision ledger (0001–0040)

| ID | Binding content |
|---|---|
| 0001 | Section 8 packaging/distribution: monorepo, nfpm, systemd, FHS paths, explicit migrate, bundled runtimes, GPG, GitHub Releases first |
| 0002 | Distro baselines: Ubuntu 24.04, Debian 12, RHEL 9, Fedora, Leap 15.6 |
| 0003 | Rule 5 version set; docutils 0.23 gated by a manual probe |
| 0004 | PostgreSQL 18.x exclusive, LTS/proven principle |
| 0005 | FastAPI + Celery/Redis + filesystem/DB storage |
| 0006 | TypeScript 7.0.2 owner override |
| 0007 | Docs/brain/AGENTS foundation, Markdown-only |
| 0008 | Standards/gates: mypy, Conventional Commits, trunk, 5 CI gates |
| 0009 | Standing Rule 6: zero skipped warnings |
| 0010 | Architecture/data model/threat model: JSON canonical, generic tree |
| 0011 | Roadmap M0–M5 + Phase A/B |
| 0012 | Work under `scriptorium/` subdirectory |
| 0013 | ff-only release promotion; `main` and `dev` identical |
| 0014 | Proprietary license/NOTICE; public-for-CI; Tech4TIME attribution |
| 0015 | Standing Rule 7: CI-green after every push |
| 0016 | Authorship convention |
| 0017 | M2 design: refresh family store, starter kit, MyST markers |
| 0018 | M3 design: grimoire rename, per-user categories, auth/document/tree semantics |
| 0019 | Login rate limiting: in-app Redis fixed window, fail-closed, XFF untrusted |
| 0020 | Athenaeum native hierarchy; grimoire-level sharing; delete refusal |
| 0021 | Slugs renamable at every layer; uniform 409/422 |
| 0022 | Folio/chapter vocabulary; single membership; duplication ≠ membership |
| 0023 | Tree endpoints: delete refusal, owner-only, cycle guard, displacement reorder |
| 0024 | Folio documents: expected-version 409, version/history append, import 422 |
| 0025 | Grimoire duplication: caller slug, owner roster, head-as-v1, any owned target |
| 0026 | M4 build design: per-Athenaeum sites, manual trigger, subprocess sandbox, keep-all numbered builds; portable artifact + design mandates |
| 0027 | Own from-scratch theme, no parent theme, full engine inheritance/vendored JS |
| 0028 | Theme design baseline: tokens, Tabler sprite, callout palette, Pygments, copy script, zero extensions |
| 0029 | Theme preview feedback: anchors, search decoration, code chrome, pager, footer/credit, toc rail |
| 0030 | Vendored Inter typography; OFL; fallback stack |
| 0031 | Theme second feedback: fluid width, search dialog, chips, sticky panel, scrollspy |
| 0032 | Theme third feedback: unified first-party search, full-page takeover, link crawl, h2 staging fix |
| 0033 | Standing Rule 8: Regression Integrity / no collateral breakage |
| 0034 | Theme fourth feedback: panel placeholder, code label, pager containment, pre-paint panel state |
| 0035 | Serving: latest/stable pointers, private default, FastAPI artifacts, manifest CSP, custom CSS |
| 0036 | URL durability: renamable public name, aliases, tombstones, `308` after auth, no rebuild |
| 0037 | Stack upgrade: Python 3.14.10, Node 26.13.0, PG18.6, Redis 8.10.2, Sphinx 9.2.0, current pins |
| 0038 | Editor/content completion: React app, image/GIF media, history restore, single-file import |
| 0039 | Backup/restore: Editorial/Full, ZIP/`.tar.gz`, validated restore, importer-owned, numbered URLs preserved |
| 0040 | Server move/first-run + built-in TLS: CLI lifecycle, strict names, local CA, native HTTPS, HTTP 308, ownership O1 |

## 5. Capability ledger

### Identity and tenancy
- Argon2id passwords; short-lived JWT access tokens; rotating refresh
  cookie with family reuse detection; login lockout/rate limiting.
- Owner/member checks on every API request; outsiders receive uniform
  `404`; audit rows record sensitive actions.
- No open registration. The first account is created by a privileged CLI
  command (0040 A1/B1). Passwords are 12–1024 characters, never argv.

### Content model and editor
- Canonical TipTap JSON `tiptap@1`; deterministic RST/MyST export.
- Generic tree: chapters/folios, nesting, reorder, cycle guards.
- Document versioning with `expected_version` 409, history detail/restore,
  single-file RST/MyST import, 409 reload/overwrite in the UI.
- Media V1: PNG/JPEG/GIF/WebP/AVIF only, magic-byte sniffing, 10 MiB
  streaming cap, atomic writes, canonical `/_static/media/{uuid}.{ext}`
  references, build-time copying, cross-grimoire reference rejection.
  Video/audio/attachments remain V1.x.

### Builds and serving
- One build at a time per Athenaeum; per-Athenaeum monotonic build
  numbers; failed builds keep logs; successful builds keep immutable
  artifacts with `manifest.json`.
- Sandboxed Sphinx 9.2.0 build in an isolated engine-only venv with
  `NoNewPrivileges`, `PrivateTmp`, resource/time limits, whitelisted env,
  and no network fetch.
- Serving at `/a/{public_slug}/`, `/latest/`, `/stable/`, `/b/{n}/`;
  private by default; owner/member access; `/a` browser cookie; strict
  manifest-derived CSP; external-only CSS; bounded namespaced custom CSS.
- Public names are owner-renamable; old names become permanent aliases;
  deletion leaves permanent tombstones; names are never reused; alias
  redirects are `308` after authorization.

### Backup, restore, and move
- 0039: Editorial (content, media, names, every ever-published
  successful build + artifact) and Full (adds failed builds, logs, and
  all successful artifacts), ZIP or `.tar.gz`, one manifest.
- Editorial streams synchronously; Full runs as a Celery job with a
  15-minute single-use HMAC download; no server-side retention.
- Restore validates the whole archive before any write, creates a fresh
  Athenaeum owned by the importer, maps every row to fresh UUIDs,
  preserves build numbers/pointers and numbered URLs, rewrites media
  URLs, nulls unmatched identities, reclaims only free/same-user-
  tombstoned names, and auto-suffixes conflicts in the API path.
- 0040 adds CLI `backup export`/`restore` sharing the 0039 core. CLI
  restore is strict: a live name or another owner's tombstone conflict
  fails before writes; `--force` bypasses only the empty-target guard.
- The supported move is content-only per Athenaeum. Users, memberships,
  refresh tokens, and audit rows are never exported; the importer owns
  restored sites. Raw `pg_dump` + filesystem copy is the documented
  ops-only full-fidelity fallback.

### First run and operations
- `scriptorium-admin setup` is read-only: config, `SECRET_KEY`, PG18,
  Alembic head/pending, roots, build Python, TLS.
- `migrate` is explicit, idempotent, and refuses PG < 18.
- `user create`/`user list`; no hashes printed.
- `verify` is read-only: DB/head, names/pointers, artifact
  manifests/jail, media size/SHA-256, config, TLS.
- One no-shell-evaluation config loader shared by CLI and services; a
  real environment variable wins over `/etc/scriptorium/config.env`.
- `postinst` never migrates or generates certificates; it creates the
  user/group/dirs, seeds config once, applies ownership, and enables the
  renewal timer.

### Built-in TLS (0040)
- Native HTTPS termination in Gunicorn/Uvicorn on `SC_TLS_BIND`
  (default `0.0.0.0:443`); a separate port-80 listener returns `308`.
  No plaintext application listener and no reverse proxy required.
- Local ECDSA P-384 CA (10 years, `root:root 0600`) + ECDSA P-256 leaf
  (90 days, `serverAuth`, DNS/IP SANs); trust the CA once.
- TLS 1.2 minimum + TLS 1.3; TLS 1.2 ECDHE+AEAD only; no CBC/RSA-kex/
  3DES/RC4/NULL/compression/renegotiation/tickets; SHA-256+.
- Imported PEM fullchain + unencrypted key with dates/strength/match/
  hash/EKU/SAN/chain validation, atomic install, graceful reload,
  automatic rollback on failure; imported certs never auto-renew.
- Daily renewal timer, renew at 30 days remaining, keep 5 versions,
  history/rollback/prune, HSTS off by default (no preload), `tls verify`.
- Redirect `Host` is honored only when it matches a certificate SAN;
  otherwise `SC_TLS_REDIRECT_HOST`, a certificate SAN, or `400`.
- Uvicorn proxy headers are disabled; `X-Forwarded-For` is untrusted.

### Packaging and ownership
- nfpm builds `.deb`/`.rpm` from bundled Python 3.14.10, app venv,
  engine-only build venv, and Redis 8.10.2; the target never runs pip or
  fetches code.
- systemd units: `scriptorium-web`, `scriptorium-worker`,
  `scriptorium-redis`, `scriptorium-redirect`, plus
  `scriptorium-tls-renew.service`/`.timer`. Services run as
  `scriptorium`, sandboxed with read-only `/opt` and `/etc`; privileged
  binds use `CAP_NET_BIND_SERVICE`.
- Ownership O1: every Scriptorium-managed file/directory is
  `scriptorium:scriptorium`. Accepted exceptions: systemd unit files and
  package metadata (root), the external PostgreSQL data directory
  (`postgres`), and the local CA private key (`root:root 0600`).

## 6. Contracts that must not regress

1. Numbered `/b/{n}/` URLs and build numbers survive every supported
   export/restore; `latest`/`stable` pointers remain meaningful.
2. Public names are one global namespace; aliases/tombstones are
   permanent; names are never reused; alias redirects are `308` after
   authorization.
3. Private is the default; outsiders get uniform `404`; private
   responses are not cacheable; public numbered builds are
   immutable-cached (privacy caveat disclosed in 0035).
4. Served artifacts require `status='ok'` and a valid manifest; CSP is
   manifest-derived; no inline styles/handlers/`<style>`; custom CSS is
   bounded and namespaced.
5. Archives are untrusted: validate manifest/inventory/hashes/sizes/
   paths before any write; fresh UUIDs; artifact/media jail; cleanup on
   failure; one transaction.
6. CLI move restore is strict on names; the API restore keeps
   auto-suffix. `--force` never relaxes name strictness.
7. `setup`/`verify` are read-only; `migrate` is explicit; `postinst`
   never touches the DB or TLS.
8. TLS is the only V1 listener contract: HTTPS on 443, HTTP→HTTPS 308 on
   80, no plaintext app listener, no proxy-header trust, hardened
   protocol/cipher policy, CA key root-only.
9. Every app path is `scriptorium:scriptorium` except the three accepted
   exceptions.
10. No SEO implementation, M5 signing/provenance, page aliases, or
    distribution before their own plans and owner rulings.

## 7. Stack at the end of this record

- Python 3.14.10 (PBS `20261026`), FastAPI 0.162.0, Starlette 1.10.0,
  Pydantic 2.14.1, Uvicorn 0.54.0, Gunicorn 26.2.0,
  uvicorn-worker 0.4.0, cryptography 50.0.2.
- SQLAlchemy 2.1.6, Alembic 1.20.1, asyncpg 0.32.0, PostgreSQL 18.6
  exclusive.
- Celery 5.6.3, redis-py 6.4.0, bundled Redis 8.10.2.
- Sphinx 9.2.0, docutils 0.22.4 (0.23 gated), MyST-Parser 5.1.0.
- Node 26.13.0 LTS / npm 11.20.0, React 19.3.1, TypeScript 7.0.2,
  TipTap 3.32.1, Vite 8.3.5, Vitest 5.0.5, ESLint 10.13.0,
  Prettier 3.9.10, Playwright 1.64.1, Testing Library 16.3.3,
  axe-core 4.14.0, Tabler icons 3.50.0.
- nfpm 2.x (validated 2.48.0).

The authoritative pin list is `docs/technology/compatibility-matrix.md`
plus the lockfiles.

## 8. Testing and CI history

- CI has three workflows: `lint-type-test` (backend ruff/format/mypy/
  pytest with PG18 + Redis; frontend lint/format/typecheck/Vitest/build/
  audit; docs/brain validator), `security` (gitleaks, pip-audit, npm
  audit, SAST), and `packaging` (nfpm contract, unit/config/docs checks,
  runtime build).
- Local live PG/Redis has repeatedly been unavailable (Docker socket
  denied, or only an older local PG). Live-DB tests therefore skip
  locally and run in CI. Never treat a local skip as proof; check CI.
- Known scoped exception: `typescript-eslint` peer range excludes
  TypeScript 7.0.2, so ESLint covers JavaScript/config only and
  `tsc --noEmit` is the TypeScript type gate. Owner-approved; review
  when typescript-eslint supports TS 7.
- `docutils 0.22.4` remains a time-boxed exception until MyST lifts its
  `<0.23` cap; the manual probe is the bump gate.
- Rule 6 means `pytest -W error`, ruff/mypy clean, no skipped
  warnings, and no unapproved suppressions.
- Rule 8 means every fix/new behavior has a regression test and no
  previously approved behavior is broken.

## 9. Known limitations and deferred work

- No page-level path aliases (B1 deferred); editor renames can change
  `latest`/`stable` page paths while numbered builds keep old paths.
- No SEO implementation: canonical host/channel, robots/sitemap,
  structured data, social metadata, and per-Athenaeum editorial controls
  require a dedicated plan and owner rulings.
- No distribution phase (Q-DIST-A…D parked).
- M5 signing/provenance, lintian/rpmlint, clean-install matrix, and the
  full admin guide remain.
- No ACME/Let's Encrypt, reverse-proxy termination, HSTS preload, or
  automatic renewal of imported certificates.
- No identity-bearing move bundle, owner-transfer endpoint, or
  zero-downtime migration; raw dump is ops-only.
- Video/audio/attachments and bulk import are V1.x.
- The local CA key cannot be read by the service by design; losing it
  means generating a new CA and re-trusting clients unless it was backed
  up as a root secret.
- `pip-audit`/`npm audit` are advisory gates; an upstream advisory can
  temporarily require a documented exception or version decision.

## 10. Branch and release state at this record

- Remote: `git@github.com:M-s-Tech4TIME/scriptorium.git` (public).
- `dev` carries all implementation through decision 0040; `main` is
  fast-forwarded to the same commit at closeout so both branches are
  byte-identical (0013).
- Before this tranche: `dev` `6e53875`, `main` `03f9466`.
- Release promotion is ff-only; never rewrite `main`. Feature work lands
  on `dev` first and must be CI-green before promotion.

## 11. How to resume after an environment change

Read `docs/history/ENVIRONMENT-MIGRATION.md` and follow its checklist.
In short:

1. Clone the repo and check out `dev` at the recorded commit.
2. Install Python 3.14.x, Node 26.13.0, PostgreSQL 18.6, Redis 8.10.2,
   nfpm 2.x, and `gh` if you will verify CI.
3. Create `backend/.venv`, install `backend/requirements.lock`, run
   `npm ci` in `frontend/`.
4. Set `DATABASE_URL`/`REDIS_URL` to live PG18/Redis if available;
   otherwise expect skips and rely on CI for live coverage.
5. Run the full local gates, then `git status`/`git log` and the brain
   resume protocol.
6. Continue only from `HANDOFF.md`; do not start SEO, M5, page aliases,
   or distribution without the owner's plan/rulings.
