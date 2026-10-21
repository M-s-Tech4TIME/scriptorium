# 2026-10-21 — M3 C3.7: folio & chapter vocabulary (0022)

Commits: this tranche · Author: alsechemist (with OpenCode) · Milestone M3, tranche C3.7

## What changed

The owner sharpened the domain vocabulary (decision **0022**): the
hierarchy is now spelled `Library (Athenaeum) → Section (grimoire-category)
→ Book (Grimoire) → Chapter (in-book folder) → Folio (page file)`, and the
tree's `kind` values follow:

- **Migration `0005_chapters_folios`** (append-only; `ck_nodes_kind`
  dropped first so `chapter`/`folio` can be written, data rewritten,
  CHECK recreated with the same name; downgrade is the exact mirror).
- **`models.Node`**: CHECK `kind IN ('chapter','folio')` + docstrings.
- **GLOSSARY**: Folio/Chapter/Section definitions recorded for the brain.
- **Docs:** data-model nodes line + migration list; 0022 record (also
  memorializes the owner's **single-membership confirmation** — a Grimoire
  belongs to exactly one Section or Uncategorized; "same book on two
  shelves" is served by the duplication tranche after C5, not membership).
- No API surface changes yet: C4 (tree endpoints) will be authored with
  `chapter|folio` from day one; the TipTap `kind` fields in `conversion/`
  are unrelated and untouched.

## Tests

`test_migration.py` roundtrip covers 0005 live in CI (11 tables unchanged;
kind values exercise both directions). Offline: `45 passed, 25 skipped`.

## Next

C4 — tree endpoints on the new vocabulary (0023).
