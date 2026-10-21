# API surface — auth, athenaeums, categories, grimoires, members

Last updated: 2026-10-21 / Ref: C3.5 in this commit (athenaeum layer, 0020)

## Conventions

- Bearer auth: `Authorization: Bearer <access-token>`; no token/invalid →
  `401`. Refresh rides an HttpOnly cookie (0017/0019, see
  `docs/technology/auth.md`).
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

## Athenaeums (`routers/athenaeums.py`, 0020) — the library layer

| Route | Access | Notes |
|---|---|---|
| GET `/athenaeums` | owner | own libraries, creation order |
| POST `/athenaeums` `{slug,title}` | authed | slug allowlist `[a-z0-9-]+` (`422`); dup **per owner** → `409`; creation order stable |
| GET `/athenaeums/{id}` | owner | foreign/unknown id → `404` |
| PATCH `/athenaeums/{id}` `{title?, slug?}` | owner | **slug renamable (0021)**: per-owner uniqueness → `409`; `[a-z0-9-]+` (else `422`) or explicit `null` → `422`; audit meta records what changed |
| DELETE `/athenaeums/{id}` | owner | **refused `409` while it holds grimoires** (Q-M3-11=A; no audit row on refusal); else cascades its categories, `204` |
| GET `/athenaeums/{id}/sidebar` | owner | one call for the sidebar (Q-M3-13=A): `{id,slug,title,categories:[{id,name,position,grimoires:[…]}],uncategorized:[…]}` |

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
| DELETE `/grimoires/{id}` | owner (`403` member) | cascades nodes/documents/builds/memberships |

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

## Audit actions (through this tranche)

`category_created|patched|deleted`, `grimoire_created|patched|deleted|moved`,
`member_added|role_changed|removed`, `athenaeum_created|patched|deleted`
(refused deletes write no audit row — nothing happened).
