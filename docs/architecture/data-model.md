# Data model — native library hierarchy, generic ordered tree (0021 / 0020 / 0018 / Q21)

Last updated: 2026-10-21 / Ref: C3.6 slug-rename policy (0021)

The canonical, ground-up structure is the Athenaeum hierarchy (decision
0020): every user owns one or more **Athenaeums** (libraries — one complete
documentation project per product/company); categories are sections inside
an Athenaeum; every grimoire (book/project) lives in an Athenaeum,
categorized or uncategorized.

```
users ──owns──> athenaeums ──contains──> grimoire_categories (sections)
                     │                        │
                     └──────contains──────────┘──> grimoires (categorized or NULL)
                                                       └──> nodes → documents → builds
```

- `users(id UUID PK, email UNIQUE, pw_hash_argon2id, display, created_at)`
- `athenaeums(id UUID PK, owner_id FK users CASCADE, slug, title, created_at, UNIQUE(owner_id, slug))` — the library layer (0020). Slug uniqueness is **per owner**: every user may own slug `default`. Slug is **renamable** (0021). Delete is owner-driven and **refused `409` while the Athenaeum still holds grimoires** (Q-M3-11=A) — the `ON DELETE CASCADE` is belt-and-braces, not reachable via API.
- `grimoire_categories(id UUID PK, athenaeum_id FK athenaeums CASCADE, name, position INT, created_at, UNIQUE(athenaeum_id, name))` — sections **inside an Athenaeum** (0020 Q-M3-9=A; `user_id` dropped, migration 0004). Deleting a section leaves its grimoires Uncategorized.
- `grimoires(id UUID PK, athenaeum_id FK athenaeums NOT NULL CASCADE, category_id FK NULL→grimoire_categories ON DELETE SET NULL, slug UNIQUE, title, source_format rst|myst DEFAULT rst, theme, created_by FK, created_at)` — every grimoire lives in an Athenaeum (0020 Q-M3-10=A); rename from `projects` (0018 Q-M3-5=A, migration 0003). Slug is **renamable** (0021, amending 0018); cross-Athenaeum moves happen via grimoire PATCH to an Athenaeum the caller owns (audit `grimoire_moved`).
- `memberships(user_id FK, grimoire_id FK, role owner|editor|viewer, PK(user_id,grimoire_id))` — sharing stays **grimoire-level only** (0020 Q-M3-12=A); no Athenaeum-level sharing yet (future decision first).
- `nodes(id UUID PK, grimoire_id FK, parent_id FK NULL=root, kind chapter|folio, title, slug, position INT, UNIQUE(grimoire_id,parent_id,slug))` — drives TOC + `toctree`; reorder = atomic sibling-position ops (Q-M3-4=A). `kind` is **`chapter|folio`** since 0022 (was 0010's `category|page`; migration 0005).
- `documents(id UUID PK, node_id FK UNIQUE, tiptap_json JSONB, source_text TEXT (server-derived cache of the canonical JSON, Q-M3-3=A), source_format, version INT, updated_by FK, updated_at)` — JSON canonical.
- `document_history(id UUID PK, document_id FK, version INT, tiptap_json JSONB, source_text TEXT, author FK, at)` — append-only; `PUT` with `expected_version` mismatches → 409 (Q-M3-2=A).
- `builds(id UUID PK, grimoire_id FK, status queued|running|ok|failed, triggered_by FK, started, finished, log_path, artifact_path)`
- `audit_log(id BIGSERIAL PK, actor FK, action, grimoire_id FK NULL, at, meta JSONB)` — Athenaeum mutations stage rows with `grimoire_id NULL` (`athenaeum_created|patched|deleted`, `grimoire_moved`).
- `refresh_tokens(id UUID PK, user_id FK CASCADE, family UUID, jti UUID UNIQUE, parent_jti UUID NULL, expires_at, created_at, revoked_at NULL, revoked_reason NULL CHECK rotated|reuse|logout|expired)` — family-based refresh reuse detection (0017). Never stores token material.

Migrations are append-only history: 0001 initial, 0002 refresh tokens,
0003 grimoire rename + per-user categories, 0004 athenaeum layer
(backfills one **"Default"** Athenaeum per user and re-points all existing
categories/grimoires into it), 0005 folio/chapter `kind` vocabulary (0022).
Old migrations are never edited.

Last updated: 2026-10-20 / Ref: be1a220 → C1 (grimoire rename + categories)

Slugs allowlisted `[a-z0-9-]+`; all content paths jailed to `/var/lib/scriptorium/sources/<grimoire>/`.
Rejected alternative: literal `categories/branches/sub_branches` tables (rigid).
Rejected alternative (0020): per-user categories kept, athenaeum mapped over them only in the API (a library abstraction would be unverifiable — scoping must be native).
