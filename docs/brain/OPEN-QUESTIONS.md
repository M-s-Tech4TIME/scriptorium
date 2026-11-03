# OPEN-QUESTIONS

Last updated: 2026-11-03 / Ref: server-move plan drafted; Q-SM-A…M open for owner rulings

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
| Q-SM-A | **First-run account bootstrap.** A1 (recommended): CLI `scriptorium-admin user create --email --display`, password via TTY prompt or `--password-stdin`; no open registration, no env secrets. A2: one-time web setup token — friendlier, but adds an unauthenticated endpoint/state. A3: bootstrap env/file consumed at first start — automation-friendly, but secret handling and hidden state. | server-move phase | 2026-11-03 |
| Q-SM-B | **User-management scope + password policy.** B1 (recommended): `user create` + `user list`; min 12 chars, max 1024, no composition; memberships re-granted via the existing API. B2: full CLI (create/list/disable/reset/delete). B3: in-app global admin role/UI. Bigger surfaces raise attack/scope cost; B1 is enough for first-run/move. | server-move phase | 2026-11-03 |
| Q-SM-C | **Move fidelity + global names.** C1 (recommended): content-only per Athenaeum; users recreated by CLI, importer owns restored sites (no owner-transfer endpoint), memberships re-granted; 0039 D1 unchanged; document that global tombstones for deleted Athenaeums are not carried (raw `pg_dump` + filesystem copy is the ops-only full-fidelity fallback). C2: CLI-only identity-bearing move bundle (users/hashes, memberships, audit; no refresh tokens) — preserves multi-user fidelity but amends D1 and adds a sensitive archive mode. C3: whole-instance raw dump only — full fidelity, version-coupled, bypasses archive validation. | server-move phase | 2026-11-03 |
| Q-SM-D | **Move tooling entry points.** D1: existing API/UI only — tested, but needs web/worker and an 8 GiB upload through the proxy. D2 (recommended): add CLI `backup export` + `restore` alongside the API, sharing the 0039 core; headless, no proxy limits. D3: CLI restore only; export stays API. | server-move phase | 2026-11-03 |
| Q-SM-E | **`setup` behavior.** E1 (recommended): read-only preflight (config, `SECRET_KEY`, PG18, roots, build venv, pending migrations) + next steps; no mutation. E2: orchestrator (migrate + optional user/restore) — convenient but hides state changes. E3: keep the current DB-only check — insufficient for first-run. | server-move phase | 2026-11-03 |
| Q-SM-F | **TLS/reverse-proxy contract.** F1 (recommended): docs + nginx/Caddy examples in `/usr/share/doc/scriptorium/`; app stays loopback; operator supplies certs; trust forwarded headers only from loopback. F2: bundle a proxy unit with automatic TLS — new runtime/dependency. F3: app terminates TLS — cert reload complexity. | server-move phase | 2026-11-03 |
| Q-SM-G | **Cutover model.** G1 (recommended): maintenance window; stop old web/worker, export, restore, verify, DNS switch; keep old host for rollback. G2: dual-run with a read-only old host and lowered TTL — more complex, split-brain risk. G3: zero-downtime replication — out of scope. | server-move phase | 2026-11-03 |
| Q-SM-H | **`SECRET_KEY` on move.** H1 (recommended): generate a new key on the new host; sessions re-authenticate; no secret transfer. H2: reuse the old key — little benefit because refresh tokens are not exported, and it requires secure transfer. H3: overlap/rotation — out of scope. | server-move phase | 2026-11-03 |
| Q-SM-I | **Public-name conflicts on move.** I1 (recommended): CLI move restore strict-fails on any current-name/alias/tombstone conflict; API owner restore keeps 0039 E1 auto-suffix. I2: always auto-suffix — risks silent URL changes. I3: `--strict-names` flag — more surface. | server-move phase | 2026-11-03 |
| Q-SM-J | **Post-move verification.** J1: manual checklist only. J2 (recommended): read-only `scriptorium-admin verify` (DB head, names/pointers, artifact manifests/jail, media hashes, counts) + checklist. J3: checklist now, verify in M5. | server-move phase | 2026-11-03 |
| Q-SM-K | **Empty-target guard.** K1 (recommended): CLI move restore refuses if any Athenaeum exists unless `--force`. K2: additive like the API — operator discipline. K3: strict first-run mode refuses if any users/Athenaeums/audit exist — safest but blocks legitimate re-runs. | server-move phase | 2026-11-03 |
| Q-SM-L | **Scope vs M5.** L1 (recommended): implement first-run/move now on current packages; M5 later adds signing/provenance/clean-install and folds the runbook into the admin guide. L2: M5 first, then move on signed packages — delays the move. L3: merge into M5 — larger tranche. | server-move phase | 2026-11-03 |
| Q-SM-M | **CLI config parity.** M1 (recommended): shared loader for `/etc/scriptorium/config.env`, env wins, no shell evaluation; CLI sees the same roots/secret as systemd. M2: document `set -a; . config.env; set +a` — error-prone. M3: `--config FILE` only — keeps app modules env-only. | server-move phase | 2026-11-03 |

Notes: Q-SERVE/Q-DIST wording was drafted by the assistant from the
owner's rulings (placement + concepts ratified 2026-10-21, see decision
0026 phase-boundary section) — the owner may edit wording before any
resolution. None of these blocks M4 or later work until their phase.

**Server move/first-run plan (Q-SM-A…M, asked 2026-11-03):** full
options, trade-offs, current-state gaps, and the proposed runbook are in
`docs/roadmap/server-move-plan.md`. Implementation is blocked until the
owner rules.

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
first-run plan is now drafted (Q-SM-A…M); page aliases, M5, and SEO remain
later phases.
