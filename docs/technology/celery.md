# Technology — Celery 5.6.3 + Redis 7.x

- Versions (locked): Celery 5.6.3 (2026-03-26; 5.7b1 excluded per Rule 5),
  redis-py 5.2.1; broker Redis 7.x (`docker-compose.yml`, M1+).
- Why: 15yr proven queue, Beat + Flower, multi-broker (decision 0005, LTS lens).
- Used: `backend/app/worker/` (Sphinx build jobs); unit `scriptorium-worker.service`.
- **M4 wiring (C3, 0026):** `app/worker/celery_app.py` builds a Celery app
  (`main="scriptorium"`, queue `scriptorium`, JSON serialization) from
  `CELERY_BROKER_URL` (env or `/etc/scriptorium/config.env`) — fail-loud
  when missing. Task `app.worker.tasks.run_athenaeum_build` (single
  JSON build-id arg) executes `app.sphinx.execute.execute_build_sync` —
  the same executor the dev/CI `SC_BUILD_DISPATCH=inline` mode uses.
  **C4 packaging:** `scriptorium-worker.service` declares
  `Requires=redis.service` and starts `After=redis.service` (plus
  postgres/network); `CELERY_BROKER_URL` ships in the 0600
  `/etc/scriptorium/config.env` example.
- Verified: 2026-10-16 (PyPI/changelog; lock resolved 2026-10-16).
