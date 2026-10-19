# Conversion layer (M2, decision 0017)

TipTap JSON (`tiptap@1`) ↔ reStructuredText / MyST. Single canonical form for
storage; the converters are the only place that knows both representations.

```
backend/app/conversion/
├── tiptap.py      typed builders + canon_doc (the canonicalizer)
├── import_doc.py  import_document(text, "rst" | "myst") → TipTap JSON
├── export_rst.py   TipTap JSON → RST
└── export_myst.py  TipTap JSON → MyST (CommonMark)
```

## Canonical TipTap form (`tiptap_doc_canon`)

`canon_doc` makes round trips deterministic

- marks sorted alphabetically (`bold, code, italic, link, strike, underline`),
- empty paragraphs / empty containers dropped,
- falsy attrs omitted: `start` 1 on ordered lists, empty `language`,
- code-block text loses its trailing newline,
- `hardBreak` is a node (never a `"\n"` text node).

Writers additionally merge adjacent text runs that share identical marks —
the same invariant the importer guarantees, so JSON output is stable
independent of input tokenization.

## Import (both formats, one walker)

Both sources parse via docutils: RST via `docutils.core.publish_doctree`,
MyST via `myst_parser.parsers.docutils_.Parser`. `report_level`/`halt_level`
are pushed to 5 (nothing printed); the walker inspects system messages
itself

- level ≥ 3 (error/severe) → `ConversionError` — import fails loudly,
- level 1–2 (info/warning) → tolerated (e.g. non-consecutive headings).

Shape notes (probe-verified, docutils 0.22.4 / myst-parser 5.1.0)

- code language lives in `literal_block` classes (`['code', 'python']`);
  plain `::` blocks have no class.
- RST strike/underline come from `.. role:: strike|underline` as `inline`
  nodes carrying a class; role content is plain text (no nested markup).
- MyST strike/underline arrive as raw HTML markers `<s>…</s>`, `<u>…</u>`,
  plus `<em>/<strong>` for edge-space runs the asterisk delimiters
  cannot carry. The import walk threads a tag stack so sibling closers
  match; unbalanced tags raise.
- MyST hard breaks are TWO raw siblings: html `<br />` and a latex twin
  containing only backslashes (the twin is ignored). A hard break becomes a
  `"\n"` run that splits into `hardBreak` nodes — real text never contains
  `\n` (inline whitespace is collapsed to one space on parse).
- docutils builds heading levels sequentially from style-introduction
  order. Single-section docs collapse title/subtitle directly under the
  document; a hand-written `# A` followed immediately by `## B` maps to the
  same title/subtitle convention. The importer restores both (level 1 and
  level 2). Skipped levels are not representable (see export).
- Tables, images, footnotes, math and other out-of-scope constructs raise
  `ConversionError` (Q-M2-1 = editor starter-kit set only).

## Export

Common structure: hard breaks → escaped text runs; paragraph lines are
guarded so text cannot re-parse as structure (leading `.. `, bullets
`* - +`, `#`, enumerator dots `5\. `, `=`/`-`/`_*` bars setext/transition
lookalikes, parenthesized enumerators).

### RST specifics

- heading characters `{1: '=', 2: '-', 3: '~', 4: '^', 5: '"', 6: '+'}`,
  bar width from `docutils.utils.column_width` (CJK-safe); level 1 emits
  overline + underline.
- paragraph internal breaks → `.. line-block::`.
- inline literals use double backticks (single = interpreted text), content
  is raw (no escape processing inside literals), delimiters widened past
  embedded backticks.
- strike/underline via `.. role::` prelude emitted on first use.
- fail-loud (docutils 0.22.4 does not nest inline markup

  - more than one mark on a run (bold+italic, code+anything, …),
  - link plus any text mark (references nest nowhere, content is plain),
  - edge spaces inside marked/link runs (`**\ x**` loses the space),
  - heading level skips (levels are sequential over reintroduced styles).

### MyST specifics

- CommonMark; fenced code blocks; `\<`-style punctuation escapes.
- `***x***` for bold+italic; code spans keep single-side edge spaces and
  pad both-side spaces (CommonMark strips one space per side only when
  both edges are spaces).
- strike/underline as `<s>/<u>` raw HTML; edge-space bold/italic as
  `<strong>/<em>` — all re-imported as marks by the importer.
- heading level skips fail loud like RST (docutils builds the same
  hierarchy from the token stream).

## Guarantees

For every corpus case in `tests/test_roundtrip.py`, in both directions

1. `export(canon(doc))` → `import` → JSON equals the canonical doc,
2. re-exporting the imported JSON returns the identical source text
   (idempotency).
