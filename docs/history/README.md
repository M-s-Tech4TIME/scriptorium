# History — project-wide record and environment handoff

Last updated: 2026-11-04 / Ref: server-move/first-run + built-in TLS (0040)

This directory exists so a new maintainer or AI agent can reconstruct
what happened, why the current system looks the way it does, and how to
resume on a different machine without guessing.

| File | Use |
|---|---|
| `PROJECT-HISTORY.md` | Narrative from bootstrap to the present: timeline, decision ledger, capability ledger, non-regression contracts, stack, limitations, branch state. |
| `ENVIRONMENT-MIGRATION.md` | Step-by-step new-machine checklist: prerequisites, clone, venvs, services, env vars, gates, TLS smoke, packaging, CI, branch sync, gotchas. |

## How this relates to the rest of `docs/`

- `docs/decisions/` is binding. If the history and a decision disagree,
  the decision wins.
- `docs/changelog/` is per-tranche. If the history and a changelog
  disagree about a specific change, the changelog plus code/tests win.
- `docs/brain/` is the live resume state. `HANDOFF.md` and
  `CURRENT-STATE.md` always describe the latest closeout hash and next
  step; the history gives the long context behind them.
- `docs/operations/` is the operator-facing runbook set. The history is
  not a substitute for those procedures.

## Maintenance rule

Update `PROJECT-HISTORY.md` in the same commit as a completed tranche
that changes a binding contract, the stack, the phase state, or the
branch/release model. Update `ENVIRONMENT-MIGRATION.md` whenever the
toolchain, local-service expectations, gate commands, or closeout
procedure changes. Keep `Last updated:` current (Rule 1) and never put
secrets, tokens, keys, or private archive contents in this directory.
