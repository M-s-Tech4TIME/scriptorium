# 0024 — Folio documents: save, concurrency, import, history (M3 C5)

- **Status:** accepted
- **Decided:** 2026-10-21 (mechanics ratified in 0018 Q-M3-2=A / Q-M3-3=A;
  role mapping + edge semantics recorded here as disclosed micro-defaults)
- **Scope:** the folio content API — `routers/documents.py` under
  `/api/v1/grimoires/{grimoire_id}/nodes/{node_id}`.

## Ratified mechanics (0018)

- **Optimistic concurrency (Q-M3-2=A):** PUT carries `expected_version`;
  mismatch → `409` with expected/current in the detail, **no mutation and
  no audit row**. Every successful save bumps `version` and appends an
  immutable `document_history` row (Q-M3-2=A).
- **Source cache (Q-M3-3=A):** `source_text` is re-derived **server-side
  from the canonical TipTap JSON** on every save via the M2 exporter for
  the Grimoire's `source_format` — client-supplied source is never stored
  as-is; TipTap stays canonical (0010/Q21).
- **Import from source (Q-M3-3=A):** PUT may instead carry `source_text`;
  it runs through the M2 importer (`import_document`) and `ConversionError`
  → `422` with the converter's message. The imported TipTap is then
  canonicalized and saved like any other save (the stored cache is the
  export of the canonical form, not the caller's raw text).

## Endpoint semantics

| Route | Access | Notes |
|---|---|---|
| GET `/document` | any member | `404` until the first save (no implicit empty row) |
| PUT `/document` `{tiptap_json \| source_text, expected_version}` | **editor or owner** | exactly one content field; `expected_version` required — `0` asserts "not created yet" (creates v1); concurrency check runs **before** conversion; save = version+1 + history append + audit `document_saved` |
| GET `/document/history` | any member | metadata list `{version, author, at}` — blobs omitted (restore is a later phase) |

## Micro-defaults (owner-vetoable, disclosed)

- **D2 extended to content:** viewers read; editing needs `editor`/`owner`
  (member under role → `403`). This is the only reading consistent with
  the M1 role vocabulary.
- `expected_version = 0` is the create-assertion; version numbering starts
  at 1 (0001 `server_default`).
- Canonical-save check: `tiptap_json` must be an object with
  `type == "doc"`; stored through `canon_doc` (deterministic exports).
- Trust-boundary size caps (Rule 2, DoS bound): `source_text` ≤ 1,000,000
  chars; serialized `tiptap_json` ≤ 2,000,000 chars → `422` otherwise.
- PUT validation order: body shape → concurrency → conversion → save.
- Audit action `document_saved` (meta: `node_id`, `version`, `imported`);
  GETs and refused PUTs write nothing.
