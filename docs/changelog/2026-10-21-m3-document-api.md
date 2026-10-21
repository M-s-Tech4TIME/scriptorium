# 2026-10-21 — M3 C5: folio documents — save, concurrency, import, history (0024)

Commits: this tranche · Author: alsechemist (with OpenCode) · Milestone M3, tranche C5

## What changed

The ratified document semantics (0018 Q-M3-2=A / Q-M3-3=A) are live as
`routers/documents.py` under
`/api/v1/grimoires/{grimoire_id}/nodes/{node_id}`:

- **GET `/document`** — any member; `404` until the first save.
- **PUT `/document`** — editor/owner (viewer → `403`; 0024 extends D2=A to
  content). Body carries `expected_version` plus exactly one of
  `tiptap_json` (canonical mode) or `source_text` (import mode):
  - mismatch → `409` with expected/current, **nothing written, no audit**;
  - `expected_version: 0` asserts "not created yet" and creates v1;
  - import mode runs the M2 importer; `ConversionError` → `422` with the
    converter's message;
  - every save canonicalizes (`canon_doc`), re-derives `source_text`
    server-side with the grimoire's exporter (`source_format` authority),
    bumps the version, and appends an immutable `document_history` row.
- **GET `/document/history`** — any member; metadata list (blobs omitted;
  restore is a later phase).
- **Trust-boundary caps** (Rule 2): source ≤ 1M chars, serialized TipTap
  ≤ 2M chars → `422`; canonical shape requires `type == "doc"`.
- **Audit:** `document_saved` (meta `node_id`/`version`/`imported`); reads
  and refused writes stage nothing.
- models: `Document.updated_at` already carried ORM `onupdate` — no schema
  change in this tranche (0001–0005 untouched).
- **Docs:** 0024 record, api.md "Folio documents" section + audit footer,
  brain.

## Tests

`tests/test_document_api.py` (2 live-PG cases): lifecycle (create-from-0,
bump, stale-writer 409 with detail, history versions/author/metadata,
viewer read/403, outsider 404, audit) and import/errors (rst + myst
imports through the grimoire's format, `ConversionError` → 422,
exactly-one-field + canonical shape + size caps → 422, cross-grimoire
addressing → 404). Offline `45 passed, 31 skipped`.

## Next

C6 — grimoire duplication (deep copy; Q-M3-16) → M3-complete report → M4.
