# API surface — auth, athenaeums, categories, grimoires, documents, media, serving

Last updated: 2026-10-31 / Ref: editor/content completion tranche

## Conventions

- Bearer auth: `Authorization: Bearer <access-token>`; no token/invalid →
  `401`. Refresh rides an HttpOnly cookie (0017/0019, see
  `docs/technology/auth.md`). Login/refresh also set a 15-minute
  `scriptorium_access` cookie scoped to `/a` for private site navigation;
  API routes continue to require the bearer header. Invalid serving
  credentials are anonymous, not a `401` (private sites become `404`).
- RBAC/IDOR: no membership → uniform `404` (never `403` — existence is not
  leaked); a member under the required role → `403`. Athenaeum endpoints are
  owner-scoped: a foreign Athenaeum id is a uniform `404`.
- Mutations write one `audit_log` row in the same transaction.
- Request/response JSON over `/api/v1`.

## Auth (`routers/auth.py`)

| Route | Role | Notes |
|---|---|---|
| POST `/auth/login` | public | `429` limiter (0019), `503` fail-closed; body `{email,password}` → `{access_token,token_type}` + refresh cookie |
| POST `/auth/refresh` | cookie | rotates cookie; reuse → 401 + family burn |
| POST `/auth/logout` | cookie | revokes family (`reason=logout`), clears cookie, `204` |
| GET `/auth/me` | bearer | `{id,email,display}` for the authenticated user; missing/deleted user → `401` |

## Athenaeums (`routers/athenaeums.py`, 0020) — the library layer

| Route | Access | Notes |
|---|---|---|
| GET `/athenaeums` | owner | own libraries, creation order; rows include `public_slug`, `is_public`, pointer ids, custom-CSS size/hash |
| POST `/athenaeums` `{slug,title}` | authed | slug allowlist `[a-z0-9-]+` (`422`); dup **per owner** → `409`; `public_slug` generated globally uniquely (current name; owner-renamable per 0036); creation order stable |
| GET `/athenaeums/{id}` | owner | foreign/unknown id → `404` |
| PATCH `/athenaeums/{id}` `{title?, slug?, is_public?}` | owner | **editor slug renamable (0021)**: per-owner uniqueness → `409`; `[a-z0-9-]+` (else `422`) or explicit `null` → `422`; `is_public` bool (private default); public slug changes only via its dedicated endpoint; audit meta records what changed |
| PATCH `/athenaeums/{id}/public-slug` `{public_slug}` | owner | **public-name rename (0036)**: `[a-z0-9-]+`, 1–160, not `latest`/`stable`/`b`/`_static`/`api` → else `422`; another site's current/alias/tombstone → `409`; own retired alias → reversion; old name becomes permanent alias; no rebuild; audit `athenaeum_public_slug_changed` |
| DELETE `/athenaeums/{id}` | owner | **refused `409` while it holds grimoires** (Q-M3-11=A; no audit row on refusal); else cascades its categories and permanently tombstones every public name, `204` |
| GET `/athenaeums/{id}/sidebar` | owner | one call for the sidebar (Q-M3-13=A): `{id,slug,title,categories:[{id,name,position,grimoires:[…]}],uncategorized:[…]}` |
| GET `/athenaeums/{id}/custom-css` | owner | `{css,sha256,bytes}` — normalized stored input |
| PUT `/athenaeums/{id}/custom-css` `{css}` | owner | E2 sandbox validation (`422` on refusal); stores normalized external-CSS input; audit `athenaeum_custom_css_updated`; requires a rebuild to publish |
| DELETE `/athenaeums/{id}/custom-css` | owner | clears the input, `204`; published artifacts unchanged |

Grimoire entries in the sidebar are light rows
(`{id,slug,title,source_format,theme,category_id}`); categories ordered by
`position` then `created_at`, grimoires inside a section by `title`.

## Categories — sections inside an Athenaeum (`routers/categories.py`, 0020 Q-M3-9=A)

Re-homed from 0018's `/grimoire-categories` (per-user) to per-Athenaeum
paths; ownership resolves through the Athenaeum's owner.

| Route | Access |
|---|---|
| GET `/athenaeums/{aid}/categories` | own rows, ordered by position |
| POST `/athenaeums/{aid}/categories` `{name}` | dup in this Athenaeum → `409`; position auto = max+1 |
| PATCH `/athenaeums/{aid}/categories/{id}` `{name?, position?}` | position = 1-based insert-displacement index → siblings compacted in-tx |
| DELETE `/athenaeums/{aid}/categories/{id}` | grimoires drop to `category_id NULL` (Uncategorized, same Athenaeum) |

Foreign Athenaeum or category id → `404` (a category of *another* Athenaeum
is equally unreachable).

## Grimoires (`routers/grimoires.py`)

