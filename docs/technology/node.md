# Technology — Node 24 LTS (build-time only)

- Version: 24.x LTS Krypton (local 24.16.0; CI resolves 24.x). Support to ~2028.
- Why: longest-supported line (Rule 5 + LTS rule); Current 26.x excluded.
  Never shipped in `.deb`/`.rpm` — build host + CI only.
- Used: `frontend/` build (Vite). Engines field pins `24.x`.
- Verified: 2026-10-16 (nodejs.org).
