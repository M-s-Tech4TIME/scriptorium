# Codebase map — "Where is X? Where do I change Y?"

Last updated: 2026-10-16 / Ref: uncommitted

| Want | Edit |
|---|---|
| TipTap schema / nodes | `frontend/src/editor/` (M2) |
| RST/MyST export + round-trip | `backend/app/convert/` + `tests/test_roundtrip*` (M2, high coverage) |
| TOC/tree API + UI | `backend/app/routers/nodes.py`, `frontend/src/components/toc/` (M3) |
| `conf.py`/`toctree` generation | `backend/app/sphinx/project.py` (generated only, never hand-edit output) |
| Build worker + sandbox | `backend/app/worker/` + `systemd units` in `packaging/` (M4) |
| Published theme | `backend/app/sphinx/theme/` extending Furo (M4) |
| API endpoint | `backend/app/routers/` + schema in `backend/app/schemas/` + test |
| DB schema change | `backend/alembic/versions/` + `docs/technology/` + changelog, same commit |
| Packaging/layout | `packaging/nfpm.yaml`, `packaging/systemd/*` (Q1–Q9, FHS) |
| Decision | `docs/decisions/NNNN-*.md` + `brain/DECISIONS-INDEX.md` |

Layout: `frontend/ backend/ packaging/ docs/` (monorepo Q1). Details: `docs/structure/layout.md`.
