# 2026-10-20 — Login rate limiting (M3 C2.5, decision 0019)

- Owner resolved Q-002: **Option B** — in-app Redis-backed fixed-window
  limiter on `/auth/login` (record: `docs/decisions/0019-…`; OPEN-QUESTIONS
  Q-002 closed).
- `app/limiter.py`: counters `limit:login:ip:<peer>` +
  `limit:login:email:<addr>`; SET NX EX + INCR (window anchored at the
  first failure); 5 failures / 900 s, env-tunable; success clears; the
  tighter counter binds.
- Router flow: limiter check precedes verification → even the CORRECT
  password gets `429` + `Retry-After` (+ audit `auth_rate_limited`) once
  the window trips. X-Forwarded-For is NOT trusted (socket peer only).
- Fail-closed: Redis unreachable/misconfigured → `503` on login
  (fail-loud principle); unknown-PEER-IP fallback kept for scope-less
  in-proc test transport only.
- Additions to `main.py`-mounted router only — no new dependencies:
  redis-py 5.2.1 was already locked as Celery's broker driver.
- CI: `redis:8.10.2` service (latest stable verified 2026-10-20) added to
  the backend job; `REDIS_URL` env → `needs_redis` skip pattern.
- Tests: `test_ratelimit_api.py` (4 cases: clean-start + key separation;
  5-failures→429+Retry-After even with correct password; success clears;
  outage→503). Offline gates stay green (skips).
- Docs: `docs/technology/redis.md` (new, Rule 5 pin), auth.md limiter
  section, brain sync, decision 0019.
