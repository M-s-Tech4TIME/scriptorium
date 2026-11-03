# Technology — Celery 5.6.3 + Redis 8.10.2

- Versions (locked): Celery 5.6.3 (2026-03-26; 5.7b1 excluded per Rule 5),
  redis-py 6.4.0; broker Redis 8.10.2 (bundled server in packages,
  `redis:8.10.2-alpine` in dev/CI).
- Why: 15yr proven queue, Beat + Flower, multi-broker (decision 0005, LTS lens).
- Used: `backend/app/worker/` (Sphinx build jobs); unit `scriptorium-worker.service`.
- **M4 wiring (C3, 0026):** `app/worker/celery_app.py` builds a Celery app
  (`main="scriptorium"`, queue `scriptorium`, JSON serialization) from
  `CELERY_BROKER_URL` (env or `/etc/scriptorium/config.env`) — fail-loud
  when missing. `app/worker/celery.py` exposes `app = build_app()` so the
  `celery -A app.worker` unit resolves the app; `include=["app.worker.tasks"]`
  registers every task by its explicit name. Task
  `app.worker.tasks.run_athenaeum_build` (single JSON build-id arg)
  executes `app.sphinx.execute.execute_build_sync` — the same executor the
  dev/CI `SC_BUILD_DISPATCH=inline` mode uses.
- **Backup jobs (0039):** Full exports/restores use
  `app.worker.tasks.run_backup_export` / `run_backup_restore`, sharing
  `app.backup.execute` with `SC_BACKUP_DISPATCH=inline`. A dispatch failure
  marks the backup job or build failed (and returns `503`) instead of
  leaving a queued row.
- **C4 packaging:** `scriptorium-worker.service` declares
  `Requires=scriptorium-redis.service` and starts after it (plus
  postgres/network); `CELERY_BROKER_URL` ships in the 0600
  `/etc/scriptorium/config.env` example. Redis 8.10.2 is bundled, so the
  package no longer depends on a distro `redis` package.
- Verified: 2026-10-30 (PyPI/changelog; lock resolved 2026-10-30).
