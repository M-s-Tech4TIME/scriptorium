# 2026-10-21 — M4 C1: build design + build identity migration (0026)

Commits: this tranche · Author: alsechemist (with OpenCode) · Milestone M4, tranche C1

## What changed

M4 opens with the owner-ruled build design, recorded as decision
**0026** — the answer to "how Scriptorium builds documentation as a
whole", framed in the Read the Docs comparison the owner requested:

- **P1 — one Athenaeum = one site:** a build compiles the entire
  library into a single unified Sphinx project; per-build numbers stand
  in for RTD "versions" at M4 granularity.
- **P2 — manual trigger only:** the owner POSTs a build; saves never
  trigger anything; automation is a later decision.
- **P3 — limited-subprocess sandbox:** RLIMIT (CPU/time, memory,
  processes), no network, minimal env; explicitly NOT containers/
  nspawn; pinned Sphinx stack and no build-time installs (Rule 2
  hermeticity).
- **P4 — keep every build:** retention/cleanup policy is a serving-phase
  decision.
- **Reconciliation (ratified):** source staging keyed **by grimoire id**
  inside each ephemeral per-build workspace (amends the persistent
  `sources/<grimoire>/` jail micro-default); artifact keyed **by
  Athenaeum** — `/var/lib/scriptorium/artifacts/{athenaeum_id}/{build_number}/`.
- **The artifact is a product:** a portable, self-contained static
  website — "grab the build folder and host it anywhere" (farm of hosts:
  own nginx, GitHub Pages, S3, Netlify…), with Scriptorium materializing
  the source the RTD user would hand-maintain. HTML-only in M4;
  zero-warning `-W` builds (`ok` ⇔ warning-free).
- **Design mandate (owner-ratified):** artifact **security parity**
  (platform controls every byte; no third-party scripts) +
  **structure locked, skin open** (platform templates; brand settings +
  custom CSS through the platform; curated default theme — vanilla
  Sphinx refused).
- **Phase boundary:** M4 = production only (no HTML over HTTP);
  serving = dedicated next phase; URL durability after serving;
  Distribution phase (push targets + React shell format) — concepts
  ratified, details parked (Q-SERVE-A…E, Q-DIST-A…D in OPEN-QUESTIONS).

Schema (**migration 0006**, append-only — 0001–0005 untouched):
`builds.build_number` per-Athenaeum counter (NOT NULL after a
deterministic backfill; legacy grimoire-era rows share one derived
legacy sequence under the NULL partition), `builds.athenaeum_id` FK
(CASCADE, belt-and-braces vs delete-refusal), `grimoire_id` relaxed to
nullable (old-row data untouched), `ck_builds_site` (exactly one key
set), `uq_builds_athenaeum_number`. `models.Build` mirrors the schema
with the two-era key docstring.

## Tests

No router changes in C1 — offline suite unchanged: `45 passed, 33
skipped` expected; conftest migrates to the new head `0006buildsite`.
Migration SQL verified against 0001's columns (0004 op-convention
mirror: explicit `fk_/uq_/ix_` names, backfill-then-NOT NULL).

## Gates

ruff check/format · mypy · `pytest -W error` offline ·
`validate-docs.sh` · CI ×3 after push (Rule 7).

## Next

**M4-C2 source generation** (TipTap → per-folio rst/md via M2 exporters,
chapter toctrees, one `conf.py` per Athenaeum; pure functions, offline
unit tests; edge cases presented first per Rule 4) → **C3 runner +
Celery + endpoints** → **C4 packaging/probes + M4-complete report**.
