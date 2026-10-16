# Common tasks (recipes)

Last updated: 2026-10-16 / Ref: uncommitted

## Add a Sphinx directive mapping (M2)
1. Add TipTap node in `frontend/src/editor/`.
2. Add exporter in `backend/app/convert/` (both RST + MyST) + round-trip test.
3. Update `docs/` + changelog same commit. Needs owner approval if new extension (allowlist).

## Add an API endpoint
1. `backend/app/routers/` + Pydantic schema + per-project RBAC check + test (`-W error`).
2. Wire frontend call; update `codebase-map.md` if new area.

## Add a UI block
1. `frontend/src/components/` + types strict + test; no `any` without approval.

## Add a migration
1. `alembic revision --autogenerate`, review SQL, `scriptorium-admin migrate` locally on PG18.
2. Same-commit: `docs/technology/` if version-relevant + changelog.

## Cut packages
`nfpm package --config packaging/nfpm.yaml --target dist/` → `lintian` + `rpmlint` clean (Rule 6).
