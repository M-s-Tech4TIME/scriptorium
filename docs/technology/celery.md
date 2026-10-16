# Technology — Celery 5.6.3 + Redis 7.x

- Versions (locked): Celery 5.6.3 (2026-03-26; 5.7b1 excluded per Rule 5),
  redis-py 5.2.1; broker Redis 7.x (`docker-compose.yml`, M1+).
- Why: 15yr proven queue, Beat + Flower, multi-broker (decision 0005, LTS lens).
- Used: `backend/app/worker/` (Sphinx build jobs); unit `scriptorium-worker.service`.
- Verified: 2026-10-16 (PyPI/changelog; lock resolved 2026-10-16).
