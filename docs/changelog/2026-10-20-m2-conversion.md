# 2026-10-20 — M2 conversion layer (TipTap ↔ RST/MyST)

- `backend/app/conversion/` package: one docutils-walking importer for both
  formats and two writers.
  - `tiptap.py`: typed builders + `canon_doc` (sorted marks, no empty
    paragraphs/containers, canonical attrs, code text without trailing `\n`).
  - `import_doc.py`: `import_document(text, source_format)` parses RST or
    MyST (via `myst_parser.parsers.docutils_.Parser`) into one doctree walk;
    docutils level ≥3 system messages raise straight away, level 1–2
    tolerated. MyST hard breaks arrive as html `<br />` + a latex twin raw
    (ignored); `<s>/<u>/<em>/<strong>` tags thread a stack so sibling
    closers map back to marks; unclosed tags raise.
  - `export_rst.py` / `export_myst.py`: line-start guards, CJK-safe heading
    bars (`docutils.utils.column_width`), RST line-block for hard breaks,
    CommonMark hard breaks (`\` EOL), role prelude for strike/underline.
- Probe-verified docutils 0.22.4 facts (wheel in `docs/decisions/
  0017-m2-design.md`): inline markup does not nest at all (strong/emphasis
  content ships literal; references nest nowhere) → RST export accepts one
  mark or a bare link per run, fails loud otherwise; inline literals and
  role content reject edge spaces; heading levels are sequential from the
  first style (skips fail loud); single-section docs collapse to
  title/subtitle directly under the document (handled).
- MyST keeps everything the editor set can express: `***bold italic***`,
  code+strike/underline runs, link+bold via tags, code-span edge spaces via
  pad tricks.
- Tests: 40 conversion cases (round-trip JSON equality + source
  idempotency, fail-loud matrix, CJK bar width, title/subtitle collapse).
- mypy: `docutils.*` override moved into effect — CI now runs
  `mypy --config-file backend/pyproject.toml backend/` so the approved
  per-module override loads; strict also typed three JSONB columns.
- See `docs/decisions/0017-m2-design.md` (Q-M2-1=A, Q-M2-2=A) and
  `docs/technology/conversion.md`.
