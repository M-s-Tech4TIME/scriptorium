# HANDOFF

Last updated: 2026-10-16 / Ref: 9d82519 (M0 seed committed)

## Was doing
Repo live at `M-s-Tech4TIME/scriptorium` (public, proprietary NOTICE). `main`+`dev`
pushed identical (`03f9466`); `main` protected (linear/no-force/no-delete). Now on `dev`.

## Next steps (in order)
1. Push this brain-sync commit on `dev` (working branch; `main` stays at release point).
2. Resume M0 locks (`uv.lock`/`package-lock.json`) + remaining `technology/*.md` on `dev`.

## Next steps (in order)
1. Commit bootstrap files + push `main` + `dev` (same SHA), verify identical.
2. Apply `main` protection (linear history, no force/delete).
3. Resume M0 locks + remaining `technology/*.md` on `dev`.

## Next steps (in order)
1. Commit the move + 0012 + Q-001 + doc updates (this commit).
2. Await owner answer on Q-001 (CI shim) — no workaround without approval.
3. Resume M0 locks (`uv.lock`/`package-lock.json`) + remaining `technology/*.md`.

## Next steps (in order)
1. ~~Commit this seed~~ Done (`9d82519`).
2. Add M0 locks (`uv.lock`/`package-lock.json`) + remaining `technology/*.md` + validators pass.
3. Add M0 skeletons: `backend/pyproject.toml`, `frontend/package.json`, `packaging/nfpm.yaml`,
   `docker-compose.yml`, `.github/workflows/*.yml`, `.pre-commit-config.yaml`.
4. Run validators (docs/brain structure + link check) and record session log.

## Half-finished / uncommitted
All files in this seed are uncommitted until step 1.

## Gotchas
- Plan-mode restrictions lifted (build mode active 2026-10-16).
- TS 7.0.2 is owner override (Q16) vs LTS/proven rule — pin exact + explicit tsconfig.
- PG 18.x exclusive — dev compose must use `postgres:18`.
