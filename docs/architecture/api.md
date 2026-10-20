# API surface (M3) — auth, categories, grimoires, members

Last updated: 2026-10-20 / Ref: C2 green (aee1872) + C3 in this commit

## Conventions

- Bearer auth: `Authorization: Bearer <access-token>`; no token/invalid →
  `401`. Refresh rides an HttpOnly cookie (0017/0019, see
  `docs/technology/auth.md`).
- RBAC/IDOR: no membership → uniform `404` (never `403` — existence is not
  leaked); a member under the required role → `403`.
- Mutations write one `audit_log` row in the same transaction.
- Request/response JSON over `/api/v1`.

## Auth (`routers/auth.py`)

| Route | Role | Notes |
|---|---|---|
| POST `/auth/login` | public | `429` limiter (0019), `503` fail-closed; body `{email,password}` → `{access_token,token_type}` + refresh cookie |
| POST `/auth/refresh` | cookie | rotates cookie; reuse → 401 + family burn |
| POST `/auth/logout` | cookie | revokes family (`reason=logout`), clears cookie, `204` |

## Sidebar categories (`routers/categories.py`, 0018 Q-M3-6/7/8)

| Route | Access |
|---|---|
| GET `/grimoire-categories` | own rows, ordered by position |
| POST `/grimoire-categories` `{name}` | dup → `409`; position auto = max+1 |
| PATCH `/grimoire-categories/{id}` `{name?, position?}` | position = 1-based index at patch time (insert-displacement → siblings compacted in-tx) |
| DELETE `/grimoire-categories/{id}` | grimoires drop to `category_id NULL` (Uncategorized) |

Foreign category ids → `404`.

## Grimoires (`routers/grimoires.py`)

| Route | Access | Notes |
|---|---|---|
| GET `/grimoires` | member rows only | `{id,slug,title,source_format,theme,category_id,created_by,role}` |
| POST `/grimoires` `{slug,title,source_format?,theme?,category_id?}` | public (authed) | slug allowlist `[a-z0-9-]+` → else `422`; dup slug → `409`; NULL category allowed (Q-M3-8); creator becomes `owner` member atomically |
| GET `/grimoires/{id}` | any member | `404` outsider |
| PATCH `/grimoires/{id}` `{title?,theme?,category_id?}` | owner (`403` member) | explicit `category_id: null` clears to Uncategorized; **`source_format` immutable after creation** |
| DELETE `/grimoires/{id}` | owner (`403` member) | cascades nodes/documents/builds/memberships |

## Members (`routers/grimoires.py`)

| Route | Access | Notes |
|---|---|---|
| GET `/grimoires/{id}/members` | any member | `{user_id,role,display}` — no emails |
| POST `…/members` `{email, role}` | owner | roles: `editor`\|`viewer` only; unknown email `404`; already member `409` |
| PATCH `…/members/{user_id}` `{role}` | owner | owner target → `409` (role fixed) |
| DELETE `…/members/{user_id}` | owner, or member deleting self | owner self-removal → `409` (delete grimoire or transfer first) |

Owner role assignment/transfer via API is intentionally absent — a future
decision (transfer flow) will precede any owner-grant endpoint.

## Audit actions (this tranche)

`category_created|patched|deleted`, `grimoire_created|patched|deleted`,
`member_added|role_changed|removed`.
