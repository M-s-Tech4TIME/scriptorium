# Technology — Sphinx 9.1.0 + docutils 0.22.4 + MyST-Parser 5.1.0

- Versions (locked): Sphinx 9.1.0 (2025-12-31), docutils 0.22.4 (0.23 gated —
  MyST 5.x upper-bounds docutils; verify in CI before bump, decision 0003),
  MyST-Parser 5.1.0 (2026-05-13, needs Sphinx ≥8<10, markdown-it-py ~4.2).
- Why: documentation engine core; RST default + MyST opt-in per project (§5).
- Used: isolated build venv only (never app deps, Rule 5.4); `backend/app/sphinx/`;
  generated-only `conf.py`, allowlisted extensions (threat model).
- **Staging contract (M4-C2, 0026):** `app/sphinx/sourcegen.py` plans the
  site — per-book directories (docname `book/<…path>/<leaf>`, leaf `index`
  mangled to `index-p`), folio bodies exported **directly from the stored
  canonical TipTap** (the `source_text` cache is never trusted for
  builds), chapters/folio-parents → `toctree` containers, one `conf.py`
  per Athenaeum (MyST/`extensions=["myst_parser"]` only when some book is
  `myst`; master docs are always RST toctree pages). Build sources are
  deterministic (`plan_site` → identical bytes for identical input) and
  fail loud (`StagingError` → build failed, never corrected-guess
  output). **Interim theme = `alabaster` placeholder; the curated default
  theme lands in C3 (0026 mandate 2).** Edge rulings E1–E3: empty
  Athenaeum → 422; empty book → skip + log note; one build per Athenaeum
  at a time (C3).
- Verified: 2026-10-16 (sphinx-doc.org/PyPI; lock resolved 2026-10-16).