| Route | Access | Notes |
|---|---|---|
| GET `/grimoires` | member rows only | `{id,athenaeum_id,slug,title,source_format,theme,category_id,created_by,role}` |
| POST `/grimoires` `{athenaeum_id,slug,title,source_format?,theme?,category_id?}` | owner of the athenaeum | missing `athenaeum_id` → `422`; foreign athenaeum → `404`; category must belong to **that same Athenaeum** (`404` otherwise); slug allowlist `[a-z0-9-]+` → else `422`; dup slug → `409`; creator becomes `owner` member atomically |
| GET `/grimoires/{id}` | any member | `404` outsider |
| PATCH `/grimoires/{id}` `{title?, slug?, theme?, category_id?, athenaeum_id?}` | owner (`403` member) | explicit `category_id: null` clears to Uncategorized; `source_format` immutable; **`slug` renamable (0021)** — global uniqueness → `409`, `[a-z0-9-]+`/`null` → `422`; **`athenaeum_id` = cross-Athenaeum move** → target must be owned (`404`), `null` target → `422` (no floating grimoires), same-id no-op; audit `grimoire_moved` on move else `grimoire_patched` |
| POST `/grimoires/{id}/duplicate` `{athenaeum_id?, slug?, title?}` | owner (`403` member) | **deep copy (0025)**: tree + head documents as v1 (no history clone), fresh owner-only roster, same `source_format`/`theme`; slug caller-supplied (`409` collision, `422` regex) or auto-derived `…-copy`, `…-copy-2`…; target library any the caller owns (default source's; foreign → `404`); copy-of-copy allowed; audit `grimoire_duplicated` |
| DELETE `/grimoires/{id}` | owner (`403` member) | cascades nodes/documents/builds/memberships |

## Tree — Chapters & Folios inside a Grimoire (`routers/nodes.py`, 0023)

The book's ordered tree drives the TOC/`toctree` (Sphinx/RTD flexibility,
unbounded depth). Vocabulary per 0022: chapters = in-book folders
(`kind 'chapter'`), folios = page files (`kind 'folio'`).

| Route | Access | Notes |
|---|---|---|
| GET `/grimoires/{gid}/tree` | any member | `{grimoire_id, nodes:[{id,parent_id,kind,title,slug,position,children}]}` — siblings ordered 1..n by `position` |
| POST `/grimoires/{gid}/nodes` `{parent_id?, kind, title, slug}` | owner | `parent_id` omitted/`null` → root set; slug `[a-z0-9-]+` → `422`; sibling-set collision → `409`; position auto = max+1 |
| PATCH `/grimoires/{gid}/nodes/{id}` `{title?, slug?, parent_id?, position?}` | owner | slugs renamable (0021: sibling-set uniqueness → `409`, `[a-z0-9-]+`/`null` → `422`); re-parent by `parent_id` presence — same Grimoire only (`404`), `null` = return to root set; **cycle guard `409`** (never under self/descendant); `position` = 1-based insert-displacement (Q-M3-4=A, one transaction), position `null` → `422` |
| DELETE `/grimoires/{gid}/nodes/{id}` | owner | **refused `409` while the node holds sub-nodes or a folio document (D1=A)** — nothing cascades by choice; emptied → `204`, no audit row on refusal |

Kinds do not restrict nesting (any node may parent another — Sphinx allows
documents as toctree parents; 0023 micro-default). Foreign
Grimoire/node ids → uniform `404` (IDOR).

## Folio documents (`routers/documents.py`, 0024)

Content of a folio (or any tree node): TipTap JSON canonical, source
server-derived (Q-M3-3=A). Optimistic concurrency per Q-M3-2=A.

| Route | Access | Notes |
|---|---|---|
| GET `/grimoires/{gid}/nodes/{nid}/document` | any member | `404` until the first save |
| PUT `…/document` `{tiptap_json \| source_text, expected_version}` | editor/owner (`403` viewer) | exactly one content field; `expected_version` required (`0` = create assertion); mismatch → `409` with expected/current, nothing written; import mode runs the M2 importer, `ConversionError` → `422`; every save: version+1, history append, source re-derived from canonical TipTap via the grimoire's `source_format`; audit `document_saved` |
| GET `…/document/history` | any member | metadata list `{version, author, at}` — blobs omitted (0024) |
| GET `…/document/history/{version}` | any member | one history row `{document_id,version,tiptap_json,source_text,author,at}`; unknown version → `404` |
| POST `…/document/history/{version}/restore` `{expected_version}` | editor/owner (`403` viewer) | appends a **new** version copied from history (history stays immutable); stale `expected_version` → `409`; re-validates media refs → `422`; audit `document_restored` |

Size caps at the trust boundary (Rule 2): `source_text` ≤ 1,000,000
chars, serialized `tiptap_json` ≤ 2,000,000 chars → `422`. Cross-grimoire
node addressing → uniform `404` (IDOR). Image nodes must reference an
uploaded asset owned by the same grimoire (`/_static/media/{uuid}.{ext}`);
external/inline sources and foreign assets → `422`.

