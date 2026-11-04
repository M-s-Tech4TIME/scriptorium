# OPEN-QUESTIONS

Last updated: 2026-11-04 / Ref: Q-SM-A…M resolved by 0040; server move/TLS implemented

| ID | Question | Blocks | Asked |
|---|---|---|---|
| Q-001 | `.github/` at `scriptorium/.github/` invisible to Actions — CLOSED as moot: re-root (Q-002A) puts workflows at repo root again. No shim needed. | — | closed 2026-10-16 |
| Q-002 | Login rate limiting: RESOLVED — owner approved Option B 2026-10-20 (in-app Redis fixed window, fail-closed; decision 0019). Implement before M4. | — | closed 2026-10-20 |
| Q-M3-16a–e | Duplication sub-decisions: RESOLVED by owner 2026-10-21 — caller-supplied slug w/ optional auto-suffix; owner-only roster; head-as-v1 (no history clone); any owned target library; copy-of-copy allowed. Decision 0025. | — | closed 2026-10-21 |
| Q-C3.5-A | **Curated default theme base — RESOLVED by owner ruling 2026-10-21 (decision 0027):** the theme is Scriptorium's own, built from the ground up (no builtin/third-party inheritance); the Sphinx engine is fully inherited/utilized incl. vendored engine JS. **Design baseline landed 2026-10-22 (decision 0028):** the external design consult answered D1–D17; the owner approved the full token/icon/palette/copy-script sheet — C3.5 code is fully specified (no design decisions outstanding). | — | closed 2026-10-21 (record complete 2026-10-22) |
| Q-EDITOR-1 | **Code-block language suggestion set in the editor** (from batch #2 platform facts, 2026-10-23): the theme shows user-defined language labels on code chrome; the EDITOR needs an accessible picker for it. Recommended (not yet approved): an accessible combobox (ARIA 1.2 pattern) seeded from the vendored Pygments lexer names, storing a display label + lexer alias separately (custom languages via the field falling back to plain text). Also covers: whether display-name inheritance auto-fills from the lexer or stays free-form. Owner verdict needed; blocks nothing in the theme (M4-C4/M5). | editor phase | 2026-10-23 |
| Q-SERVE-A | **RESOLVED by owner (A2, decision 0035):** owner-selected published builds with `latest`/`stable` pointers over immutable numbered builds; unpublish clears pointers only. | — | closed 2026-10-24 |
| Q-SERVE-B | **RESOLVED by owner (B3, decision 0035):** per-Athenaeum public toggle, private by default; owner/member reads allowed, outsiders uniform `404`. | — | closed 2026-10-24 |
| Q-SERVE-C | **RESOLVED by owner (C1, decision 0035):** FastAPI serves artifacts directly; no nginx alias required for v1. | — | closed 2026-10-24 |
| Q-SERVE-D | **RESOLVED by owner (D1, decision 0035):** global `public_slug` + `/a/{slug}/`, `/latest/`, `/stable/`, `/b/{n}/`. **Amended by 0036 (2026-10-28):** the owner may rename the public name; old names are permanent aliases; deletion tombstones; URL shape Option 1 retained. | — | closed 2026-10-24; amended 2026-10-28 |
| Q-SERVE-E | **RESOLVED by owner (E2, decision 0035):** manifest-derived strict CSP, external-only styles, bounded namespaced custom CSS; manifest ships with exported artifacts. | — | closed 2026-10-24 |
| Q-DIST-A | Credential vault design for push targets — encryption at rest, minimal scope, rotation. | distribution phase | 2026-10-21 |
| Q-DIST-B | Delivery semantics — retries/backoff, per-target status log, "re-push latest" button rules. | distribution phase | 2026-10-21 |
| Q-DIST-C | Target roster priority + mode (repo backup vs Pages hosting) — GitHub → GitLab → SFTP → FTP? | distribution phase | 2026-10-21 |
| Q-DIST-D | React shell format spec — `content.json`/`site.json` schema, routing/404 fallback, CSP posture. | distribution phase | 2026-10-21 |
| Q-BK-A | **RESOLVED by owner (A1, decision 0039):** Editorial carries content, media, names, and every ever-published successful build with its served artifact, so numbered `/b/{n}` URLs survive in both modes; Full adds failed builds, logs, and artifacts for every successful build. | — | closed 2026-11-01 |
| Q-BK-B | **RESOLVED by owner (B3, decision 0039):** both ZIP and `.tar.gz`, selectable per export; restore auto-detects the container; one shared manifest. | — | closed 2026-11-01 |
| Q-BK-C | **RESOLVED by owner (C1, decision 0039):** on-demand, no server-side retention; Editorial streams synchronously; Full runs as a Celery job with an expiring single-use signed download. | — | closed 2026-11-01 |
| Q-BK-D | **RESOLVED by owner (D1, decision 0039):** the importer owns the restored site; unmatched identities are nulled; users, memberships, refresh tokens, and audit rows are never exported. | — | closed 2026-11-01 |
| Q-BK-E | **RESOLVED by owner (E1, decision 0039):** restore always creates a fresh Athenaeum owned by the importer; reclaim a public name only when free or tombstoned by the same user; conflicts get the standard auto-suffix; other owners' names/tombstones are never touched. | — | closed 2026-11-01 |
| Q-SM-A | **RESOLVED by owner (A1, decision 0040):** CLI `scriptorium-admin user create --email --display`, password via TTY prompt or `--password-stdin`; no open registration, no env secrets. | — | closed 2026-11-03 |
| Q-SM-B | **RESOLVED by owner (B1, decision 0040):** `user create` + `user list`; 12–1024 characters, no composition; memberships re-granted via the existing API. | — | closed 2026-11-03 |
| Q-SM-C | **RESOLVED by owner (C1, decision 0040):** content-only per Athenaeum; users/memberships/refresh tokens/audit are never exported; the importer owns the restored site; global tombstones for deleted Athenaeums are not carried; raw `pg_dump` + filesystem copy is the documented ops-only full-fidelity fallback. | — | closed 2026-11-03 |
| Q-SM-D | **RESOLVED by owner (D2, decision 0040):** CLI `backup export` + `restore` alongside the API, sharing the 0039 core; headless, no proxy upload limit, no Redis/Celery dependency for the CLI export. | — | closed 2026-11-03 |
| Q-SM-E | **RESOLVED by owner (E1, decision 0040):** read-only `setup` preflight (config, `SECRET_KEY`, PG18, Alembic head, roots, build Python, TLS) + next steps; never mutates state. | — | closed 2026-11-03 |
| Q-SM-F | **RESOLVED by owner (revised F-A1…F-L1, decision 0040):** app-native TLS in Gunicorn/Uvicorn on 443 plus HTTP→HTTPS `308` on 80; no reverse proxy; no plaintext app listener; local ECDSA P-384 CA + P-256 leaf; hardened TLS 1.2/1.3; daily renewal/5 versions; PEM import with validation/rollback; HSTS off by default; add `cryptography`/`uvicorn-worker`; ownership/sandbox; full TLS CLI; SAN auto-detect/overrides; built-in TLS only in V1. | — | closed 2026-11-03 |
| Q-SM-G | **RESOLVED by owner (G1, decision 0040):** maintenance-window cutover; stop old web/worker, export, restore, verify, DNS switch; keep old host for rollback. | — | closed 2026-11-03 |
| Q-SM-H | **RESOLVED by owner (H1, decision 0040):** generate a new `SECRET_KEY` on the new host; sessions re-authenticate; no secret transfer. | — | closed 2026-11-03 |
| Q-SM-I | **RESOLVED by owner (I1, decision 0040):** CLI move restore strict-fails on a live-name/other-owner-tombstone conflict; the API owner restore keeps 0039 auto-suffix; `--force` only bypasses the empty-target guard. | — | closed 2026-11-03 |
| Q-SM-J | **RESOLVED by owner (J2, decision 0040):** read-only `scriptorium-admin verify` (DB head, names/pointers, artifact manifests/jail, media hashes, TLS) plus the manual checklist. | — | closed 2026-11-03 |
| Q-SM-K | **RESOLVED by owner (K1, decision 0040):** CLI move restore refuses if any Athenaeum exists unless `--force`; `--force` never relaxes name strictness. | — | closed 2026-11-03 |
| Q-SM-L | **RESOLVED by owner (L1, decision 0040):** implement first-run/move now on current packages; M5 later adds signing/provenance/clean-install and folds the runbook into the admin guide. | — | closed 2026-11-03 |
| Q-SM-M | **RESOLVED by owner (M1, decision 0040):** shared loader for `/etc/scriptorium/config.env`, env wins, no shell evaluation; CLI sees the same roots/secret as systemd. | — | closed 2026-11-03 |

Notes: Q-SERVE/Q-DIST wording was drafted by the assistant from the
owner's rulings (placement + concepts ratified 2026-10-21, see decision
0026 phase-boundary section) — the owner may edit wording before any
resolution. Q-DIST-A…D remain open and parked for the distribution phase.

