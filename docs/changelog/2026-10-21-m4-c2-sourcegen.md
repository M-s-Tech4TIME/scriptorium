# 2026-10-21 — M4 C2: deterministic source staging (sourcegen)

Commits: `7d14f3a` (edge-ruling record) + this tranche · Author:
alsechemist (with OpenCode) · Milestone M4, tranche C2

## What changed

The three C2/C3 edge cases were presented with options and ruled
**A/A/A** by the owner, recorded in 0026 §Edge rulings (`7d14f3a`):
**E1** empty Athenaeum → `422` refusal · **E2** empty grimoire → skipped
from the site + build-log note · **E3** one build at a time per
Athenaeum — trigger while queued/running → `409` (enforced in C3).

Then `app/sphinx/sourcegen.py` — the pure staging planner behind "one
Athenaeum = one site" (0026 P1):

- **Snapshot folding:** `snapshot_nodes(rows)` folds flat,
  loader-ordered node rows into `SnapshotNode` trees (order preserved
  per sibling set; row order irrelevant).
- **Layout:** per-book directories under the build root — folio pages
  at `book/<…ancestor slugs>/<folio>` (docname = file path), chapter /
  folio-parent pages as RST `toctree` containers (0023 unrestricted
  nesting: a folio may parent). Book masters: `book/index.rst`; the
  site root `index.rst` toctrees all books.
- **Bodies export direct from the stored canonical TipTap** (the save
  path canonicalizes; `source_text` is never a build input — 0026
  micro-default). Export failure → `StagingError` → the build must
  record **failed** (Rule 6 fail-loud, no guessed output).
- **conf.py per Athenaeum:** MyST (`myst_parser` + `.md` suffix) only
  when at least one book is `myst`; master documents are always RST
  toctree pages; `html_theme` placeholder `'alabaster'` — **interim
  micro-default**, curated theme (mandate 2) lands in M4-C3.
- **Docname rule:** node leaf slug `index` would collide with the book
  master docname → mangled `index-p` (rare, deterministic, disclosed).
- **Toctree titles:** `Title <ref>` explicit form; angle brackets in
  titles sanitized to `«»` (presentation-only; node titles in the DB
  are untouched — disclosed micro-default).
- **Determinism:** identical snapshot → identical file map byte for
  byte (tested: `first == second`).

## Tests

`tests/test_sourcegen.py` — 14 offline cases (no PG): layout + index
routing, E1 refusals ×2 (no books / all books empty), E2 skip-note +
absence rules, MyST conf & `.md` pages, RST-only conf, nesting parent
pages (chapter containers + folio-with-children body+toctree),
contentless-shell exclusion, `index-p` mangle, toctree title
sanitization, determinism, `StagingError` fail-loud (heading skip,
0017 matrix), snapshot/order folding. Suite: **`59 passed, 33
skipped`** (baseline 45 → +14).

## Gates

ruff check/format · mypy strict (45 files) · `pytest -W error` zero
warnings · `validate-docs.sh` · CI ×3 verified green on `3a15b52`
(Rule 7; migration 0006 exercised by CI's live-PG suite at this head).

## Next

**M4-C3 runner + Celery + endpoints**: materialize the plan into the
per-build workspace, run `sphinx -W` inside the limited-subprocess
sandbox (P3), artifact under
`/var/lib/scriptorium/artifacts/{athenaeum}/{build_number}/`, status
machine queued→running→ok|failed, `POST /api/v1/athenaeums/{id}/builds`
(owner-only; E3 `409`) + GET list/one (members); Sphinx pinned into the
app stack + `docs/technology/`; live tests.
