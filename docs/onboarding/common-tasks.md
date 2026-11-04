# Common tasks (recipes)

Last updated: 2026-11-04 / Ref: server-move/first-run + built-in TLS (0040)

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

## Change the TLS profile or lifecycle
1. Read decision 0040 F-B1/F-E1/F-F1/F-J1 and `docs/technology/tls.md`.
2. Edit `backend/app/tls/`; keep `TlsUvicornWorker`'s hardened context and
   the redirect Host/SAN check intact.
3. Add regressions in `backend/tests/test_tls.py`/`test_tls_redirect.py`;
   update the packaging contract if units/config keys change.
4. Update `docs/operations/tls.md` + decision/changelog same commit.

## Change first-run, move, or verification
1. Read decision 0040 A1–M1 and `docs/operations/server-move.md`.
2. Keep `setup`/`verify` read-only, `migrate` explicit and PG18-gated, and
   CLI restore strict on public names; `--force` must never relax names.
3. Add regressions in `backend/tests/test_cli.py`; live-DB tests run in CI.
4. Update the server-move runbook, install guide, threat model, changelog.

## Cut packages
`nfpm package --config packaging/nfpm.yaml --target dist/` → `lintian` + `rpmlint` clean (Rule 6).