**Server move/first-run (Q-SM-A…M): RESOLVED by owner 2026-11-03 and
implemented 2026-11-04 (decision 0040).** The approved plan is
`docs/roadmap/server-move-plan.md`; operator runbooks are
`docs/operations/server-move.md` and `docs/operations/tls.md`. No
implementation remains blocked by these questions.

M4-C2/C3 edge cases — RESOLVED by owner 2026-10-21 (**A/A/A**, recorded
in 0026 §Edge rulings): empty Athenaeum → 422 refusal; empty grimoire →
skipped + log note; one build at a time per Athenaeum, trigger while
queued/running → 409.

**Curated default theme base — RESOLVED (owner 2026-10-21, decision
0027):** Scriptorium's own from-scratch theme with full engine
inheritance (incl. vendored engine JS, pinned DOM contracts). The
design baseline (tokens, icons, palette, copy script) landed 2026-10-22
via decision 0028 and the owner's sheet approval; C3.5 code follows.
See 0027 + 0028.

**Serving questions Q-SERVE-A…E are RESOLVED (owner A2/B3/C1/D1/E2,
decision 0035) and implemented. URL durability was approved separately
(A1/B1/C1/D1/E1/F1, decision 0036) and implemented. Distribution
questions Q-DIST-A…D remain OPEN and parked in their table rows above.**

