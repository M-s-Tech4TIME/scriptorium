# HANDOFF

Last updated: 2026-10-16 / Ref: uncommitted (M0 seed)

## Was doing
Seeding M0 foundation after owner approved Q1–Q23 + Rule 6 + roadmap. Git repo
initialized on `main`; writing `AGENTS.md`, `docs/`, `brain/` skeletons.

## Next steps (in order)
1. Commit this seed (docs + brain + AGENTS) as initial commit.
2. Add `docs/decisions/0001-*.md` records + `technology/` pins + `compatibility-matrix.md`.
3. Add M0 skeletons: `backend/pyproject.toml`, `frontend/package.json`, `packaging/nfpm.yaml`,
   `docker-compose.yml`, `.github/workflows/*.yml`, `.pre-commit-config.yaml`.
4. Run validators (docs/brain structure + link check) and record session log.

## Half-finished / uncommitted
All files in this seed are uncommitted until step 1.

## Gotchas
- Plan-mode restrictions lifted (build mode active 2026-10-16).
- TS 7.0.2 is owner override (Q16) vs LTS/proven rule — pin exact + explicit tsconfig.
- PG 18.x exclusive — dev compose must use `postgres:18`.
