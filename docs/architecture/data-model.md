# Data model (Q21 / 0018) — generic ordered tree, grimoire terminology

Last updated: 2026-10-20 / Ref: be1a220 → C1 (grimoire rename + categories)

- `users(id UUID PK, email UNIQUE, pw_hash_argon2id, display, created_at)`
- `grimoire_categories(id UUID PK, user_id FK CASCADE, name, position INT, created_at, UNIQUE(user_id, name))` — per-user sidebar groupings (0018; users create/rename/reorder/delete).
- `grimoires(id UUID PK, category_id FK NULL→grimoire_categories ON DELETE SET NULL, slug UNIQUE, title, source_format rst|myst DEFAULT rst, theme, created_by FK, created_at)` — renamed from `projects` (0018 Q-M3-5=A, migration 0003).
- `memberships(user_id FK, grimoire_id FK, role owner|editor|viewer, PK(user_id,grimoire_id))`
- `nodes(id UUID PK, grimoire_id FK, parent_id FK NULL=root, kind category|page, title, slug, position INT, UNIQUE(grimoire_id,parent_id,slug))` — drives TOC + `toctree`; reorder = atomic sibling-position ops (Q-M3-4=A).
- `documents(id UUID PK, node_id FK UNIQUE, tiptap_json JSONB, source_text TEXT (server-derived cache of the canonical JSON, Q-M3-3=A), source_format, version INT, updated_by FK, updated_at)` — JSON canonical.
- `document_history(id UUID PK, document_id FK, version INT, tiptap_json JSONB, source_text TEXT, author FK, at)` — append-only; `PUT` with `expected_version` mismatches → 409 (Q-M3-2=A).
- `builds(id UUID PK, grimoire_id FK, status queued|running|ok|failed, triggered_by FK, started, finished, log_path, artifact_path)`
- `audit_log(id BIGSERIAL PK, actor FK, action, grimoire_id FK NULL, at, meta JSONB)`
- `refresh_tokens(id UUID PK, user_id FK CASCADE, family UUID, jti UUID UNIQUE, parent_jti UUID NULL, expires_at, created_at, revoked_at NULL, revoked_reason NULL CHECK rotated|reuse|logout|expired)` — family-based refresh reuse detection (0017). Never stores token material.

Last updated: 2026-10-19 / Ref: ba153e9

Slugs allowlisted `[a-z0-9-]+`; all content paths jailed to `/var/lib/scriptorium/sources/<grimoire>/`.
Rejected alternative: literal `categories/branches/sub_branches` tables (rigid).
