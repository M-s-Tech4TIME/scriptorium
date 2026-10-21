# 0022 — Folio & Chapter vocabulary (and structure confirmations)

- **Status:** accepted
- **Decided:** 2026-10-21 (owner: Q-M3-14=A, chapter=A, single-membership)
- **Scope:** domain vocabulary of the ordered tree; amends 0010's generic
  `kind` values (`category|page`) inside the library hierarchy.

## Rulings (owner, 2026-10-21)

1. **Q-M3-14=A — Folio is the domain term of record.** Tree `kind 'page'`
   → **`folio`**: DB CHECK (migration 0005), model, and every future API
   payload/doc. Mirrors how 0018 renamed `projects → grimoires` throughout.
2. **Chapter (A).** In-book folder nodes (`kind 'category'`, 0010) collapse
   terminologically with sidebar **Grimoire-categories**. They are renamed
   **`chapter`** in the *same* 0005 migration (zero extra cost; C4 will be
   authored with it). Final spelling of the hierarchy:

   ```
   Library (Athenaeum) → Section (grimoire-category) → Book (Grimoire)
                          Book → Chapter (in-book folder) → Folio (page file)
   ```

3. **Single section membership is correct** (recorded so the pending
   sidebar work never grows a junction table): a Grimoire lives in exactly
   one Grimoire-category or in the Uncategorized bucket. The owner's
   flexibility for "same book on two shelves" is served by the
   **duplication/copy** feature (deep copy tranche after C5, Q-M3-16) —
   independent, editable copies, not shared membership.

## Durability note

All layers are renamable (0021). Nothing in 0005 or the tree endpoints
depends on slug or kind-string stability across time: artifact addressing
is by immutable id/build identity (serving phase decides the URL scheme).
