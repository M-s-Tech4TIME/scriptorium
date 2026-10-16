# Technology — argon2-cffi 25.1.0 + PyJWT 2.15.1 (+ httpx 0.28.1 dev)

- Versions (locked): argon2-cffi 25.1.0, PyJWT (`pyjwt`) 2.15.1; httpx 0.28.1 (dev/test).
- Why: Argon2id (OWASP-recommended) for passwords; minimal proven JWT for
  short-lived access + rotating refresh (Q22); httpx is Starlette TestClient's transport.
- Used: `backend/app/auth.py` (hash/verify, mint/decode, `require_membership` 404-on-outsider).
  Keys ≥32 bytes enforced by PyJWT (surfaced via `-W error` in tests).
- Known gap (parked for M2): server-side refresh-reuse detection needs a token store
  (schema addition — owner call).
- Verified: 2026-10-16 (PyPI; lock resolved 2026-10-16).
