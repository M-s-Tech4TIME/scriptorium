# PROJECT-SUMMARY (brain map, not a copy)

Last updated: 2026-10-21 / Ref: M4-C2 landed (3a15b52)

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
  (0021–0025 landed). **M4-C1 + C2 + C3 LANDED:** 0026 per-Athenaeum
  numbered builds + `app/sphinx/sourcegen.py` deterministic staging +
  sandbox runner/Celery/`builds` endpoints (`c6c407d`+`fadef93`+
  `1e1637e` CI ×3); migration head `0006buildsite`;
  suite baseline `66 passed, 36 skipped`. **0027 recorded: the theme is
  Scriptorium's own, from scratch (no builtin/third-party inheritance;
  engine fully inherited incl. vendored engine JS)** — C3.5
  implementation awaits the owner's design-consult tokens; then C4
  packaging. Owner ruled the artifact to be a portable static
  website + design mandates (security parity; structure locked,
  skin open). Terminology: "grimoire" everywhere (0018). Auth
  surface = login/refresh/logout only. Live API tests drive the app
  via `httpx.ASGITransport` (starlette.testclient import warns →
  Rule 6).
- **Config keys (auth path):** `SECRET_KEY` (JWT), `SCRIPTORIUM_COOKIE_SECURE`
  (prod sets Secure), `REDIS_URL` (limiter, fail-closed when missing),
  `SCRIPTORIUM_RATELIMIT_LOGIN_MAX` / `_WINDOW_S` (0019, optional).
