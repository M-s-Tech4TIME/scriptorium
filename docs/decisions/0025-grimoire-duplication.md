# 0025 — Grimoire duplication (Q-M3-16a–e)

- **Status:** accepted
- **Decided:** 2026-10-21 (owner ruled all five sub-decisions)
- **Scope:** the copy feature serving the 0022 single-membership ruling —
  "same book on two shelves" means an independent deep copy, never shared
  membership.

## Owner rulings

| Sub | Ruling |
|---|---|
| a | **Caller-supplied slug, optional auto**: the body may carry `slug` (regex `[a-z0-9-]+` else `422`; global collision → `409`); when omitted the API derives one — `source-slug-copy`, then `-copy-2`, `-copy-3`, … (first free; attempt cap 100 → `409`). |
| b | **Owner-only membership**: the copy's roster is empty except its owner (the duplicator). Copies start private; sharing remains a deliberate act. |
| c | **Current version only**: each folio document is copied at its head content as **v1** with the cached source; no history rows are cloned (the original's history is its own provenance). |
| d | **Any library the caller owns**: body may carry `athenaeum_id` (default = the source's). Foreign/unknown target → `404`, mirroring the ratified move rule. |
| e | **Copies of copies allowed**; no lineage tracking in M3 (derivative-tracking stays a potential later phase beside URL durability). |

## Endpoint

`POST /api/v1/grimoires/{grimoire_id}/duplicate`
`{athenaeum_id?, slug?, title?}` — **source owner only**; the copy is a
brand-new grimoire owned by the caller.

## Deep-copy semantics

- New `grimoires` row: source's `source_format`/`theme` copied;
  `created_by` = caller; audit `grimoire_duplicated`.
- **Category (micro-default, disclosed):** same-library copies inherit the
  source's category; cross-library copies land `NULL` (Uncategorized) —
  categories are Athenaeum-scoped (0020), so a foreign category reference
  would be invalid.
- **Title (micro-default, disclosed):** omitted title → `"<source title> (copy)"`.
- **Tree:** nodes copied in parent-first order preserving kind, title,
  slug, and sibling positions under a fresh id map (per-sibling-set slug
  uniqueness re-satisfied inside the new grimoire by construction).
- **Documents:** one `documents` row per source folio document — head
  `tiptap_json` + cached `source_text`, `version = 1`, `updated_by` =
  caller. **History ruling clarified on implementation:** the source's
  v1..vN provenance is never cloned; the copy's own v1 save leaves
  exactly one new history row (authored by the duplicator at copy time),
  preserving the C5 invariant that every version leaves a trace.
- All in one transaction; source is untouched and remains editable.

## Micro-defaults (owner-vetoable, disclosed)

- **Role:** duplication is owner-only on the source (member under role →
  `403`) — structure-level mutation per D2=A; editors read content
  anyway, and the copy would be theirs, so a future relaxation is a
  one-line change.
- Auto-slug attempt cap: 100 candidates → `409` (unreachable in practice).
