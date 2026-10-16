# OPEN-QUESTIONS

Last updated: 2026-10-16 / Ref: uncommitted (subdir move)

| ID | Question | Blocks | Asked |
|---|---|---|---|
| Q-001 | `.github/workflows` now lives at `scriptorium/.github/` (owner-ordered move) so GitHub Actions will not run CI. Options: (A) keep a repo-root `.github/workflows/` that checks out and delegates into `scriptorium/` (Recommended — restores CI, tiny root shim); (B) move `.github/` back to repo root while everything else stays under `scriptorium/`; (C) accept no GitHub CI (local validators only). Trade-offs: A keeps "everything under scriptorium" spirit with a 2-file shim; B splits layout; C loses blocking gates (violates Rule 2/6 enforcement). Recommendation: A. | CI gates (0008) | 2026-10-16 |

All Plan-mode questions Q1–Q23 answered. Nothing here is self-answered (Rule 4).
