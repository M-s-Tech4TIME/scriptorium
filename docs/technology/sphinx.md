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
  output). **The theme is Scriptorium's own, named `scriptorium` —
  decision 0027:** built from the ground up (no Sphinx builtin /
  third-party template inheritance, `theme.conf` has no parent;
  furo/rtd/alabaster-as-final rejected), while the Sphinx **engine** is
  fully inherited/utilized — builder, environment, toctree/prev-next/
  genindex, `searchindex.js` client search, Pygments. The engine's
  client JS (`searchtools.js`, `doctools.js`, `sphinx_highlight.js`,
  `language_data.js`) is **vendored at build time** from the installed
  pinned Sphinx into each workspace (never committed, never fetched);
  the theme's search DOM ids are pinned to what the vendored
  `searchtools.js` expects and are bumped together with the engine.
  Implementation template surface: `layout.html`, `page.html`,
  `search.html`, `genindex.html` + one stylesheet
  (`backend/app/sphinx/theme/scriptorium/`); brand injection /
  custom-CSS hooks / dark-mode policy are serving-phase (0026 mandate
  2). Edge rulings
  E1–E3: empty Athenaeum → 422; empty book → skip + log note; one build
  per Athenaeum at a time (409, enforced in C3). **C3 round-trip
  refinements:** every staged toctree entry is an absolute `</docname>`;
  every referenced page carries its node/book title as a generated top
  section (toctree titles come from the target's own titles); `.md`
  pages emit the MyST fenced `{toctree}` (masters stay RST); the save
  path itself exports sources, so staged builds are exporter-clean by
  construction.
- **Runner (M4-C3, 0026 P3):** `app/sphinx/runner.py` materializes the
  plan into `/var/lib/scriptorium/builds/{build_id}/` (FHS default;
  `SC_BUILD_ROOT` dev override) and runs `python -m sphinx -W -b html .
  _build/html` — `-W` is the `ok` gate. Child env is a strict whitelist
  (`PATH`, `LC_ALL`, `PYTHONHASHSEED=0`, `HOME` inside the workspace;
  `app.sphinx.runner.child_env`); RLIMITs CPU 600 s / AS 1.5 GiB / FSIZE
  512 MiB / core 0 (`SC_SPHINX_*` overrides); wall timeout 900 s.
  Honest limitation (P3 ruled out containers): egress isolation comes
  by construction of the pinned stack, not a kernel namespace.
  Artifact on `ok`: `{SC_ARTIFACT_ROOT}/{athenaeum}/{build_number}/`
  (html/ + build.log); `SC_BUILD_PYTHON` defaults to `sys.executable`
  pre-packaging (isolated build venv required in production, C4).
- Verified: 2026-10-16 (sphinx-doc.org/PyPI; lock resolved 2026-10-16).
