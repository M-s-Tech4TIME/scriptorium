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

## Micro-defaults (owner-vetoable, disclosed)

- Numbering starts at 1 per Athenaeum; legacy grimoire-era rows are
  numbered in one shared legacy sequence (ordered by `started`, `id`).
- The `ck_builds_site` exact-one-key CHECK (no both-set, no both-null
  rows) — enforced at the DB even though application code always writes
  new-style rows.
- Curated default-theme base picked in M4-C3 (visible to the owner as a
  preview before it ships).
- Edge cases in staging (empty Athenaeum → refuse build? empty grimoire →
  skip or placeholder? per-Athenaeum build serialization?) are **not**
  decided here — they will be presented with options in M4-C2/C3.
