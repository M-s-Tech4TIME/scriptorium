# 0038 — Editor/content completion: media, history restore, and the V1 app

- **Status:** accepted; implemented scope recorded 2026-10-31
- **Scope:** the editor-facing V1 surface: the React application, image/GIF
  media, document history restore, and single-file source import.
- **Not in this record:** backup/restore (both modes), page-level path
  aliases, M5 hardening, and SEO. Those remain separate phases; the
  owner-approved requirements are restated at the end so they are not
  lost.

## Owner rulings carried into this tranche

| Area | Ruling |
|---|---|
| Media scope | V1 accepts images and GIF only. Video, audio, and attachments are V1.x. |
| Import scope | Single-file `.rst` / `.md` import into one folio is V1. Bulk Sphinx/Read-the-Docs import is post-V1; importing built HTML is out of scope. |
| Media trust boundary | The canonical URL is `/_static/media/{uuid}.{ext}`. Allowed types are PNG, JPEG, GIF, WebP, and AVIF; the cap is 10 MiB. SVG, external URLs, data URIs, and remote images are refused. The type is decided from magic bytes, never the upload header or filename. |
| Media ownership | An asset belongs to exactly one grimoire. Every read and upload re-checks membership; a document save rejects a reference to another grimoire's asset. |
| Editor auth | The access token stays in memory only. Bootstrapping uses the HttpOnly refresh cookie, and authenticated media is fetched as a blob for editor display. |
| History | Restoring a version appends a new version; history rows are never rewritten. Optimistic concurrency (`expected_version`) still applies. |
| Public names | Already ruled in 0036: owner-renamable, permanent aliases, permanent tombstones, names never reused. |

## Implemented surface

### Backend

- `GET /api/v1/auth/me` returns the authenticated identity
  (`id`, `email`, `display`).
- `GET …/document/history/{version}` returns one immutable history row.
- `POST …/document/history/{version}/restore` appends a new version from
  history, re-validates media references, writes `document_restored`, and
  returns the new document body.
- `media_assets` (migration `0009media`) plus:
  - `POST /api/v1/grimoires/{gid}/media` — raw-body upload, magic-byte
    sniffing, 10 MiB streaming cap, atomic write, DB rollback cleanup;
  - `GET /api/v1/grimoires/{gid}/media` — member-visible asset list;
  - `GET /api/v1/media/{id}/content` — authenticated bytes with
    `nosniff`, private cache, and SHA-256 `ETag`.
- Document saves validate every image source against the owning grimoire.
- Builds resolve referenced assets from DB rows, copy them into
  `_static/media`, and fail loudly on missing files or unsafe paths.
- RST/MyST import and export round-trip `image` nodes (`.. image::` /
  `![alt](src "title")`).

### Frontend

- Vite 8 + React 19 application with lazy routes, a memory-only access
  token, single-flight refresh, and typed API errors.
- Login, dashboard, Athenaeum page (grimoires, builds, publication
  channels, settings), and grimoire editor.
- TipTap editor with the approved starter-kit surface plus images;
  toolbar, links, image upload, `Ctrl/Cmd+S`, unsaved-change warning, and
  conflict reload/overwrite.
- Tree CRUD, history detail/restore, generated-source preview, and
  single-file import.
- Canonical media URL ↔ blob URL mapping; saves always send canonical
  URLs, never `blob:` URLs.
- Vitest coverage for slug/date helpers, media mapping/cleanup, and API
  auth refresh/error handling.

## Deferred (approved requirements, not implemented here)

- **Backup/restore:** both Editorial and Full modes are required. A
  restored site must preserve numbered `/b/{n}/` URLs exactly. The design
  and implementation are a separate tranche.
- **Server move / first-run provisioning:** separate tranche.
- **Page-level path aliases:** deferred by 0036 B1.
- **SEO:** every SEO attribute must be user-controllable per Athenaeum.
  No implementation before the dedicated plan and owner rulings.
- **M5 hardening:** signed packages, SBOM/provenance, clean-install
  matrix.
