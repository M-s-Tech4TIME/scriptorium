# 0009 — Standing Rule 6 zero-skipped-warnings (Q19)

Status: accepted | Date: 2026-10-16 | Approver: owner (new non-negotiable rule)
Decision: No warning/error/diagnostic/highlight skipped; root-cause fix; suppressions only via owner approval + decision ref + scoped allowlist + expiry. CI: -W error everywhere, sphinx -W, lintian/rpmlint clean.
Consequences: Joins Rules 1–5; in AGENTS.md + development/standards.md; slows upgrades but keeps them safe.
