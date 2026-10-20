# OPEN-QUESTIONS

Last updated: 2026-10-20 / Ref: c26cd7e (M3 C1 green)

| ID | Question | Blocks | Asked |
|---|---|---|---|
| Q-001 | `.github/` at `scriptorium/.github/` invisible to Actions — CLOSED as moot: re-root (Q-002A) puts workflows at repo root again. No shim needed. | — | closed 2026-10-16 |
| Q-002 | Login rate limiting: none in M3 C2 (brute-force surface on `/auth/login`). Options: (A) leave until M4 + do it in a reverse proxy/packaging layer; (B) in-app fixed-window limiter (Redis Celery broker already present). Security note per Rule 2; no urgency gate this milestone. | M4 | 2026-10-20 |

All Plan-mode questions Q1–Q23 answered. Q-002 awaits an owner call (Rule 4).
