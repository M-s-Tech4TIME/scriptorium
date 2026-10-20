# Technology — Redis 8.10.2 (server) + redis-py 5.2.1 (driver)

- Versions: Redis **8.10.2** (latest stable, GA Jul 2026 — CI service pin);
  `redis-py` **5.2.1** (already in requirements.lock as Celery's Redis
  broker driver — part of the Celery-compatible set, Rule 5; no separate
  bump without a Celery-compat owner check).
- Why (0019, Q-002=B): login rate limiting needs counters that survive
  restarts and hold across workers — a TTL'd fixed window in Redis gives
  that with zero new dependencies (Redis is frozen stack via Celery).
- Used: `backend/app/limiter.py` — fixed-window counters
  `limit:login:ip:<peer>` / `limit:login:email:<addr>`, SET NX EX + INCR
  (window anchored at the first failure — INCR never resets TTL), `5`
  failures / `900` s (env: `SCRIPTORIUM_RATELIMIT_LOGIN_MAX` / `_WINDOW_S`)
  — applied on `/auth/login` only.
- Fail-closed: any Redis error ⇒ `503` on login (fail-loud principle).
  `decode_responses=True`; client cached per process and reset per test
  (one event loop per test).
- X-Forwarded-For NOT trusted — peer = socket address; document a proxy
  transition by running uvicorn with `--proxy-headers
  --forwarded-allow-ips` (M4 deployment docs).
- CI: `redis:8.10.2` service on the backend job (`REDIS_URL=redis://…/1`).
  Ops/packaging (M4): `scriptorium-web` systemd gets `Requires=redis` /
  `After=redis` — config doc will carry the same.
- Verified: 2026-10-20 (releases.sh / eosl.date: 8.10.2 current stable).
