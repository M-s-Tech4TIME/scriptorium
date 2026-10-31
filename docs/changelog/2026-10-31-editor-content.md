# 2026-10-31 — Editor/content completion (0038)

V1 editor surface, image/GIF media, history restore, and single-file
import. Backup/restore, page aliases, M5, and SEO remain later phases.

## Backend

- `GET /api/v1/auth/me` returns `{id,email,display}`.
- Document history:
  - `GET …/document/history/{version}` returns one immutable row;
  - `POST …/document/history/{version}/restore` appends a new version,
    re-validates media, audits `document_restored`, and keeps
    `expected_version` conflict handling.
- Media (migration `0009media`, `media_assets`):
  - raw-body upload with magic-byte sniffing (PNG/JPEG/GIF/WebP/AVIF),
    10 MiB streaming cap, generated storage paths, atomic write, DB
    rollback cleanup;
  - member-visible list and authenticated content read with `nosniff`,
    private cache, and SHA-256 `ETag`;
  - canonical `/_static/media/{uuid}.{ext}` URLs;
  - document saves reject external, data, malformed, and foreign-grimoire
    image sources.
- Builds resolve referenced assets from DB rows, copy them into
  `_static/media`, and fail loudly on missing files or unsafe paths.
- RST/MyST import/export support `image` nodes (`.. image::` and
  `![alt](src "title")`).

## Frontend

- New Vite 8 + React 19 application:
  - memory-only access token, refresh-cookie bootstrap, single-flight
    refresh, typed `ApiError`;
  - login, dashboard, Athenaeum page (grimoires, builds, publication
    channels, settings), grimoire editor;
  - TipTap editor with headings, marks, lists, quote, code, rule, link,
    image upload, `Ctrl/Cmd+S`, and conflict reload/overwrite;
  - tree CRUD, history detail/restore, source preview, single-file
    RST/MyST import, `useBlocker` + `beforeunload` unsaved-change guards;
  - canonical media URL ↔ blob URL mapping (saves never send `blob:`).
- Lazy route chunks keep TipTap off the login/dashboard path.
- Vitest: slug/date helpers, media mapping/cleanup, API auth
  refresh/error handling.

## Tooling

- CI frontend job now runs `typecheck`, `test`, and `build` in addition to
  lint, format check, and `npm audit --audit-level=high`.
- `.prettierignore` excludes build output, dependencies, and the lockfile.
- `tsconfig` uses `skipLibCheck` because Testing Library and Vitest both
  augment `Assertion` with incompatible parameters under TypeScript 7;
  application code remains fully checked.

## Tests and gates

- Backend: `115 passed, 44 skipped` locally; ruff, format, mypy clean.
  CI ran `159 passed` with no skips against live PG18/Redis, including
  media/history endpoints and migration `0009media`.
- Frontend: typecheck, lint, format check, 16 Vitest tests, production
  build, and high-severity audit gate pass.
- Pushed as `476dfff`; lint-type-test, security, and packaging all green.

## Docs

Decision 0038; API, data model, conversion, frontend, overview, security,
roadmap, brain, and this changelog.
