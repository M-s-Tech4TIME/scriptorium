# AGENTS.md — Scriptorium coding agents (read first)

## Rule 4 first (Owner Decision Authority — non-negotiable)
Never take any decision without the owner's explicit approval — library, tool, version,
name, design, schema, default, limit, error handling, refactor, scope change, or
resolving a brief ambiguity. Present: question + options (≥2) + trade-offs
(security/maintainability/performance/complexity/cost/future) + recommendation, then WAIT.
Park blocked work in `docs/brain/OPEN-QUESTIONS.md`. Never self-answer. Report any
unapproved decision immediately with revert/approve options.

## The other Standing Rules (summary — full text in `project-details.md` §0a)
1. **Living docs (Rule 1):** update `docs/` in the same commit as code. No task done without docs.
2. **Secure high-quality code (Rule 2):** OWASP ASVS, validate at trust boundaries, no secrets
   in repo, sandboxed Sphinx builds, typed/linted/tested, SAST + dep scan blocking.
3. **Brain (Rule 3):** follow `docs/brain/README.md` resume + update protocols every session.
5. **Versions (Rule 5):** latest-stable + compatible as a set, pinned + locked, `docs/technology/` updated same commit.
6. **Zero skipped warnings (Rule 6):** no warning/error/diagnostic/highlight skipped. Fix root
   cause. Any suppression needs owner approval + decision record + scoped allowlist + expiry.
   CI enforces `-Werror` equivalents.
7. **CI-green after every push (Rule 7):** after every push, check CI; if red, stop new work,
   fix properly on `dev`, re-push, re-verify green. Never stack work on red CI.
8. **Regression integrity (Rule 8):** no collateral breakage. Map every affected surface before
   changing; run the full gates + browser checks for UI; add a regression test for every fix and
   new behavior; any unavoidable breaking change needs owner approval + decision record +
   migration/rollback plan. Preserve all previously approved behavior.

## Where to start (every session)
1. Read this file, then `docs/brain/README.md`.
2. Read `docs/brain/PROJECT-SUMMARY.md`, `CURRENT-STATE.md`, `HANDOFF.md`, `TASKS.md`, `OPEN-QUESTIONS.md`.
3. Reconcile with `git log` / `git status`. Do not re-scan the whole codebase.
4. Continue from `HANDOFF.md` next steps. Do not proceed on anything blocked by an open question.

## Frozen foundation (changes need owner approval)
- Section 8: monorepo, nfpm, web+worker+redis systemd units (`scriptorium-web`,
  `scriptorium-worker`, `scriptorium-redis`, user `scriptorium`), FHS
  `/opt`+`/etc/scriptorium`+`/var/lib|log|cache/scriptorium`,
  file+env+`setup` config, explicit `migrate`, bundled frontend, GPG+SBOM/provenance,
  GitHub Releases first then static APT/YUM repo.
- Stack (0037): Python 3.14.10 bundled, Node 26.13.0 LTS, React 19.3.1, TS 7.0.2,
  TipTap 3.32.1, Sphinx 9.2.0, docutils 0.22.4 (0.23 gated), MyST 5.1.0,
  FastAPI 0.162.0, SQLA 2.1.6, Alembic 1.20.1, asyncpg 0.32.0, Celery 5.6.3 +
  redis-py 6.4.0 + bundled Redis 8.10.2, PG 18.6 exclusive, TipTap-JSON canonical,
  generic-tree schema.
- Workflow: Conventional Commits, trunk-based (`main` + `feat/*`), 5 CI gates
  (lint-type-test, security, docs, brain, packaging).

## Definition of Done (every commit/push)
Code meets Rule 2 + Rule 6 + Rule 8 checks; `docs/` + `brain/` updated same commit; changelog entry;
existing approved behavior preserved with regression evidence; CI gates pass **and CI status
verified green after push (Rule 7)**; every decision owner-approved + recorded.
