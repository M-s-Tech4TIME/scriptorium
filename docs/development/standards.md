# Development — standards, testing, branching (Q18 + Rule 6)

Last updated: 2026-10-16 / Ref: uncommitted

- **Python:** `ruff` lint+format, `mypy --strict`, hints required, `pytest -W error`.
  Pyright rejected (mypy has SQLA/Alembic history).
- **TS:** `eslint` flat + `prettier`, `strict` + `noUncheckedIndexedAccess`, `tsc --noEmit`,
  `eslint --max-warnings 0`, `vitest` + RTL. No `any` without approval.
- **Tests:** unit + integration + e2e; converter round-trip + build pipeline are high-coverage.
- **Commits:** Conventional (`feat/fix/docs/sec/chore` + scope), small, squash PRs.
- **Branching:** trunk `main` protected + `feat/*` short-lived; agent self-review checklist = reviewer.
- **Rule 6 enforcement:** Python `-W error`, `sphinx -W --keep-going`, `lintian`/`rpmlint` clean;
  suppressions only via owner-approved allowlist + expiry + decision ref.
- **Rule 7 (CI-green):** every push followed by a CI check; red CI stops new work until fixed
  and re-verified green on the same branch.
- **Security gates:** gitleaks, `pip-audit` + `npm audit`, semgrep/CodeQL blocking; no secrets in repo.
