# Technology — Redis 8.10.2 (bundled server) + redis-py 6.4.0

- Versions: Redis **8.10.2** (latest stable) is built from the pinned source
  tarball at package-build time and bundled at `/opt/scriptorium/redis`.
  `redis-py` **6.4.0** is the latest driver compatible with the pinned
  Celery/kombu set (`kombu 5.6.2` requires `redis<6.5`).
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
- Packaging: `packaging/scripts/build-redis.sh` verifies the source
  SHA-256 (`b9ffee…c02b3`), builds core `redis-server` + `redis-cli`, and
  packages them at `/opt/scriptorium/redis`. The new
  `scriptorium-redis.service` is `Type=notify`, runs as the `scriptorium`
  user, and is required by both web and worker units. The packaged config
  seeds `/etc/scriptorium/redis.conf` (localhost-only, append-only AOF,
  `noeviction`) without overwriting an existing file.
- Dev/CI: `docker-compose.yml` uses `redis:8.10.2-alpine` with AOF and a
  healthcheck; the backend CI service pins `redis:8.10.2`.
- Verified: 2026-10-30 — bundled `redis-server v=8.10.2` starts from the
  packaged config and answers `PONG`; Redis packaging contract tests pass.
