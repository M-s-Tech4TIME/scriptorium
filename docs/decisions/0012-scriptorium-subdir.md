# 0012 — Work under scriptorium/ subdirectory (owner-directed amendment to 0001)

Status: accepted | Date: 2026-10-16 | Approver: owner (direct order, byte-identical move)
Context: Owner ordered all M0 work moved byte-identical into `scriptorium/`; future work under `scriptorium/`.
Options: (A) Move all tracked files via `git mv` into `scriptorium/`, repo root keeps only `.git` + `scriptorium/` (chosen) vs (B) keep flat root (rejected by owner).
Decision: (A). Verified byte-identical (sha256 per-file, 0 mismatches, 55 files).
Consequences: Amends 0001 layout only; all relative paths inside move together (nfpm `../backend` still resolves).
Known issue parked: `.github/workflows` moved to `scriptorium/.github/` is invisible to GitHub Actions (requires repo-root `.github/`). See OPEN-QUESTIONS.md Q-001 — CI will not run until owner picks a fix. No silent workaround applied (Rule 4).
