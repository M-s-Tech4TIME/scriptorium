# PROJECT-SUMMARY (brain map, not a copy)

Last updated: 2026-10-16 / Ref: uncommitted (M0 seed)

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
