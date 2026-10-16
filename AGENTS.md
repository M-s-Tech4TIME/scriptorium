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

## Where to start (every session)
1. Read this file, then `docs/brain/README.md`.
2. Read `docs/brain/PROJECT-SUMMARY.md`, `CURRENT-STATE.md`, `HANDOFF.md`, `TASKS.md`, `OPEN-QUESTIONS.md`.
3. Reconcile with `git log` / `git status`. Do not re-scan the whole codebase.
4. Continue from `HANDOFF.md` next steps. Do not proceed on anything blocked by an open question.

## Frozen foundation (changes need owner approval)
- Section 8: monorepo, nfpm, web+worker systemd units (`scriptorium-web`, `scriptorium-worker`,
  user `scriptorium`), FHS `/opt`+`/etc/scriptorium`+`/var/lib|log|cache/scriptorium`,
  file+env+`setup` config, explicit `migrate`, bundled frontend, GPG+SBOM/provenance,
  GitHub Releases first then static APT/YUM repo.
- Stack: Python 3.12.x, Node 24 LTS, React 19.3.x, TS 7.0.2, TipTap 3.31.x, Sphinx 9.1.0,
  docutils 0.22.4 (0.23 gated), MyST 5.1.0, FastAPI 0.143.0, SQLA 2.1.4, Alembic 1.20.0,
  Celery 5.6.3 + Redis, PG 18.x exclusive, TipTap-JSON canonical, generic-tree schema.
- Workflow: Conventional Commits, trunk-based (`main` + `feat/*`), 5 CI gates
  (lint-type-test, security, docs, brain, packaging).

## Definition of Done (every commit/push)
Code meets Rule 2 + Rule 6 checks; `docs/` + `brain/` updated same commit; changelog entry;
CI gates pass; every decision owner-approved + recorded.
