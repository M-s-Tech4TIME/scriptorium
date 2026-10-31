# Codebase map — "Where is X? Where do I change Y?"

Last updated: 2026-10-31 / Ref: editor/content completion 0038

| Want | Edit |
|---|---|
| TipTap schema / nodes | `frontend/src/editor/EditorSurface.tsx`, `backend/app/conversion/tiptap.py` |
| RST/MyST export + round-trip | `backend/app/conversion/` + `backend/tests/test_roundtrip*` (M2, high coverage) |
| TOC/tree API + UI | `backend/app/routers/nodes.py`, `frontend/src/editor/TreePanel.tsx` (M3) |
| `conf.py`/`toctree` generation | `backend/app/sphinx/sourcegen.py` (generated only, never hand-edit output) |
| Build worker + sandbox | `backend/app/worker/` + `backend/app/sphinx/runner.py` + `packaging/systemd/*` (M4) |
| Published theme | `backend/app/sphinx/theme/scriptorium/` — Scriptorium own theme, engine inherited (0027) |
| API endpoint | `backend/app/routers/` + tests; Pydantic request models live beside their routers |
| Publications / serving | `backend/app/routers/publications.py`, `backend/app/routers/site.py`, `backend/app/serving/` (0035) |
| Media uploads / references / build copying | `backend/app/routers/media.py`, `backend/app/media.py`, `frontend/src/editor/media.ts`, migration `0009_media_assets.py` (0038) |
| Document history / restore | `backend/app/routers/documents.py`, `frontend/src/editor/HistoryPanel.tsx` (0024/0038) |
| Public-name registry / aliases / tombstones | `backend/app/models.py` (`PublicName`), `backend/app/routers/athenaeums.py`, migration `0008_url_durability.py` (0036) |
| DB schema change | `backend/alembic/versions/` + `docs/technology/` + changelog, same commit |
| Packaging/layout | `packaging/nfpm.yaml`, `packaging/systemd/*` (Q1–Q9, FHS) |
| Decision | `docs/decisions/NNNN-*.md` + `brain/DECISIONS-INDEX.md` |

Layout: `frontend/ backend/ packaging/ docs/` (monorepo Q1). Details: `docs/structure/layout.md`.
