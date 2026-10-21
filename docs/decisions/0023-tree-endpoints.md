# 0023 — Grimoire tree endpoints: Chapters & Folios (M3 C4 design)

- **Status:** accepted
- **Decided:** 2026-10-21 (owner: D1=A, D2=A, chapter option A; micro-defaults
  as approved earlier with the C4 plan)
- **Scope:** ordered-tree API inside a Grimoire; records rulings where 0018
  left tree semantics open. Root schema unchanged (0001's partial unique
  slug indexes already cover both sibling sets).

## Endpoints (`routers/nodes.py`, prefix `/api/v1/grimoires/{grimoire_id}`)

| Route | Access | Notes |
|---|---|---|
| GET `/tree` | any member | nested `{grimoire_id, nodes:[{id,kind,title,slug,position,children}]}` — anchors into Scriptorium's own navigation vocabulary (Athenaeum → Grimoire → Chapter → Folio) |
| POST `/nodes` `{parent_id?, kind, title, slug}` | owner | `parent_id` omitted/`null` → root set; position auto = max+1 in the sibling set; slug `[a-z0-9-]+` → `422`; sibling-set collision → `409` |
| PATCH `/nodes/{id}` `{title?, slug?, parent_id?, position?}` | owner | rename (0021: per-sibling-set uniqueness, `null` → `422`); re-parent by `parent_id` presence — same Grimoire only (`404`), `null` = move to root; **cycle guard `409`** (never under self/descendant); `position` = 1-based insert-displacement in the target sibling set (Q-M3-4=A, one transaction) |
| DELETE `/nodes/{id}` | owner | **refused `409` while the node holds sub-nodes or a folio document (D1=A)**; nothing is cascaded by choice — explicit empties-first |

## Owner-ruled semantics

- **D1=A Delete-refusal:** a delete that would cascade children or content
  silently is refused `409` with no audit row (mirrors 0020's Athenaeum
  refusal). Empties → `204`.
- **D2=A Owner-only mutations:** any member reads `GET /tree`; create/
  patch/delete require role `owner` (member under role → `403`, outsider →
  uniform `404`).
- **Single-membership hierarchy** reaffirmed (0022); all layers renamable
  (0021).

## Micro-defaults (owner-vetoable, revealed now)

- **Kind does not restrict nesting** (any node may parent another): the
  owner's stated goal is to replicate Sphinx/RTD flexibility, where a
  document *is* a legal toctree parent. Folders are chapters, files are
  folios, and nesting depth is unbounded. If the owner prefers strict
  book-folder/file semantics, this one check is a 2-line change.
- **`kind` is immutable after creation** (renames touch title/slug only
  per 0021); re-parenting never changes kind.
- **Audit actions:** `node_created|node_patched|node_moved|node_deleted`
  (`node_moved` only when `parent_id` changes), all keyed to the Grimoire
  row; refused deletes write no audit row (nothing happened).
- **Position auto = max+1** on create; displacement reorder re-indexes the
  whole sibling set 1..n in one transaction.
