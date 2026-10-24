# Changelog 2026-10-24 — Standing Rule 8: regression integrity

## What landed

- Added **Standing Rule 8 — Regression Integrity (No Collateral Breakage)**
  to the project-wide rules, exactly as approved by the owner in the
  preview #5 review.
- Recorded the full rule and its rationale in
  `docs/decisions/0033-standing-rule-8-regression-integrity.md`.
- Added the summary and Definition of Done clause to `AGENTS.md`.
- Added the verification bullet to `docs/development/standards.md`.
- Added the agent checklist item to `docs/onboarding/agent-guide.md`.
- Updated the docs status line to Rules 1–8.
- Synced the brain index, current state, handoff, tasks, and open
  questions.

## Why

The owner approved preview #5 and directed that all future features, UI
updates, and improvements must preserve every previously approved
behavior and the integrity of the whole codebase. The existing rules
covered quality, warnings, decisions, and CI but did not state the
positive regression-proof obligation. Rule 8 makes that obligation
explicit and enforceable.

## Verification

Docs/governance only; no runtime behavior changed. The full backend gates
remain green from the approved baseline commit (`80 passed / 36 skipped`,
ruff + `mypy --strict` clean). The next theme change (0034) is the first
change executed under Rule 8 and will include the full regression matrix.
