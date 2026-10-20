# PROJECT-SUMMARY (brain map, not a copy)

Last updated: 2026-10-21 / Ref: d62784e (C3 green) + C3.5 staged (0020)

- **What:** Scriptorium — self-hosted docs platform. Browser WYSIWYG (TipTap) → valid
  Sphinx source (RST default, MyST opt-in) → sandboxed background build → served HTML.
- **Stack (frozen, Rule 5):** Python 3.12.x, FastAPI 0.143.0, SQLA 2.1.4, Alembic 1.20.0,
  Celery 5.6.3 + Redis, PG 18.x exclusive, Node 24 LTS, React 19.3.x, TS 7.0.2,
  TipTap 3.31.x, Sphinx 9.1.0, docutils 0.22.4 (0.23 gated), MyST 5.1.0, nfpm 2.x.
- **Arch in brief:** monorepo `frontend/ backend/ packaging/`; `web` + `worker` systemd
  units (user `scriptorium`); FHS `/opt`+`/etc/scriptorium`+`/var/lib|log|cache`;
  TipTap-JSON canonical (`tiptap@1`); DB tree `nodes` drives `toctree`; isolated Sphinx venv.
- **Conventions:** Conventional Commits, trunk `main` + `feat/*`, 5 CI gates, Rule 6 zero-skip.
- **Depth:** `docs/architecture/`, `docs/decisions/`, `docs/technology/compatibility-matrix.md`.
- **M2 (conversion) key facts:** docutils 0.22.4 inline markup never nests —
  RST export = one mark per run + fail-loud matrix; MyST carries the editor
  set via HTML paths. See `docs/technology/conversion.md` + 0017.
- **M3 status (as of this sync):** C1–C3.5 green — **0020 athenaeum layer
  LANDED (`4b57c82`+`30dd8b4`+`b6a453d`, CI ×3):** native hierarchy
  `user → Athenaeums → categories (per-Athenaeum, user_id dropped) →
  grimoires (athenaeum_id NOT NULL)`, migration head `0004athenaeum`
  backfills a "Default" per user; delete refuses 409 while grimoires
  remain; nested sidebar endpoint; sharing stays grimoire-level.
  Category/grimoire paths re-homed under `/api/v1/athenaeums/{id}/…`;
  C4 (tree) + C5 (documents) next, then M3 done. Terminology: "grimoire"
  everywhere (0018). Auth surface = login/refresh/logout only. Live API
  tests drive the app via `httpx.ASGITransport` (starlette.testclient
  import warns → Rule 6).
- **Config keys (auth path):** `SECRET_KEY` (JWT), `SCRIPTORIUM_COOKIE_SECURE`
  (prod sets Secure), `REDIS_URL` (limiter, fail-closed when missing),
  `SCRIPTORIUM_RATELIMIT_LOGIN_MAX` / `_WINDOW_S` (0019, optional).