## Media (`routers/media.py`, V1 images/GIF)

Uploads use a raw request body (not multipart). The server sniffs magic
bytes; the declared content type and filename extension are not trusted.

| Route | Access | Notes |
|---|---|---|
| POST `/grimoires/{gid}/media?filename=…` | editor/owner (`403` viewer) | raw bytes; PNG/JPEG/GIF/WebP/AVIF only (`415` otherwise); 10 MiB cap (`413`); empty `422`; returns the asset row incl. canonical `url` and authenticated `content_url` |
| GET `/grimoires/{gid}/media` | any member | assets for the grimoire, newest first |
| GET `/media/{asset_id}/content` | any member of the owning grimoire | bytes with sniffed `Content-Type`, `X-Content-Type-Options: nosniff`, private 5-minute cache + SHA-256 `ETag`; outsider/unknown → `404` |

Canonical content stores `/_static/media/{asset_id}.{ext}` image sources.
The editor resolves those URLs through the authenticated content endpoint
as blob URLs; builds copy referenced files into the artifact. SVG,
remote URLs, data URIs, video, audio, and attachments are out of V1 scope.

## Members (`routers/grimoires.py`)

| Route | Access | Notes |
|---|---|---|
| GET `/grimoires/{id}/members` | any member | `{user_id,role,display}` — no emails |
| POST `…/members` `{email, role}` | owner | roles: `editor`\|`viewer` only; unknown email `404`; already member `409` |
| PATCH `…/members/{user_id}` `{role}` | owner | owner target → `409` (role fixed) |
| DELETE `…/members/{user_id}` | owner, or member deleting self | owner self-removal → `409` (delete grimoire or transfer first) |

Owner role assignment/transfer via API is intentionally absent — a future
decision (transfer flow) will precede any owner-grant endpoint. Sharing
stays grimoire-level only (0020 Q-M3-12=A).

## Publications (`routers/publications.py`, 0035 A2)

Owner-only; foreign Athenaeum/build ids are uniform `404`.

| Route | Notes |
|---|---|
| GET `/athenaeums/{id}/publication` | `{athenaeum_id,public_slug,public_aliases,is_public,latest,stable,latest_url,stable_url}`; `public_aliases` is `[{slug,retired_at}]`; each pointer is `{build_id,build_number,status,published_at,published_by,url}` or `null` |
| POST `/athenaeums/{id}/publish` `{build_id,channel?}` | `channel` = `latest`\|`stable`\|`both` (default `both`); build must be `ok` and manifest-backed (`409` otherwise); records first publication history; audit `build_published` |
| DELETE `/athenaeums/{id}/publish?channel=…` | clears the selected pointer(s), `204`; audit `build_unpublished`; numbered builds stay addressable |

## Served sites (`routers/site.py`, 0035 B3/C1/D1/E2)

These are browser-facing HTML routes, not JSON API routes. Access is
public for `is_public=true`; otherwise owner or any member (bearer or
`scriptorium_access` cookie), with a uniform `404` for outsiders.

| Route | Notes |
|---|---|
| GET `/a/{public_slug}/` | `307` to `latest` if available, else `stable`; `404` when neither |
| GET `/a/{public_slug}/latest/…` | latest pointer alias; `Cache-Control: no-cache` |
| GET `/a/{public_slug}/stable/…` | stable pointer alias; `Cache-Control: no-cache` |
| GET `/a/{public_slug}/b/{number}/…` | immutable published build; one-year immutable cache |
| GET `/a/{public_slug}` / `…/{latest\|stable}` / `…/b/{number}` | slash-less redirects to canonical roots |
| GET `/a/{retired_slug}/…` | permanent alias: after the same access check, `308` to `/a/{current_slug}/…`; path suffix and query preserved; tombstones/unknown names `404` |

Directories redirect to a trailing slash; missing files, traversal paths,
unpublished numbered builds, and non-manifest-backed artifacts are `404`.
Canonical redirects use a relative `Location` and preserve the query.
Alias redirects use a relative `Location`, preserve the suffix/query, and
flatten to the current canonical name. Every file response carries the
manifest-derived CSP and the E2 security headers; private file and redirect
responses add `private, no-store`, `Vary: Cookie`, and
`X-Robots-Tag: noindex, nofollow`; public alias redirects are `no-cache`.

## Audit actions (through this tranche)

`category_created|patched|deleted`, `grimoire_created|patched|deleted|moved`,
`member_added|role_changed|removed`, `athenaeum_created|patched|deleted`,
`athenaeum_public_slug_changed`, `node_created|patched|moved|deleted`,
`document_saved`, `document_restored`, `grimoire_duplicated`, `build_published`,
`build_unpublished`, `athenaeum_custom_css_updated`
(refused deletes/saves write no audit row — nothing happened).
