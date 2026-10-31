# Technology — argon2-cffi 25.1.0 + PyJWT 2.15.1 + redis-py 6.4.0 (+ httpx 0.28.1 dev)

Last updated: 2026-10-30 / Ref: stack-upgrade phase (0037)

- Versions (locked): argon2-cffi 25.1.0, PyJWT (`pyjwt`) 2.15.1,
  redis-py 6.4.0 (Celery/kombu-compatible cap); httpx 0.28.1 (dev/test).
- Why: Argon2id (OWASP-recommended) for passwords; minimal proven JWT for
  short-lived access + rotating refresh (Q22); httpx 0.28.1 also drives
  in-process ASGI tests (`httpx.ASGITransport` — `starlette.testclient` is
  deprecated in this stack and its import raises a Rule-6 warning).
- Used: `backend/app/auth.py` (hash/verify + `verify_dummy` enumeration
  guard, mint/decode, family store, `require_membership` 404-on-outsider);
  `backend/app/routers/auth.py` (M3 C2 endpoints, decision 0018 Q-M3-1=A).
- Keys ≥32 bytes enforced by PyJWT (surfaced via `-W error` in tests).

## M3 auth/session endpoints (C2)

- `POST /api/v1/auth/login` — email+password → `{"access_token", "token_type":
  "bearer"}` + `Set-Cookie: scriptorium_refresh` (HttpOnly, SameSite=Lax,
  path=/, 7 d max-age, Secure when `SCRIPTORIUM_COOKIE_SECURE` truthy) and
  `scriptorium_access` (the same 15-minute access token, HttpOnly,
  SameSite=Lax, path=/a, Secure in production; 0035 B3). Refresh rotates
  both; logout clears both.
  Unknown email burns an argon2 dummy verify (timing-uniform, no account
  enumeration); bad credentials → uniform `401 {"detail": "Invalid credentials."}`.
- `POST /api/v1/auth/refresh` — rotates the cookie through the M2 family
  store; reuse of any rotated-out cookie → `401` and the whole family is
  burned (0017). Missing cookie → `401`.
- `POST /api/v1/auth/logout` — revokes the refresh family (`reason=logout`),
  clears the cookie, `204`; junk/expired cookie still clears (idempotent).
- Users are seeded by CLI only — no open registration (Q-M3-1=A).
- Login rate limiting (0019, Q-002=B): Redis fixed window, 5 failures /
  15 min keyed per-IP (socket peer, XFF untrusted) and per-email;
  over-limit → `429` + `Retry-After` + audit `auth_rate_limited`;
  success clears; Redis outage → `503` (fail-closed). See
  `docs/technology/redis.md`.
- Tests: `backend/tests/test_auth_api.py` (live PG18 in CI; rotation,
  reuse-burn, logout revocation, enumeration-shape 401s) and
  `backend/tests/test_ratelimit_api.py` (live Redis; window trip, key
  separation, success reset, fail-closed). Both drive the app via
  `httpx.ASGITransport`.

- Known gap resolved (0019): per-IP login rate limiting shipped in M3 C2.5;
  M4 packaging docs add the `After=redis` systemd note + proxy guidance.
- Verified: 2026-10-30 (PyPI; lock resolved 2026-10-30); endpoints 2026-10-20.
