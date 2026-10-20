# 0019 — Login rate limiting (Q-002 resolved)

- **Status:** accepted
- **Decided:** 2026-10-20 (owner)
- **Scope:** brute-force resistance on `/api/v1/auth/login` (OWASP ASVS 2.2.x)

## Decision (owner picked **Option B**)

In-app fixed-window limiter, Redis-backed, in-process — not deferred to a
reverse-proxy layer (packaging bundles no proxy; the default install must
meet the control itself).

- **Mechanism:** Redis `INCR` + `EXPIRE`, fixed window 15 min
  (`LOGIN_WINDOW_SECONDS = 900`), max 5 failures
  (`LOGIN_MAX_FAILURES = 5`). Two counters must both be under limit:
  per-source-IP (`limit:login:ip:<peer>`) and per-email
  (`limit:login:email:<addr>`).
- **Scope:** `/auth/login` only. Refresh is single-use rotation (0017) and
  logout idempotent — no limit value there.
- **Reply shape:** over-limit → `429` + `Retry-After` (remaining window
  seconds) + uniform `{"detail": ...}`; audit_log row `auth_rate_limited`
  per trip.
- **Failure of Redis = fail-closed:** limiter unavailable → `503`, login
  refused (fail-loud project principle 0017; availability sacrifice is the
  owner's accepted trade-off).
- **Counters clear on successful login** (standard ASVS behaviour).
- **X-Forwarded-For is NOT trusted** — the limiter keys on the socket peer
  (`request.client.host`). If an admin fronts a proxy later, uvicorn
  `--proxy-headers --forwarded-allow-ips` becomes the explicit trust
  boundary (documented in redis.md / deployment docs at M4).
- **Dependency:** `redis-py` — already locked at 5.2.1 (present as the
  Celery Redis broker driver). No new dependency introduced.
- **Environment overrides:** `SCRIPTORIUM_RATELIMIT_LOGIN_MAX`,
  `SCRIPTORIUM_RATELIMIT_LOGIN_WINDOW_S` (validated ints; bad values fail
  loud at first use).

## Alternatives rejected

- **A (reverse proxy / M4 advisory):** no proxy is part of the frozen
  packaging; control would never exist in default installs → Rule 2 gap.
- **C (in-memory / PG table):** in-memory breaks on restarts + multiple
  workers; PG table needs migration + cleanup cron for what Redis TTL does
  free.

## Test/CI plan

- Tests skip unless `REDIS_URL` is set (`needs_redis`, same pattern as
  `needs_db`); CI adds a `redis:8` service to the backend job.
- Cases: 5 failures → 429+Retry-After; per-email key trips independently;
  success clears; window resets; fail-closed shape.
