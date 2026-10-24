# PROJECT-SUMMARY (brain map, not a copy)

Last updated: 2026-10-24 / Ref: 1add6c8 M4-C4 pushed, CI ×3; M4 implementation complete

- **What:** Scriptorium — self-hosted docs platform. Browser WYSIWYG (TipTap) → valid
  Sphinx source (RST default, MyST opt-in) → sandboxed background build → served HTML.
- **Stack (frozen, Rule 5):** Python 3.12.x, FastAPI 0.143.0, SQLA 2.1.4, Alembic 1.20.0,
  Celery 5.6.3 + Redis, PG 18.x exclusive, Node 24 LTS, React 19.3.x, TS 7.0.2,
  TipTap 3.31.x, Sphinx 9.1.0, docutils 0.22.4 (0.23 gated), MyST 5.1.0, nfpm 2.x.
- **Arch in brief:** monorepo `frontend/ backend/ packaging/`; `web` + `worker` systemd
  units (user `scriptorium`); FHS `/opt`+`/etc/scriptorium`+`/var/lib|log|cache`;
  TipTap-JSON canonical (`tiptap@1`); DB tree `nodes` drives `toctree`;
  builds = limited-subprocess Sphinx 9.1.0 sandbox, `-W` (0026).
- **Conventions:** Conventional Commits, trunk `main` + `feat/*`, 5 CI gates, Rule 6 zero-skip.
- **Depth:** `docs/architecture/`, `docs/decisions/`, `docs/technology/compatibility-matrix.md`.
- **M2 (conversion) key facts:** docutils 0.22.4 inline markup never nests —
  RST export = one mark per run + fail-loud matrix; MyST carries the editor
  set via HTML paths. See `docs/technology/conversion.md` + 0017.
- **M4 status (as of this sync):** M3 C1–C6 complete, green ×3
  (0021–0025 landed). **M4-C1 + C2 + C3 + C3.5 complete:** 0026
  per-Athenaeum numbered builds, `sourcegen.py` deterministic staging,
  sandbox runner/Celery/`builds` endpoints; migration head
  `0006buildsite`. The theme is Scriptorium's own, from scratch
  (0027–0034; engine inherited incl. vendored JS, first-party search,
  Inter, feedback batches 0029–0034). **M4-C4 complete/pushed
  (`1add6c8`, CI ×3):** isolated `/opt/scriptorium/build-venv` from a 27-pin
  engine-only lock, config example/queue/build keys, both units
  `Requires=redis`/`After=redis`, postinst artifacts/config seed/
  build-venv check, manual docutils-0.23 probe (58 passed; pin stays
  0.22.4), M4 report. Suite 87 passed / 36 skipped. Owner ruled the
  artifact to be a portable static website + design mandates (security
  parity; structure locked, skin open). Terminology: "grimoire"
  everywhere (0018). Auth surface = login/refresh/logout only. Live
  API tests drive the app via `httpx.ASGITransport`
  (starlette.testclient import warns → Rule 6).
- **Config keys:** `SECRET_KEY` (JWT; empty fails loud), `DATABASE_URL`,
  `SCRIPTORIUM_COOKIE_SECURE` (prod sets Secure), `REDIS_URL` (limiter,
  fail-closed when missing), `CELERY_BROKER_URL` (worker), and the
  `SC_BUILD_*` / `SC_SPHINX_*` build paths/limits; optional
  `SCRIPTORIUM_RATELIMIT_LOGIN_MAX` / `_WINDOW_S` (0019). Packaged
  example at `packaging/config.env.example` (0600 seed).
