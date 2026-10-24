# M4 report — build pipeline + theme (C1–C4)

Status: **implementation complete 2026-10-24** · Owner: alsechemist ·
Decision: 0026 (build design), 0027–0034 (theme) · Next: serving phase
(Q-SERVE-A…E), then URL durability and distribution.

## What M4 delivers

- **C1 — build design + identity (0026):** one Athenaeum = one numbered
  site; manual trigger; immutable artifact per build; limited-subprocess
  sandbox; keep every build. Schema/migration `0006buildsite`.
- **C2 — deterministic staging:** `app/sphinx/sourcegen.py` plans the
  whole library, stages per-grimoire sources, emits generated-only
  `conf.py` + toctrees, and fails loud on staging errors.
- **C3 — sandbox runner + queue + API:** `app/sphinx/runner.py` runs
  `python -m sphinx -W -b html` under RLIMITs and a whitelisted env;
  Celery task `run_athenaeum_build`; owner-triggered build endpoints,
  per-Athenaeum numbering, status machine, audit, artifact/log layout.
- **C3.5 — own theme (0027–0034):** from-scratch Sphinx theme, vendored
  engine JS, first-party search (dialog + full page), reading layout,
  On-This-Page rail, code chrome, pager, Inter, and the owner-approved
  feedback batches 0029–0034.
- **C4 — packaging/probe groundwork:** isolated
  `/opt/scriptorium/build-venv` from a 27-pin engine-only lock;
  `SC_BUILD_PYTHON` production wiring; `config.env.example` with the
  queue/build keys; both units `Requires=redis.service` /
  `After=redis.service`; postinst seeds config 0600, creates
  `artifacts/`, and fails loud without the build venv; manual
  docutils-0.23 probe workflow + script.

## Evidence

- Full backend suite: **87 passed / 36 skipped**, `pytest -W error`;
  ruff + `mypy --strict` clean.
- Real sandboxed `-W` Sphinx build exercised by
  `tests/test_theme_build.py`; artifact/link/search/contrast contracts
  pinned.
- Browser verification of preview #7 (headless Chrome): collapsed panel
  pre-paint marker, pager geometry at 1400/1000/800 px, code labels,
  search 7 folios/12 sections, dialog/clear/toggles/scrollspy intact.
- CI green ×3 on `2680738` (lint-type-test, security, packaging);
  C4 commit re-runs the same gates plus the packaging contract.
- docutils-0.23 probe run 2026-10-24: **58 passed** with Sphinx 9.1.0 /
  MyST 5.1.0; pin stays 0.22.4 because MyST's metadata cap is the gate
  and a version bump is an owner decision.

## Honest limitations / deferred

- Egress isolation is by construction of the pinned stack (no
  credentials/proxy in the whitelisted child env), not a kernel network
  namespace — P3 explicitly rejected containers/nspawn.
- M4-C4 packages the **build** venv and config contract; the full signed
  `.deb`/`.rpm`, app-venv assembly, lintian/rpmlint, SBOM/provenance,
  and clean-install matrix remain M5.
- docutils 0.23 stays gated; the probe is a manual bump gate, not a
  push gate.
- Serving decisions (stable/latest pointers, routing, brand injection,
  custom CSS, dark-mode policy) are the next phase, not part of C4.

## Commit map

- `b15446f` — C3.5 theme passes 0029–0032 (approved preview #5).
- `cbe2b22` — Standing Rule 8 (0033).
- `2680738` — fourth feedback batch + no-flash panel fix (0034).
- C4 commit — packaging build venv, config keys, Redis ordering,
  docutils probe, this report.
