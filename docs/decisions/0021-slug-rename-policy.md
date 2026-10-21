# 0021 — Slugs are renamable across the whole library hierarchy

- **Status:** accepted
- **Decided:** 2026-10-21 (owner, D0=B + 0018-amendment ruling)
- **Scope:** mutability of every URL-name in the hierarchy; amends 0018
  (grimoire slugs effectively immutable) and supersedes the C3.5
  micro-default "athenaeum slug immutable after creation".

## Ruling

The owner wants **each and every layer renamable** — Athenaeum, Grimoire,
and (from C4) the book's tree nodes (chapters/folios). Grimoire-categories
have no slug by design (sidebar entity); their `name` rename via PATCH has
always existed and is unaffected.

## Uniform rename rules (all layers)

- Rename = optional `slug` field on the entity's PATCH body.
- Allowlist `[a-z0-9-]+` → otherwise `422`; explicit `null` → `422`
  (slugs never "float").
- Uniqueness scope is unchanged and stays database-enforced:
  - Athenaeum: `UNIQUE(owner_id, slug)` (per owner) → violation `409`;
  - Grimoire: global `slug UNIQUE` → violation `409`;
  - Tree nodes: per-sibling-set partial unique indexes
    (`uq_nodes_root_slug` / `uq_nodes_child_slug`, 0001) → violation `409`.
- A rename writes **no new audit actions** — the existing
  `athenaeum_patched` / `grimoire_patched` metas record the change
  (`slug_changed` / `changes=["slug"]`). `grimoire_moved` remains
  Athenaeum-move-only.
- A rename is a pure column update: nothing else in the current schema is
  slug-derived, so renames never cascade or rewrite dependent data.

## Broken-URL durability (deferred, explicitly)

Public-URL durability after renames (alias/redirect ledger, immutable
build identity, resolve-by-id) is deferred to its **dedicated later
phase** with its own decision record. App-internal addressing is by UUID
id and is immune to renames by construction; nothing in C4–C6 or M3
depends on slug stability.
