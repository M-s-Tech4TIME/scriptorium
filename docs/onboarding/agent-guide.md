# Agent guide (for AI coding agents)

Last updated: 2026-10-24 / Ref: decision 0033 (Standing Rule 8)

1. **Resume first:** `AGENTS.md` → `docs/brain/README.md` → SUMMARY/CURRENT/HANDOFF/TASKS/OPEN-QUESTIONS → `git log`/`status` reconcile.
2. **Rule 4 script:** question + ≥2 options + trade-offs + recommendation → WAIT. Park in `OPEN-QUESTIONS.md` if owner away.
3. **Commits:** Conventional (`feat:`, `fix:`, `docs:`, `sec:`, `chore:`), small scope, docs+brain same commit, changelog entry, 5 gates pass.
4. **Forbidden without approval:** new dep, version change, name, default/limit, suppression/allowlist, schema change, scope cut.
5. **Rule 6:** zero skipped warnings. Fix root cause. `ruff/mypy --strict`, `eslint --max-warnings 0`,
   `tsc --noEmit`, `pytest -W error`, `sphinx -W`, `lintian`/`rpmlint` clean.
6. **Rule 8:** no collateral breakage. Map affected surfaces before changing; run full gates +
   browser checks for UI; add a regression test for every fix/new behavior; any breaking change
   needs owner approval + decision record + migration/rollback plan.
7. **Context full?** Finish/park safely, write `HANDOFF.md` + `SESSION-LOG/YYYY-MM-DD-*.md`.