**SEO phase (owner-requested 2026-10-28, not an open question yet):** the
owner wants a dedicated, fully detailed SEO plan later; every SEO
feature/attribute must be user-controllable per Athenaeum in the editorial
panel. Canonical host/channel, robots/sitemap, structured data, and social
metadata are undecided. Do not implement before the plan and owner
rulings. Sequencing relative to distribution is not ruled; recommended
URL durability → SEO → distribution.

**Standing Rule 8 (approved 2026-10-24):** the owner approved the
Regression Integrity rule as written; it is not an open question. The
next theme batch (0034) is the first change executed under it.

**0032 search scope (not an open question):** the owner approved
client-side on-demand sectioning with ~10 candidate folios and
progressive render; a build-time section index is the documented scale
upgrade, deferred. `searchtools.js` stays in the vendored asset set
(0027) although no page loads it — removing it would reopen 0027 and is
not part of this tranche.

**Design-baseline sub-items (all RESOLVED 2026-10-22, decision 0028, no
open remainder):** single fixed scheme (D3 supersedes D2), no logo file
v1 (`--sd-wordmark` hook reserved), icon breadth across the artifact
surface, category labels all-caps bold verdigris (D15 owner-revision),
Tabler inline-sprite icons (CDN loader eliminated), custom Pygments
style, first-party copy script, zero asset-injecting extensions v1,
uniform `--sd-page-ink` callout body ink. A future second color scheme
(`[data-theme]`) is its own later ruling, not an open question here.

**Backup/restore (Q-BK-A…E, asked 2026-10-31): RESOLVED by owner
2026-11-01 (A1/B3/C1/D1/E1, decision 0039) and implemented.** Editorial
and Full both preserve numbered `/b/{n}/` URLs; ZIP and `.tar.gz` are both
supported; Full is async with no retention; the importer owns the restored
site with unmatched identities nulled; restore creates a fresh Athenaeum
and reclaims only free or same-user-tombstoned names. The server-move/
first-run + built-in TLS phase (Q-SM-A…M, decision 0040) is implemented;
page aliases, M5, distribution, and SEO remain later phases.
