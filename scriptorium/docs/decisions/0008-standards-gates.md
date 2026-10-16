# 0008 — Standards/gates Q18

Status: accepted | Date: 2026-10-16 | Approver: owner
Decision: ruff + mypy --strict (not pyright) + pytest -W error; eslint flat + prettier + strict + noUncheckedIndexedAccess + max-warnings 0 + tsc --noEmit + vitest; Conventional Commits; trunk main + feat/* squash; 5 blocking gates (lint-type-test, security, docs, brain, packaging).
Consequences: Strictest signal; slower triage on third-party noise (handled via Rule 6 allowlist).
