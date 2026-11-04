# docs/ — Scriptorium living documentation (index)

> Rule 1: docs are a first-class deliverable, updated in the same commit as code.
> Rule 4: any change to approved content needs owner approval + decision record.

## Map
- `brain/` — fast-resume memory. Start here after `AGENTS.md`. See `brain/README.md`.
- `history/` — project-wide narrative + environment-migration handoff (`PROJECT-HISTORY.md`, `ENVIRONMENT-MIGRATION.md`).
- `onboarding/` — zero-to-productive: `getting-started.md`, `codebase-map.md`, `common-tasks.md`, `agent-guide.md`.
- `architecture/` — system design, data flow, module boundaries.
- `decisions/` — numbered ADRs `0001-*.md`, immutable once accepted.
- `structure/` — file/folder layout + naming conventions.
- `development/` — coding standards, testing, branching, commits, Rule 6 enforcement.
- `security/` — threat model, secure-coding rules, decisions.
- `technology/` — each technology: version, release/support dates, why, where used + `compatibility-matrix.md`.
- `operations/` — deploy, config, environments, runbooks, admin install guide.
- `changelog/` — per-push entries.
- `roadmap/` — phases, milestones, gates.

## Status (2026-11-04)
M0–M4 implementation, serving (0035), URL durability (0036), backup/restore
(0039), and server move/first-run + built-in TLS (0040) are implemented.
Decision 0040 adds the CLI first-run/move/verify lifecycle, a shared
no-shell-evaluation config loader, native HTTPS termination with a local
CA and HTTP→HTTPS `308`, and the `scriptorium:scriptorium` ownership
contract. M5 signing/provenance, page aliases, distribution, and the
dedicated SEO phase remain later; SEO still requires its own plan and
owner rulings. Approved: Q1–Q23, Rules 1–8. See
`brain/DECISIONS-INDEX.md`.
