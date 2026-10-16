# Data model (Q21) — generic ordered tree

Last updated: 2026-10-16 / Ref: uncommitted

- `users(id UUID PK, email UNIQUE, pw_hash_argon2id, display, created_at)`
- `memberships(user_id FK, project_id FK, role owner|editor|viewer, PK(user_id,project_id))`
- `projects(id UUID PK, slug UNIQUE, title, source_format rst|myst DEFAULT rst, theme, created_by FK, created_at)`
- `nodes(id UUID PK, project_id FK, parent_id FK NULL=root, kind category|page, title, slug, position INT, UNIQUE(project_id,parent_id,slug))` — drives TOC + `toctree`; reorder = re-`position` in tx.
- `documents(id UUID PK, node_id FK UNIQUE, tiptap_json JSONB, source_text TEXT, source_format, version INT, updated_by FK, updated_at)` — JSON canonical.
- `document_history(id UUID PK, document_id FK, version INT, tiptap_json JSONB, source_text TEXT, author FK, at)` — single-editor history; Phase A keys versions here.
- `builds(id UUID PK, project_id FK, status queued|running|ok|failed, triggered_by FK, started, finished, log_path, artifact_path)`
- `audit_log(id BIGSERIAL PK, actor FK, action, project_id FK NULL, at, meta JSONB)`

Slugs allowlisted `[a-z0-9-]+`; all content paths jailed to `/var/lib/scriptorium/sources/<project>/`.
Rejected alternative: literal `categories/branches/sub_branches` tables (rigid).
