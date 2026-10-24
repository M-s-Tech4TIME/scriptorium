# Decision 0033 — Standing Rule 8: Regression Integrity (No Collateral Breakage)

Status: accepted · 2026-10-24 · Owner: alsechemist (directive delivered in
the preview #5 review chat, after approving the 0029–0032 theme stack)

## Context

The owner approved preview #5 and then made the preservation requirement
explicit: future features, UI updates, and improvements must not break or
compromise anything already approved — UI, backend, features, components,
elements, or contracts. The owner asked that this be a **standing rule for
the whole Scriptorium project**, not a one-off instruction for the next
theme pass.

The existing rules already cover adjacent ground: Rule 2 (secure,
high-quality code), Rule 4 (owner decision authority), Rule 6 (zero
skipped warnings), and Rule 7 (CI-green after every push). None of them
states the positive obligation to prove that a change preserves every
previously accepted behavior. This rule makes that obligation explicit and
gives it the same project-wide, non-negotiable status.

## Owner directive

> while introducing new features, new UI updates and making any
> improvements, make 100% sure that it doesn't break or compromise any
> other thing, whether its UI, whether is backend, whether its feather and
> even an approved or accepted feature, item, component, element, whatever
> there is, please make sure nothing breaks at all. Maintain the integrity
> of the whole project and its codebase.

## Decision — Standing Rule 8

### Standing Rule 8: Regression Integrity (No Collateral Breakage)

Every change must preserve the integrity of the whole project. A change is
not complete if it adds or fixes one thing while breaking, weakening, or
silently changing any other approved behavior, UI, component, element,
feature, contract, test, document, or backend behavior.

**8.1 Whole-project scope.** This applies to UI, backend, data,
build/staging, packaging, security, accessibility, documentation, and
tests. "It works on the changed page" is not sufficient.

**8.2 Pre-change impact review.** Before implementing, identify every
affected surface and the existing tests/contracts that protect it. If a
change necessarily alters an approved behavior, stop and obtain owner
approval under Rule 4; record it.

**8.3 Mandatory verification.** Every change runs the full gates: ruff
lint/format, `mypy --strict`, `pytest -W error`, Sphinx `-W`/build/artifact
tests, and browser checks for UI changes. Every bug fix and new behavior
gets a regression test. No skipped warnings or tests.

**8.4 No silent regressions.** If a regression is found, stop new work,
fix the root cause, add a test that fails without the fix, and report it.
Do not paper over it or trade one approved behavior for another.

**8.5 Definition of Done.** A commit/push is complete only when existing
approved behavior is preserved, verification evidence is recorded, and
docs/brain/changelog are updated in the same commit.

**8.6 Breaking changes.** Any unavoidable breaking change requires
explicit owner approval, a decision record, a migration/rollback plan, and
a staged verification path. It is never implicit in a feature.

## Relationship to the other rules

- **Rule 4** still governs every choice. Rule 8 does not authorize a
  "preserve at all costs" workaround that silently changes an approved
  behavior; it requires stopping and asking.
- **Rule 6** makes warnings non-skippable; Rule 8 makes existing behavior
  non-skippable. The full `pytest -W error` gate is shared evidence.
- **Rule 7** remains the push discipline: green CI after every push,
  fix-on-red, no stacking on red.
- **Rule 2** supplies the quality/security baseline; Rule 8 adds the
  regression-proof obligation on top of it.

## Consequences

- The Definition of Done in `AGENTS.md` now includes Rule 8.
- Every future theme/UI change must include a regression check for the
  surfaces it touches, not only a test of the new behavior.
- The 0034 fourth-feedback batch is the first change executed under this
  rule; it will verify the previously approved search, dialog, toggles,
  clear control, scrollspy, weights, and inline-code behavior in addition
  to the three new fixes.
- Any unavoidable breaking change becomes an owner decision with a
  migration/rollback plan; it is never folded silently into a feature.

## Files

- `project-details.md` §0a — full rule text and the standing-rules table.
- `AGENTS.md` — summary + Definition of Done.
- `docs/development/standards.md` — verification bullet.
- `docs/onboarding/agent-guide.md` — agent checklist.
- `docs/README.md` — rules status.
- `docs/brain/DECISIONS-INDEX.md` and brain state/handoff/tasks.
- `docs/changelog/2026-10-24-standing-rule-8-regression-integrity.md`.
