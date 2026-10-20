# PROJECT-SUMMARY (brain map, not a copy)

Last updated: 2026-10-20 / Ref: c26cd7e (M3 C1 green) + C2 staged

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
- **M3 status (as of this sync):** C1 green (grimoire rename + categories,
  migration head `0003grimoire`); C2 staged (auth/session endpoints);
  C3–C5 next. Terminology: "grimoire" everywhere (0018). Auth surface =
  login/refresh/logout only. Live API tests drive the app via
  `httpx.ASGITransport` (starlette.testclient import warns → Rule 6).
