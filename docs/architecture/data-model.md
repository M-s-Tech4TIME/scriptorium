# Data model — native library hierarchy, generic ordered tree (0021 / 0020 / 0018 / Q21)

Last updated: 2026-10-31 / Ref: editor/content completion tranche

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
- `athenaeums(id UUID PK, owner_id FK users CASCADE, slug, public_slug, title, is_public, custom_css, latest_build_id, stable_build_id, created_at, UNIQUE(owner_id, slug), UNIQUE(public_slug))` — the library layer (0020). Editor-slug uniqueness is **per owner**: every user may own slug `default`; it is **renamable** (0021). `public_slug` is the current global serving name (0035 D1; **owner-renamable** per 0036). A collision at creation gets an 8-hex suffix (migration backfill uses the full UUID, plus a numeric suffix only if that name is already taken). `is_public` is private-by-default (B3); `custom_css` holds normalized external-CSS input; the two pointers reference published builds (`ON DELETE SET NULL`). Delete is owner-driven and **refused `409` while the Athenaeum still holds grimoires** (Q-M3-11=A) — the `ON DELETE CASCADE` is belt-and-braces, not reachable via API.
- `public_names(slug TEXT PK, athenaeum_id FK athenaeums NULL SET NULL, is_current BOOL, created_at, retired_at)` — the single global public-URL namespace (0036 A1/C1/E1/F1). Exactly one current row per live Athenaeum via a partial unique index; retired rows are permanent aliases; deletion leaves rows with `athenaeum_id NULL` as permanent tombstones. The slug primary key prevents a canonical name, alias, or tombstone from being claimed by another site. Migration 0008 backfills every existing `athenaeums.public_slug` as current.
- `grimoire_categories(id UUID PK, athenaeum_id FK athenaeums CASCADE, name, position INT, created_at, UNIQUE(athenaeum_id, name))` — sections **inside an Athenaeum** (0020 Q-M3-9=A; `user_id` dropped, migration 0004). Deleting a section leaves its grimoires Uncategorized.
- `grimoires(id UUID PK, athenaeum_id FK athenaeums NOT NULL CASCADE, category_id FK NULL→grimoire_categories ON DELETE SET NULL, slug UNIQUE, title, source_format rst|myst DEFAULT rst, theme, created_by FK, created_at)` — every grimoire lives in an Athenaeum (0020 Q-M3-10=A); rename from `projects` (0018 Q-M3-5=A, migration 0003). Slug is **renamable** (0021, amending 0018); cross-Athenaeum moves happen via grimoire PATCH to an Athenaeum the caller owns (audit `grimoire_moved`).
- `memberships(user_id FK, grimoire_id FK, role owner|editor|viewer, PK(user_id,grimoire_id))` — sharing stays **grimoire-level only** (0020 Q-M3-12=A); no Athenaeum-level sharing yet (future decision first).
- `nodes(id UUID PK, grimoire_id FK, parent_id FK NULL=root, kind chapter|folio, title, slug, position INT, UNIQUE(grimoire_id,parent_id,slug))` — drives TOC + `toctree`; reorder = atomic sibling-position ops (Q-M3-4=A). `kind` is **`chapter|folio`** since 0022 (was 0010's `category|page`; migration 0005).
- `documents(id UUID PK, node_id FK UNIQUE, tiptap_json JSONB, source_text TEXT (server-derived cache of the canonical JSON, Q-M3-3=A), source_format, version INT, updated_by FK, updated_at)` — JSON canonical.
- `document_history(id UUID PK, document_id FK, version INT, tiptap_json JSONB, source_text TEXT, author FK, at)` — append-only; `PUT` with `expected_version` mismatches → 409 (Q-M3-2=A). Restore appends a new version copied from history; it never rewrites old rows.
- `media_assets(id UUID PK, grimoire_id FK grimoires CASCADE, filename, content_type, size_bytes, sha256, storage_path, created_by FK users NULL SET NULL, created_at)` — V1 image/GIF assets (migration 0009). The row is the authorization/metadata source; bytes live under `SC_MEDIA_ROOT` at `storage_path` (`{id[:2]}/{id}.{ext}`). `content_type` is one of PNG/JPEG/GIF/WebP/AVIF and is sniffed from magic bytes, never trusted from the upload header. Canonical document image URLs are `/_static/media/{id}.{ext}`; the build copies referenced files into the artifact. SVG, remote URLs, and non-image uploads are rejected.
- `builds(id UUID PK, grimoire_id FK NULL *(pre-0026 rows)*, athenaeum_id FK NULL, build_number, status queued|running|ok|failed, triggered_by FK, started, finished, log_path, artifact_path, published_at, published_by FK NULL)` — **one site per Athenaeum (0026):** a build compiles the entire library; `build_number` is a per-Athenaeum monotonic counter (`uq_builds_athenaeum_number`); exactly one key is ever set (`ck_builds_site`). Pre-M4 rows stay grimoire-keyed. Artifacts live at `/var/lib/scriptorium/artifacts/{athenaeum_id}/{build_number}/` (portable static site). `published_at`/`published_by` record first publication history (0035 A2); a published build stays addressable by number after unpublish.
- `audit_log(id BIGSERIAL PK, actor FK, action, grimoire_id FK NULL, at, meta JSONB)` — Athenaeum mutations stage rows with `grimoire_id NULL` (`athenaeum_created|patched|deleted`, `athenaeum_public_slug_changed`, `grimoire_moved`).
- `refresh_tokens(id UUID PK, user_id FK CASCADE, family UUID, jti UUID UNIQUE, parent_jti UUID NULL, expires_at, created_at, revoked_at NULL, revoked_reason NULL CHECK rotated|reuse|logout|expired)` — family-based refresh reuse detection (0017). Never stores token material.

Migrations are append-only history: 0001 initial, 0002 refresh tokens,
0003 grimoire rename + per-user categories, 0004 athenaeum layer
(backfills one **"Default"** Athenaeum per user and re-points all existing
categories/grimoires into it), 0005 folio/chapter `kind` vocabulary (0022), 0006 build key era +
per-Athenaeum build numbers (0026), 0007 serving fields/public slug/pointers
(0035), 0008 public-name registry/aliases/tombstones (0036), 0009 media
assets (V1 images/GIF). Old migrations are never edited.

Last updated: 2026-10-28 / Ref: URL-durability phase 0036

Slugs allowlisted `[a-z0-9-]+`. Sources are no longer held in a persistent
per-grimoire jail — 0026 supersedes `/var/lib/scriptorium/sources/<grimoire>/`:
each build materializes an ephemeral staging tree **keyed by grimoire id**
inside its workspace and compiles it into the site artifact at
`/var/lib/scriptorium/artifacts/{athenaeum_id}/{build_number}/` — a
portable, self-contained static website (HTML in M4; `ok` ⇔ warning-free
under Sphinx `-W`, design mandate in 0026). Since 0035, a successful
artifact also carries `manifest.json` beside `html/`: file inventory +
SHA-256, inline-script CSP hashes, site/build identity, and the
custom-CSS path/hash. The manifest is the serving/export contract; an
artifact without it is not publishable or servable.
Rejected alternative: literal `categories/branches/sub_branches` tables (rigid).
Rejected alternative (0020): per-user categories kept, athenaeum mapped over them only in the API (a library abstraction would be unverifiable — scoping must be native).
Rejected (0026): container/nspawn isolation (P3 = limited-subprocess sandbox); per-grimoire sites/artifacts (P1 = one Athenaeum = one site).
