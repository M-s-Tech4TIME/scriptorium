# HANDOFF

Last updated: 2026-10-20 / on `dev`, commit C (M2 conversion) staged with this sync

## Was doing
M2 commit C: conversion layer (`backend/app/conversion/` —
`tiptap.py`, `import_doc.py`, `export_rst.py`, `export_myst.py`),
`tests/test_roundtrip.py` (40 cases), mypy override made effective
(`mypy --config-file backend/pyproject.toml backend/` in CI + 3 typed
JSONB columns), docs (`docs/technology/conversion.md`, changelog
2026-10-20-m2-conversion.md) + this brain sync.

## Next steps (in order)
1. Commit on `dev` (Conventional Commits + Co-authored-by trailer), push,
   verify CI green ×3 via `gh run list` (Rule 7; packaging slowest).
2. M3 plan proposal for owner approval (Rule 4): REST endpoints design —
   routers, permissions matrix, IDOR strategy, working-copy semantics.
3. Only after approval: implement M3 on `dev`.

## Gotchas (carried)
- docutils 0.22.4 inline markup never nests; heading levels are sequential;
  title/subtitle docinfo convention — all probed, encoded in 0017 +
  `docs/technology/conversion.md`.
- CI mypy MUST use `--config-file backend/pyproject.toml` (overrides live
  there); ruff/pytest steps unchanged.
- Live-DB tests skip offline; need PG18 with schema at migration head
  `0002_refresh_tokens`.
- Two earlier sessions derailed into corrupted output after long numbered
  plans — keep per-step work small; write files one at a time.
- `gh run list --repo M-s-Tech4TIME/scriptorium --limit 3` verifies CI;
  ~5–10 min per push.
