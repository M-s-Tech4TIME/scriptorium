# 0026 — M4 build design: per-Athenaeum production (Q-M4-P1…P4 + design mandate)

- **Status:** accepted
- **Decided:** 2026-10-21 (owner ruled the four build forks in the M4 design
  session; the reconciliation and the design mandate were ratified in the
  same session, then re-confirmed before implementation)
- **Scope:** the M4 milestone — producing the documentation website
  artifact. Serving, URL durability, and remote distribution are separate
  phases and are **not** in scope here.

## Owner rulings

| Fork | Ruling |
|---|---|
| P1 — site unit | **One Athenaeum = one site.** A build compiles the *entire library* (all grimoires, chapters, folios) into a single unified Sphinx project/website. The Read the Docs "project" analog is the Athenaeum; per-build numbers stand in for RTD "versions" at M4 granularity (stable/latest publish pointers are serving-phase decisions). |
| P2 — trigger | **Manual only.** The Athenaeum owner POSTs a build trigger (endpoint lands in M4-C3). Saves never trigger anything. Automation/scheduling is a later decision. |
| P3 — isolation | **Limited-subprocess sandbox.** Sphinx runs as a subprocess under RLIMIT (CPU/time, memory, processes), no network, minimal environment. Explicitly **not** containers/nspawn. Hermetic per Rule 2: pinned Sphinx/docutils/MyST from the frozen stack; no installs at build time (RTD's environment-creation step is deliberately rejected). |
| P4 — retention | **Keep every build.** Each successful build's artifact is retained indefinitely; retention/cleanup policy is a serving-phase decision. |

## Artifact model (reconciliation, owner-ratified)

- **Source staging** inside each build workspace is keyed **by grimoire
  id** — every book materializes into its own directory inside the
  ephemeral, per-build staging tree. This *amends* the earlier
  `/var/lib/scriptorium/sources/<grimoire>/` persistent-jail micro-default:
  staging is now built per build and thrown away after the run.
- **Artifact** keyed **by Athenaeum**:
  `/var/lib/scriptorium/artifacts/{athenaeum_id}/{build_number}/`.
- **Numbered builds** (ratified): every build is an immutable, **numbered**
  snapshot of the whole library. `builds.build_number` is a per-Athenaeum
  monotonic counter (1, 2, 3, …). The numbered-artifact model — "build the
  library, get a new numbered artifact, previous ones retained" — was
  presented and approved during the artifact-model discussion.

## The artifact is a product

- The output folder is a **portable, self-contained static website**: no
  database, no Scriptorium runtime dependency, no server process. Users
  copy it to any static host — their own nginx, GitHub Pages, S3 +
  CDN, Netlify, anything — exactly the "grab the build folder and host it"
  story of Read the Docs, except Scriptorium generates the source folder
  the RTD user would have hand-maintained (the two-stage pipeline:
  materialize → compile).
- **HTML only in M4.** PDF/EPUB output is deferred to a later decision;
  the pipeline design does not prejudge it.
- **Zero-warning builds:** Sphinx runs with `-W`; a build is `ok` **only
  if** warning-free — Rule 6 applied to the output product itself.

## Design mandate (owner-ratified 2026-10-21)

1. **Artifact security parity.** A website Scriptorium builds must be as
   secure and stable as Scriptorium itself: Scriptorium controls every
   byte of generated output (canonical TipTap JSON → escaped source; no
   raw-HTML injection surface), the toolchain is pinned/hermetic/no-network,
   and generated sites ship **no third-party scripts or trackers**
   (self-contained). Host-level hardening (CSP/security headers) belongs
   to the serving phase.
2. **Structure locked, skin open.** Scriptorium owns the site structure —
   layout, templates, navigation. Users own the skin *through the
   platform*: brand settings (colors/fonts/logo/accents) plus optional
   custom CSS — trusted-but-sandboxed, CSP-backed at serve time, no
   template overrides. No user ever hand-edits generated files. The
   shipped default look is a **Scriptorium-curated theme, never vanilla
   Sphinx** (micro-default: base theme choice is made in M4-C3).

## Phase boundary (owner-confirmed)

- **M4 = production only.** Build + artifact + status. **No HTML over
  HTTP** — the M4 UI shows builds and artifacts, not served pages.
- **Serving phase** (dedicated, next): Scriptorium hosts the latest OK
  build on the same server as a convenience layer (same-origin control,
  publish toggles). Questions Q-SERVE-A…E are parked in OPEN-QUESTIONS.
- **URL-durability phase** (after serving: aliases/redirects/immutable
  build identity once serving stabilizes URL schemes).
- **Distribution phase** (post-serving; concept approved, details later):
  push targets — GitHub/GitLab repos (scoped tokens; backup or Pages
  hosting, e.g. `gh-pages`), SFTP (paramiko) / FTP, future sinks;
  encrypted credentials; audited per-target deliveries with status, log,
  and retry; **manual push per target after a successful build — never
  automatic**. Plus the **React shell build format**: a prebuilt
  React+TypeScript docs-viewer compiled once and shipped inside
  Scriptorium; builds emit `content.json` + `site.json`; zero Node on the
  server; per-build format choice `sphinx | react` — both derived from
  the one canonical source.

## Migration 0006 (append-only)

Adds to `builds`: `athenaeum_id` (FK `athenaeums`, nullable, CASCADE —
mirrors the athenaeum-layer FKs; delete-refusal makes it
belt-and-braces), `build_number` (NOT NULL, backfilled from a
deterministic `ROW_NUMBER` sequence), relaxes `grimoire_id` to nullable,
and adds `ck_builds_site` (exactly one of the two keys must be set) and
`uq_builds_athenaeum_number`. Pre-M4 rows remain grimoire-keyed (their
data is untouched; they share one derived legacy number sequence under
the NULL athenaeum partition). Migrations 0001–0005 are immutable.

## Edge rulings (owner, 2026-10-21)

Ruled A/A/A immediately before C2 implementation:

| Edge | Ruling |
|---|---|
| E1 | **Empty Athenaeum** (no grimoires) → build **refused `422`** — "nothing to build"; no blank artifact folders. |
| E2 | **Empty grimoire** (book with zero folios) inside a build → **skipped from the site** + a note in the build log (keeps the `-W` build warning-free; the owner sees it in the log). |
| E3 | **One build at a time per Athenaeum** — triggering while a build is queued/running → **`409`**. Matches the manual-trigger philosophy; makes numbering trivially collision-free. |

## Micro-defaults (owner-vetoable, disclosed)

- Numbering starts at 1 per Athenaeum; legacy grimoire-era rows are
  numbered in one shared legacy sequence (ordered by `started`, `id`).
- The `ck_builds_site` exact-one-key CHECK (no both-set, no both-null
  rows) — enforced at the DB even though application code always writes
  new-style rows.
- Curated default-theme base picked in M4-C3 (visible to the owner as a
  preview before it ships).
- Staging materializes **always from canonical TipTap** (per-build export
  via the M2 exporters; the documents `source_text` cache is not
  trusted as a build input — no stale-source artifacts).
- Interim Sphinx theme in C2's generated `conf.py` is a placeholder
  base (`alabaster`); **curated default theme lands in C3** per the
  design mandate above.
- Edge cases in staging are ruled (owner 2026-10-21, A/A/A) — see
  **Edge rulings** above: empty Athenaeum → `422`; empty grimoire →
  skipped + log note; one build at a time per Athenaeum (trigger while
  queued/running → `409`).

## C3 mechanics (2026-10-21 — implementation-recorded mechanism micro-defaults, disclosed)

- **Trigger:** `POST /api/v1/athenaeums/{id}/builds` — Athenaeum-owner
  only; `GET` list/one is owner-or-member (membership on any grimoire
  inside). Foreign Athenaeum → uniform `404` (IDOR rule in force).
- **E1 mechanics:** the trigger pre-check counts grimoires — zero →
  `422` ("nothing to build"). A library whose books are ALL empty still
  passes the pre-check and fails at **run time** (`status=failed`,
  log note) — per-book emptiness is E2 territory, not E1.
- **E3 + numbering serialization:** the active-build check and the
  `max(build_number)+1` insert run in one transaction guarded by
  `pg_advisory_xact_lock` (single-int8 form, keyed on the first half of
  the Athenaeum id) — concurrent triggers cannot race past the lock.
- **Dispatch:** `SC_BUILD_DISPATCH` — `celery` (prod default; task
  `app.worker.tasks.run_athenaeum_build` on queue `scriptorium`; broker
  from `CELERY_BROKER_URL` env or `/etc/scriptorium/config.env`,
  fail-loud when missing) or `inline` (dev/CI only: the request thread
  runs the same `app.sphinx.execute` executor and the row is refreshed
  so the 201 carries the final status).
- **Executor:** a fresh async engine per run, awaited-disposed in
  `finally` (the cached app engine never crosses event loops — M3
  lesson). Status machine `queued → running → ok|failed` writes
  `started/finished/log_path/artifact_path`; staging/plan failures mark
  `failed` and drop a crash log under the build workspace.
- **Audit:** action `build_triggered` (grimoire_id NULL — Athenaum-
  scope action keyed in meta).
- **Sandbox mechanics (P3):** the child environment is a whitelist —
  `PATH`, `LC_ALL=C.UTF-8`, `PYTHONHASHSEED=0`, `HOME` inside the build
  workspace; inherited keys (proxies, secrets) are structurally absent.
  RLIMITs: `SC_SPHINX_CPU_SECONDS=600`, `SC_SPHINX_MEMORY_BYTES=1.5 GiB`,
  `SC_SPHINX_MAX_FILE_BYTES=512 MiB`, core=0; wall timeout
  `SC_SPHINX_TIMEOUT_S=900`. Command: `python -m sphinx -W -b html . _build/html`.
  Honest limitation (from the P3 ruling: no containers): OS-level
  egress isolation is by *construction* of the pinned stack — nothing
  in it dials out and no proxy/credential env exists — not a kernel
  namespace.
- **Paths:** FHS defaults; dev/CI overrides `SC_ARTIFACT_ROOT`,
  `SC_BUILD_ROOT`, `SC_BUILD_PYTHON`. Disclosed micro-default:
  `SC_BUILD_PYTHON` falls back to `sys.executable` pre-packaging —
  production must point it at the isolated build venv (packaging, C4).
  On `ok`: artifact `{SC_ARTIFACT_ROOT}/{athenaeum}/{build_number}/`
  (html/ + build.log), staging removed. On `failed`: log kept under
  `{SC_BUILD_ROOT}/{build_id}/build.log` (workspace retained; retention
  decisions are the serving phase's, P4).
- **Curated theme base:** queued for C3 but **not decided here**
  (Rule 4) — `alabaster` remains the placeholder; the owner question
  precedes any C4 packaging.
