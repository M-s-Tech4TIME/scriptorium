# 2026-10-21 — M4 C3: sandboxed runner + Celery + build endpoints

Tranche C3 of decision 0026 · CI ×3 verified in the follow-up sync.

## What changed

The production half of "numbered builds" (0026 P1/P2/P3):

- **`app/sphinx/loader.py`** — snapshot loader with sidebar-identical
  ordering (categories by `position, created_at`; grimoires by title;
  uncategorized bucket last; nodes by `position, id`). Folds into
  sourcegen's `snapshot_nodes` for the pure planner.
- **`app/sphinx/runner.py`** — the sandboxed build: whitelist child env
  (`child_env`; proxies/secrets structurally absent), RLIMITs
  (CPU 600 s / AS 1.5 GiB / FSIZE 512 MiB / core 0, `SC_SPHINX_*`
  overrides), 900 s wall timeout, `python -m sphinx -W -b html . _build/html`.
  `ok` = warning-free. Artifact `html/` + `build.log` copied under
  `/var/lib/scriptorium/artifacts/{athenaeum}/{build_number}/`; staging
  removed on success, kept on failure (log + sources for inspection —
  retention is the serving phase's call, P4).
- **`app/sphinx/execute.py`** — one executor for both schedulers: fresh
  engine per run, awaited disposal in `finally`, status machine
  `queued → running → ok|failed`, `started/finished/log_path/artifact_path`
  recorded, staging/plan exceptions → failed + crash log.
- **`app/worker/`** — Celery wiring (`celery_app.py`; queue
  `scriptorium`, broker `CELERY_BROKER_URL` env/config.env, fail-loud)
  + `tasks.py` (`run_athenaeum_build` — same executor).
- **`app/routers/builds.py`** — `POST .../builds` (owner-only; E1
  zero-grimoire `422`; E3 `409` while queued/running; `max+1` numbering
  serialized with `pg_advisory_xact_lock` keyed on the Athenaeum id),
  `GET .../builds` (list, newest-first) + `GET .../builds/{id}` — owner
  or member-of-any-grimoire; foreign ids uniform 404. Dispatch
  `SC_BUILD_DISPATCH` (`celery` default / `inline` dev-CI with post-run
  refresh). Audit action `build_triggered`.
- `main.py` registers the router. No DELETE route: retention is a
  serving-phase decision (0026 P4) — unregistered DELETE gives the
  framework 405.

## CI round-trip findings (fixed before green)

The first CI live run rooted out four honest gaps (all fixed in-tranche):

- **Toctree document-relative resolution:** staged entries now use
  absolute `</docname>` refs (nested pages resolved against their own
  directory otherwise — `toc.not_readable`).
- **No-title targets:** Sphinx builds toctree entries from the target's
  own section titles; a page of bare paragraph text has none
  (`toc.no_title` drops the entry). Every referenced page now carries
  its node/book title as a generated top section (deterministic;
  disclosed above in 0026 §CI-discovered staging rulings).
- **MyST directives:** `.md` pages emit the fenced `{toctree}` form.
- **0006 downgrade vs library-era rows:** athenaeum-keyed builds
  cannot survive the legacy `grimoire_id NOT NULL` — the downgrade now
  drops them first (honest mirror).

Also re-anchored `test_failed_build_records_log` from a heading-skip
corpus (unsaveable through the real save path: documents.py runs the
exporter on save — ConversionError → 500) to the ruled run-time failure
(athenaeum with grimoires but all books empty → `failed` + crash log).

## Micro-defaults (disclosed, owner-vetoable)

- `SC_BUILD_PYTHON` falls back to `sys.executable` before packaging;
  production expects the isolated build venv (packaging, C4).
- `inline` dispatch blocks the HTTP request until the build finishes
  (dev/CI convenience; production is `celery`).
- E1 pre-check counts grimoires; an all-empty-books library fails at
  run time (E2-consistent) rather than 422.
- mypy override for `celery.*` (no py.typed marker) — scoped allowlist
  mirroring the docutils precedent (0017).
- **Theme**: the curated default base was queued for C3 but remains an
  OPEN OWNER QUESTION (0026 §C3 mechanics; `alabaster` placeholder) —
  parked in OPEN-QUESTIONS, asked next.

## Tests

- `tests/test_build_api.py` (live, 3 cases): E1 422, owner-only trigger
  404, numbered builds 1→2 with artifact inspection on disk, E3 409
  (external queued row), audit rows, member-visible GETs + stranger 404
  + cross-build 404, failed run (all-empty books) with crash log.
- `tests/test_worker_units.py` (offline, 7 cases): celery broker
  wiring + fail-loud, FHS env defaults, env-int fail-loud, dispatch
  whitelist, router registration (OpenAPI map), child-env whitelist
  non-inheritance proof.
- Suite: `66 passed, 36 skipped` offline baseline (was 59/33).

## Next

M4-C4: packaging (worker unit `After=redis`, build venv creation),
0017 docutils probe mechanics, M4-complete report + brain sync —
after the owner answers the theme question.
