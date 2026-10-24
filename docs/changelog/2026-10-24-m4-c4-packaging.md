# Changelog 2026-10-24 — M4-C4: packaging build venv, config contract, docutils probe

## What landed

- **Isolated build venv:** `packaging/build-requirements.in` +
  `build-requirements.lock` pin the engine trio only (Sphinx 9.1.0,
  docutils 0.22.4, MyST 5.1.0; 27 transitive pins constrained by the app
  lock). `packaging/scripts/build-venv.sh` creates
  `packaging/build-venv` with `--no-deps` and asserts app deps are
  absent. nfpm installs it at `/opt/scriptorium/build-venv`;
  `SC_BUILD_PYTHON` points there in production.
- **Config contract:** `packaging/config.env.example` carries
  `DATABASE_URL`, `SECRET_KEY`, cookie/Redis/queue keys, the `SC_*`
  build paths/limits, and optional limiter overrides. `postinst` seeds
  `/etc/scriptorium/config.env` 0600 only when absent, creates
  `artifacts/`, and fails loud if the build venv is missing; it still
  never touches the DB.
- **Systemd ordering:** `scriptorium-web` and `scriptorium-worker` now
  declare `Requires=redis.service` and start `After=redis.service`
  (worker also after PG/network). The worker's Celery broker URL is in
  the packaged config.
- **0017 docutils-0.23 probe:** `scripts/probe-docutils-023.sh` builds
  an isolated venv, force-installs `docutils==0.23` with `--no-deps`,
  and runs round-trip/sourcegen/real-Sphinx-build tests under
  `-W error`. The manual `docutils-0.23-probe` workflow exposes it; it
  is deliberately not a push gate. Probe run: 58 passed, pin unchanged.
- **Regression coverage:** `backend/tests/test_packaging.py` pins the
  lock isolation, build-venv script, Redis ordering, config keys,
  nfpm contents, postinst behavior, and manual probe mechanics. The
  `packaging` CI job checks the same contract + shell syntax.
- **Records:** M4 report (`docs/roadmap/m4-report.md`), install/nfpm/
  celery/redis/sphinx/python/compatibility/layout/threat-model updates,
  brain sync.

## Why

M4-C3 left `SC_BUILD_PYTHON` falling back to `sys.executable`; production
must run user-content builds in an engine-only venv with no app deps.
C4 closes that gap and makes the worker's Redis dependency explicit at
the unit level. The docutils probe turns decision 0003's "0.23 gated"
into a repeatable manual gate without making every push depend on a
future MyST release.

## Verification

- `87 passed / 36 skipped` (`pytest -W error`), ruff + `mypy --strict`
  clean.
- `build-venv.sh` created a venv that imports 9.1.0 / 0.22.4 / 5.1.0
  and has no FastAPI/SQLAlchemy/Celery/asyncpg/Alembic.
- Probe with docutils 0.23: 58 passed (round-trip, sourcegen, real
  sandboxed theme build).
- Shell syntax (`sh -n` / `bash -n`), nfpm contents, systemd ordering,
  and config keys are asserted by tests and the packaging CI job.

## Status

C4 is pushed as `1add6c8`; all three CI workflows are green. M4
implementation is complete; serving phase (Q-SERVE-A…E) is the next
owner gate.
