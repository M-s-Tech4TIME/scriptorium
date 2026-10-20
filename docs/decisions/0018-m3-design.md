# 0018 — M3 design: grimoire terminology, categories, API semantics

- **Status:** accepted
- **Decided:** 2026-10-20 (owner)
- **Scope:** M3 REST endpoints + data-model terminology/building blocks

## M2 carry-overs ratified (2026-10-20)

- Fail-loud matrix kept as shipped: RST export rejects mark combinations
  (bold+italic, strike/underline/code pairwise, link+any mark), edge
  spaces inside marked/link runs, and heading level skips — all probed
  docutils 0.22.4 limits; MyST stays lossless (Q-M3-M2-A).
- CI mypy runs `mypy --config-file backend/pyproject.toml backend/` so the
  approved docutils override actually loads; strict surfaced 3 JSONB
  columns now typed `dict[str, Any]` (Q-M3-M2-B).

## M3 decisions

- **Q-M3-1=A** Auth surface: `POST /auth/login`, `/auth/refresh`,
  `/auth/logout` only; users seeded by CLI. No open registration (attack
  surface stays small; registration/invites revisit with M4+).
- **Q-M3-2=A** Optimistic concurrency: document `PUT` carries
  `expected_version`; mismatch → `409 Conflict`; every save bumps version
  and appends to `document_history`.
- **Q-M3-3=A** `source_text` is a server-derived cache of the canonical
  TipTap JSON (decision 0010 stands). Grimoire page creation may import
  from source via the M2 converter; `ConversionError` → `422` with message.
- **Q-M3-4=A** Tree reorder: explicit atomic sibling-order operations only
  (no racy per-node deltas).
- **Q-M3-5=A** Terminology: "projects" become **grimoires** throughout —
  DB table `grimoires` (migration 0003 renames; old migrations immutable),
  model `Grimoire`, API `/api/v1/grimoires/…`, docs/brain. Full DB
  coherence per owner's "full rename incl. DB" choice: FK columns
  `project_id` → `grimoire_id` (memberships/nodes/builds/audit_log) and
  the `ix_*` indexes renamed likewise; all constraints/indexes follow.
- **Q-M3-6=A** Categories: per-user `grimoire_categories` (name, position,
  owned by user); grimoires reference a category; user-side CRUD for
  create/rename/reorder/delete.
- **Q-M3-7=A** Category delete → its grimoires drop to `category_id NULL`
  ("Uncategorized"); nothing cascades/deletes.
- **Q-M3-8=A** NULL category allowed at grimoire creation (Uncategorized is
  an implicit bucket, not a stored row).

## Endpoint map (M3)

- `/api/v1/grimoire-categories` GET/POST; `/…/{id}` PATCH (rename/order), DELETE (→NULL).
- `/api/v1/grimoires` GET/POST; `/…/{id}` GET/PATCH/DELETE (owner-only delete).
- `/api/v1/grimoires/{id}/members` GET/POST/DELETE.
- `/api/v1/grimoires/{id}/tree` GET; `…/nodes` POST; `…/nodes/{node_id}` PATCH/DELETE.
- `/api/v1/grimoires/{id}/nodes/{node_id}/document` GET/PUT (+`expected_version`); `…/history` GET.
- Audit rows on all mutations (schema table exists).
- IDOR: membership resolution per request; outsiders get uniform 404.
