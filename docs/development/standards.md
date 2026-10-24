# Development — standards, testing, branching (Q18 + Rule 6)

Last updated: 2026-10-24 / Ref: decision 0033 (Standing Rule 8)

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
- **Rule 8 (regression integrity):** map every affected surface before changing; run the full
  gates plus browser checks for UI; add a regression test for every bug fix and new behavior;
  no collateral breakage. Any unavoidable breaking change needs owner approval, a decision
  record, and a migration/rollback plan.
- **Security gates:** gitleaks, `pip-audit` + `npm audit`, semgrep/CodeQL blocking; no secrets in repo.
