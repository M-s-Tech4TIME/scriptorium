# Brain — resume protocol (mandatory, Rule 3.3)

## On session start / after any reset
1. Read `AGENTS.md`, then this file.
2. Read `PROJECT-SUMMARY.md`, `CURRENT-STATE.md`, `HANDOFF.md`.
3. Read `TASKS.md`, `OPEN-QUESTIONS.md`. Do not proceed on blocked items.
4. Reconcile: compare `CURRENT-STATE.md` commit ref vs `git log -1` + `git status --short`.
   If drift, investigate delta only, update brain first.
5. Read only relevant `MODULE-NOTES/` + source files. Never re-scan the whole repo.
6. Continue from `HANDOFF.md` next steps.

## Update protocol (Rule 3.4)
- Update brain in the same commit as code. Keep `CURRENT-STATE.md` + `HANDOFF.md` current.
- Every file: `Last updated: YYYY-MM-DD / Ref: <sha>`.
- No secrets in brain (Rule 2).
- Park owner questions in `OPEN-QUESTIONS.md`; index approvals in `DECISIONS-INDEX.md`.
