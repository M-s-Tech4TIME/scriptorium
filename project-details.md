# Scriptorium: Project Brief (v1)

## 0. Note to Open Code (read first)

This document is the owner's starting brief. Do the deep thinking yourself: analyze, plan, and design the architecture, data model, module boundaries, and implementation roadmap from scratch. But **you do not decide anything on your own.** Every decision, of any size, is proposed to the owner and approved by the owner before it takes effect (Standing Rule 4). Your job is to research, reason, present options with a recommendation, and then wait for the owner's answer.

Before writing any feature code, read **Section 0a (Standing Rules)** in full, and note that **Section 8 (Distribution, Packaging, and Repository Strategy) must be decided with the owner before implementation proceeds past initial setup.** Those rules outrank feature work, deadlines, and convenience.

**If your context was reset or has filled up:** do not re-analyze the whole codebase. Follow the resume protocol in `docs/brain/README.md` (Standing Rule 3).

---

## 0a. Standing Rules (Non-Negotiable, Project-Wide)

These rules apply from the first commit to the last, across every phase, for every contributor (human or coding agent). They are not v1-only and not optional. If a task conflicts with a Standing Rule, the rule wins. **Standing Rule 4 (Owner Decision Authority) governs how every other rule is carried out.**

### Standing Rule 4: Owner Decision Authority (No Silent Decisions)

Open Code, and any other coding agent or contributor, must never take a decision without the owner's explicit approval. This applies to every decision, regardless of size, scope, or how obvious the answer seems.

**4.1 What counts as a decision (non-exhaustive).** Choosing a library, tool, service, or version; naming things (modules, endpoints, database tables, files, branches); picking a design or UI approach; selecting a data model, schema, or storage layout; resolving an ambiguity in this brief; changing, adding, or dropping scope; deviating from this brief in any way; choosing between two valid implementation approaches; adding or removing a dependency; setting a default, limit, or configuration value; deciding how to handle an edge case or error; refactoring or restructuring; and deciding to skip, defer, or postpone anything.

**4.2 No silent actions of any kind.**
- No silent choices: do not pick an option and move on.
- No silent drops: do not omit, defer, simplify, or descope anything without telling the owner and getting approval.
- No silent reactions: do not change course, work around a problem, or substitute an approach without telling the owner and getting approval.
- No silent assumptions: when something is unclear, ask. If an assumption is unavoidable, state it and get confirmation before relying on it.
- Anything not covered by this brief is not "implicitly allowed". It is a question for the owner.

**4.3 How to ask.** When a decision arises, stop that line of work and present to the owner:
- The question or decision needed, in plain language
- The realistic options (at least two where they exist)
- The trade-offs of each (security, maintainability, performance, complexity, cost, effect on future phases)
- Your recommendation and why
- Then wait for the owner's answer.

Batch related questions so the owner is not interrupted needlessly, but never batch them in a way that hides a decision. If the owner is unavailable, park the question in `docs/brain/OPEN-QUESTIONS.md` and continue only with work that does not depend on the answer. Never answer your own question to keep going.

**4.4 Recording.** Every approved decision is recorded as a decision record (Rule 1.4) that includes: the owner's approval, its date, and the options that were considered. A decision record without owner approval is a proposal, not a decision. Pending approvals are listed in `docs/brain/OPEN-QUESTIONS.md`, and approved ones in `docs/brain/DECISIONS-INDEX.md`.

**4.5 Reporting.** If an unapproved decision is ever found to have been made, whether by mistake or oversight, report it to the owner immediately, in plain language, and offer to revert or to seek approval.

**4.6 What does not need a question.** Carrying out an already-approved decision exactly as approved, and mechanical work with no alternative (for example, fixing a typo, or applying a formatting rule the owner already approved). When in doubt, ask.

### Standing Rule 1: Living Documentation

Documentation is a first-class deliverable, prioritized as highly as the code itself.

**1.1 Dedicated documentation folder.** The repository contains a top-level `docs/` folder that is maintained continuously. It records every decision, every piece of work done, how things are implemented, and what lives where.

**1.2 Required structure (propose refinements to the owner, but keep these categories):**

```
docs/
├── README.md                  # Index and navigation for all documentation
├── brain/                     # Agent memory (see Standing Rule 3)
├── onboarding/                # Start here: zero-to-productive guide
│   ├── getting-started.md     # Setup, run, test, build, deploy locally
│   ├── codebase-map.md        # "Where is X? Where do I change Y?" lookup
│   ├── common-tasks.md        # Step-by-step recipes (add a Sphinx directive
│   │                          #   mapping, add an API endpoint, add a UI block...)
│   └── agent-guide.md         # Instructions for AI coding agents
├── architecture/              # System design, diagrams, data flow, module boundaries
├── decisions/                 # Decision records (ADR style), numbered, immutable once accepted
├── structure/                 # File and folder structure, naming conventions
├── development/               # Coding standards, testing strategy, branching, commit conventions
├── security/                  # Threat model, secure coding rules, security decisions
├── technology/                # Each technology: what, why, exact version, support status (Rule 5)
├── operations/                # Deployment, configuration, environments, runbooks
│                              #   (including administrator installation guides, see Section 8)
├── changelog/                 # Chronological log of work done, per commit/push
└── roadmap/                   # Phases, milestones, open questions
```

Also place an `AGENTS.md` (or equivalent) at the repository root that points coding agents to `docs/onboarding/agent-guide.md` and `docs/brain/README.md`, and restates the Standing Rules in brief, with Rule 4 first.

**1.3 Update triggers (mandatory).** Documentation is updated in the same commit as the change that requires it, and verified before every push. At minimum, update docs whenever any of the following happens:
- A feature, module, endpoint, or component is added, changed, or removed
- A file or folder is created, moved, renamed, or deleted (update `structure/` and `codebase-map.md`)
- A technology, library, or version is introduced or changed (update `technology/`)
- An architectural or design decision is made (add a decision record)
- A security-relevant change is made (update `security/`)
- Anything is discovered that would surprise a future contributor

**1.4 Decision records.** Every significant decision gets a numbered record containing: context, options considered, decision, consequences, owner approval (who, when), and status (proposed / accepted / superseded). Superseded records are kept, never deleted.

**1.5 Onboarding requirement.** A brand-new contributor, human or coding agent (Open Code, Claude, or any other), must be able to read `docs/` alone and answer, without asking anyone:
- What is this project and how is it structured?
- Where does the code for a given feature live?
- What do I edit, where, and how, to make a given kind of change?
- How do I run, test, and build it?
- Why were the key decisions made?

The `codebase-map.md` and `common-tasks.md` files exist specifically to make this possible and must stay accurate.

**1.6 Enforcement.** Propose to the owner mechanisms so this rule is enforced rather than aspirational, for example:
- A pull request / commit checklist item: "docs updated"
- A CI check that fails when source changes land without any corresponding `docs/` change (heuristic, tuned to avoid noise)
- Link and structure validation of the docs folder in CI
- A changelog entry required per push

**1.7 Definition of Done.** No task, commit, or push is complete until its documentation is updated. Code without matching documentation is considered unfinished.

### Standing Rule 2: Secure, High-Quality Code From Day One

Security and quality are built in from the first line, never retrofitted.

**2.1 Standards.** Follow well-recognized, industry-standard practices throughout. Anchor to established references, for example:
- OWASP Top 10 and OWASP ASVS for web application security
- A secure SDLC approach (threat modeling at design time, security review at implementation time)
- Language-specific best practices and style guides for Python and TypeScript
- Principle of least privilege, defense in depth, secure-by-default configuration

**2.2 Minimum practices (propose additions to the owner):**
- **Input handling:** validate and sanitize all input at trust boundaries; encode all output. This is critical because user content drives Sphinx builds and is rendered as HTML.
- **Authentication and authorization:** strong password hashing, secure session/token handling, role-based access control, per-project authorization checks on every request.
- **Secrets management:** no secrets in the repository, ever; environment- or vault-based configuration; secret scanning in CI.
- **Dependency hygiene:** pinned versions, automated vulnerability scanning, and a policy for timely updates (see Rule 5).
- **Build isolation:** Sphinx builds run sandboxed with restricted filesystem, network, CPU, memory, and time limits, since build inputs are untrusted. Evaluate the risk of Sphinx extensions and arbitrary `conf.py` content and restrict them accordingly.
- **Data protection:** TLS everywhere, secure headers, CSRF/XSS/SQL-injection/SSRF/path-traversal protections, safe file upload handling (images).
- **Logging and auditing:** structured logs, no sensitive data in logs, audit trail for security-relevant actions.
- **Error handling:** no internal details leaked to clients.

**2.3 Quality practices (propose additions to the owner):**
- Static typing (TypeScript strict mode; Python type hints with a type checker)
- Linters and formatters enforced automatically (pre-commit hooks and CI)
- Automated tests at unit, integration, and end-to-end levels, with the editor-to-RST/MyST conversion treated as a high-test-coverage area (round-trip tests)
- Mandatory code review (or equivalent self-review checklist for agents) before merge
- Small, well-scoped commits with a consistent commit message convention
- Static analysis (SAST) and dependency scanning in CI; a failing security check blocks merge
- Clear module boundaries, no dead code, no copy-paste duplication, meaningful naming

**2.4 Security documentation.** Maintain a threat model and secure-coding guide in `docs/security/`, updated as the system evolves (this ties Rule 2 to Rule 1).

### Standing Rule 3: Persistent Agent Memory ("Brain" Folder)

The coding agent must never lose track of the project. A dedicated memory folder, `docs/brain/`, acts as the agent's persistent brain so that when its context window fills, overflows, or resets, it can resume exactly where it left off without re-reading or re-analyzing the entire codebase.

**3.1 Purpose.** The brain exists so that:
- No decision, progress, or discovery is ever lost to a context reset
- A fresh agent session (the same agent after a reset, or a different agent entirely) can take over seamlessly
- The full codebase never has to be re-analyzed from scratch to regain context

**3.2 Required structure (propose refinements to the owner, but keep these roles):**

```
docs/brain/
├── README.md              # Resume protocol: what to read, in what order, after any reset
├── PROJECT-SUMMARY.md     # Compact, always-current summary: what Scriptorium is,
│                          #   stack, architecture in brief, key conventions
├── CURRENT-STATE.md       # Where the project is right now: phase, completed work,
│                          #   in-progress work, known broken things, last commit reference
├── HANDOFF.md             # Written at the end of every session or when context is
│                          #   nearly full: exactly what was being done, the very next
│                          #   steps, half-finished work, uncommitted changes, gotchas
├── TASKS.md               # Backlog and task board: todo / in progress / done / blocked
├── DECISIONS-INDEX.md     # One-line index of all decision records with approval status,
│                          #   linking into docs/decisions/ (the brain links, not duplicates)
├── OPEN-QUESTIONS.md      # Questions awaiting owner approval (Rule 4), assumptions to
│                          #   confirm, things to verify. Nothing here may be self-answered.
├── MODULE-NOTES/          # One short summary per module/area: purpose, key files,
│                          #   public interfaces, invariants, pitfalls, related tests
├── GLOSSARY.md            # Project-specific terms, naming, and conventions
└── SESSION-LOG/           # One short dated file per session: what was done, why,
                           #   outcome, pointers to commits and decision records
```

**3.3 Resume protocol (mandatory, documented in `docs/brain/README.md`).** At the start of every session, and immediately after any context reset, the agent must:
1. Read `AGENTS.md`, then `docs/brain/README.md`.
2. Read `PROJECT-SUMMARY.md`, `CURRENT-STATE.md`, and `HANDOFF.md`.
3. Read `TASKS.md` and `OPEN-QUESTIONS.md`. Do not proceed on anything that depends on an unanswered question.
4. Reconcile the brain with reality: compare the last commit referenced in `CURRENT-STATE.md` against `git log` and `git status`. If they differ, investigate only the delta and update the brain first.
5. Read only the `MODULE-NOTES/` and source files relevant to the task at hand. Do not re-scan the whole codebase.
6. Continue from the "next steps" in `HANDOFF.md`.

**3.4 Update protocol (mandatory).**
- Update the brain after every meaningful unit of work, and in the same commit as the code change it describes.
- Do not wait for the context to fill up. Keep `CURRENT-STATE.md` and `HANDOFF.md` current continuously, so a sudden reset loses nothing.
- When context usage is high, stop starting new work, finish or safely park the current step, and write a complete `HANDOFF.md` and `SESSION-LOG/` entry.
- Every brain file carries a "last updated" date and the commit reference it reflects.
- Record decisions, assumptions, dead ends, and rejected approaches, so they are not re-explored or re-litigated.

**3.5 Quality rules for the brain.**
- Compact and scannable: the brain is a map and summary, not a copy of the code. Link to files and decision records instead of duplicating them.
- Consistent: fixed file names, fixed structure, and fixed templates so any agent can follow it without interpretation.
- Accurate over comprehensive: a stale brain is worse than a small one. If something is unverified, mark it as such.
- Pruned: archive old session logs and completed tasks periodically so the entry files stay short enough to load in full at the start of every session.
- Contains no secrets, credentials, or sensitive data (Standing Rule 2 applies to the brain too).

**3.6 Enforcement.** Propose to the owner safeguards, for example:
- A commit/push checklist item: "brain updated (CURRENT-STATE, HANDOFF, TASKS)"
- A CI check that flags source changes without a corresponding brain update, and validates required brain files and their "last updated" and commit-reference fields
- A reconciliation check that detects when `CURRENT-STATE.md` has drifted from the actual repository state

**3.7 Relationship to other docs.** The brain is the fast-resume layer; the rest of `docs/` is the full reference. The brain points into `docs/` for depth. Decisions live in `docs/decisions/`, and the brain only indexes them.

### Standing Rule 5: Technology Versions (Latest and Stable, Built for Long-Term Maintenance)

The technology stack (Section 9) is decided. The versions of every technology, library, and tool must be both **the latest and stable**, and chosen so the project can be maintained for a long time and upgraded easily.

**5.1 Selection criteria.** For every technology, language runtime, framework, library, and tool:
- Choose the **newest release that is stable**: a general-availability release, never an alpha, beta, or release candidate.
- Where a project offers long-term support (LTS) or a stable/maintained release line, prefer it, provided it is current.
- The selected version must be actively maintained, still receiving security fixes, and have a support window long enough to fit the project's lifetime.
- If "latest" and "stable" conflict (for example, a brand-new major release with known issues or an immature ecosystem), do not choose silently: present both options to the owner with trade-offs (Rule 4).

**5.2 Verify, do not assume.** Versions must be checked against official, current sources (official release pages, registries, changelogs, support/EOL tables) at the time of selection. Do not rely on training knowledge or memory for version numbers, since it may be outdated.

**5.3 Compatibility of the whole set.** Select versions as a coherent set, not one by one. Verify cross-compatibility before approval, especially across: the Python runtime, Sphinx, docutils, MyST-Parser, Sphinx extensions and themes, the backend web framework and its dependencies, the Node.js runtime, React, TypeScript, TipTap and its extensions, PostgreSQL and its drivers, and the task queue. Because Scriptorium will ship as `.deb` and `.rpm` packages (Section 8), also verify compatibility with the target Linux distributions and their system-provided libraries and runtimes. If the latest version of one component blocks another, present the conflict and options to the owner.

**5.4 Reproducibility and low collision risk.**
- Pin exact versions and commit lockfiles for every ecosystem (Python and JavaScript).
- Use isolated, reproducible environments; the Sphinx build environment must be isolated from the application's own dependencies.
- Keep the dependency footprint small: do not add a dependency where the standard library or an existing dependency suffices (any new dependency is still a Rule 4 decision).
- Avoid unmaintained, abandoned, or single-maintainer-risk libraries without raising the risk to the owner.
- Keep third-party code behind clear module boundaries (adapters or wrappers around the Sphinx build, the editor, and the database layer) so that upgrading or replacing a dependency touches few places.

**5.5 Easy future upgrades.**
- Define an upgrade process and propose it to the owner: automated dependency update proposals, CI that runs the full test suite against upgrades, and a regular review cadence.
- Upgrades, especially major ones, are Rule 4 decisions: proposed to the owner with release notes, breaking changes, migration effort, and a rollback plan. They are never applied silently.
- Track support end dates so upgrades are planned before a version reaches end of life.
- Maintain strong automated tests (Rule 2.3), especially around the editor-to-RST/MyST conversion and the Sphinx build pipeline, so upgrades can be verified quickly and safely.

**5.6 Documentation.** Maintain `docs/technology/` with, for each technology: exact version, release date, support or end-of-life date, the reason it was chosen, the date the version was last verified, and where it is used. Include a compatibility matrix for the full set. Update it in the same commit as any version change (Rule 1.3).

### Standing Rule 8: Regression Integrity (No Collateral Breakage)

Every change must preserve the integrity of the whole project. A change is not complete if it adds or fixes one thing while breaking, weakening, or silently changing any other approved behavior, UI, component, element, feature, contract, test, document, or backend behavior.

**8.1 Whole-project scope.** This applies to UI, backend, data, build/staging, packaging, security, accessibility, documentation, and tests. "It works on the changed page" is not sufficient.

**8.2 Pre-change impact review.** Before implementing, identify every affected surface and the existing tests/contracts that protect it. If a change necessarily alters an approved behavior, stop and obtain owner approval under Rule 4; record it.

**8.3 Mandatory verification.** Every change runs the full gates: ruff lint/format, `mypy --strict`, `pytest -W error`, Sphinx `-W`/build/artifact tests, and browser checks for UI changes. Every bug fix and new behavior gets a regression test. No skipped warnings or tests.

**8.4 No silent regressions.** If a regression is found, stop new work, fix the root cause, add a test that fails without the fix, and report it. Do not paper over it or trade one approved behavior for another.

**8.5 Definition of Done.** A commit/push is complete only when existing approved behavior is preserved, verification evidence is recorded, and docs/brain/changelog are updated in the same commit.

**8.6 Breaking changes.** Any unavoidable breaking change requires explicit owner approval, a decision record, a migration/rollback plan, and a staged verification path. It is never implicit in a feature.

### How the Standing Rules Work Together

| Event | Required action |
|---|---|
| Any decision, however small | Stop, ask the owner with options and a recommendation, wait for approval (Rule 4) |
| Session start or context reset | Follow the resume protocol in `docs/brain/README.md`; reconcile brain with `git log` (Rule 3) |
| Any commit | Code meets Rule 2 checks; existing approved behavior preserved; matching docs and brain updated in the same commit (Rules 1, 2, 3 and 8) |
| Any bug fix or new feature | Pre-change impact review; full gates; regression test added; no collateral breakage (Rule 8) |
| Any push | Changelog entry added; docs and brain verified; CI security and quality gates green after the push (Rules 7 and 8) |
| Any design decision | Owner-approved decision record written; `DECISIONS-INDEX.md` updated |
| Any unavoidable breaking change | Explicit owner approval, decision record, migration/rollback plan, staged verification (Rule 8.6) |
| Any new technology or version change | Owner approval; verified latest-stable and compatible; `docs/technology/` updated (Rules 4 and 5) |
| Distribution, packaging, or repository structure question | Governed by Section 8; owner decision required before implementation proceeds past initial setup |
| Context nearly full | Park current work safely; write `HANDOFF.md` and `SESSION-LOG/` entry |
| New contributor joins | Onboarding docs and brain are sufficient to start without help; gaps found are fixed immediately |

### First Actions for Open Code (before feature work)

1. Confirm to the owner that you have read and understood the Standing Rules.
2. Research and present for decision: **Section 8 (Distribution, Packaging, and Repository Strategy)**. This is a foundational decision and must be resolved before implementation proceeds past initial setup.
3. Research and present for approval: the versions of every technology in the stack (Rule 5), verified against official sources, with the compatibility matrix.
4. Propose for approval: the `docs/` structure (including `docs/brain/` with all required files and templates), `AGENTS.md`, and onboarding files.
5. Propose for approval: coding standards, commit conventions, and CI quality, security, docs, and brain gates.
6. Draft for approval: the initial threat model and architecture decision records.
7. Seed the brain: `PROJECT-SUMMARY.md`, `CURRENT-STATE.md`, `HANDOFF.md`, `TASKS.md`, `OPEN-QUESTIONS.md`.
8. Only after the owner approves the plan, begin v1 implementation.

---

## 1. Vision

Scriptorium is a technical documentation platform inspired by Read the Docs and built entirely on the Sphinx documentation engine. It uses Sphinx's modules, extensions, and build system fully, but removes the need for authors to hand-write reStructuredText (RST) or MyST Markdown.

Authors work in a Microsoft Word-like WYSIWYG editor in the browser. The editor's output is converted into valid Sphinx source (RST or MyST), which Sphinx builds and Scriptorium serves.

Scriptorium is designed first as a self-hosted, on-premises product that engineers and system administrators install on their own servers (see Section 8), with a possible SaaS offering as a later direction.

## 2. Problem Being Solved

With Read the Docs and plain Sphinx, authors must:
- Hand-write `.rst` or MyST files and learn Sphinx directive syntax
- Build locally or via CI to preview results
- Manage the source tree, `conf.py`, and TOC trees manually

Scriptorium moves all of this into a web UI. Authoring, formatting, structuring, and publishing are fully manageable from the platform, and users never need to touch raw markup.

## 3. Target Experience

- Word-like editing: ribbon or toolbar, headings, bold, italic, underline, font sizing, lists, tables, links, blockquotes.
- Native documentation elements that map to Sphinx directives: code blocks (language selection and syntax highlighting), images, and note, attention, warning, tip, and danger admonitions, plus cross-references.
- Live synchronization between editor content and valid Sphinx source.
- Technical-documentation feel with polished rendering of the published output.
- Visual identity: enterprise-serious and classy, with an old-world, alchemical, scriptorium/grimoire undertone. It should not look like a generic SaaS product.

## 4. Project and Content Structure

- Multiple projects per platform, each with categories.
- Hierarchical structure: main branches, sub-branches, and mid-level sub-branches, all manageable in the UI.
- The table of contents (TOC) is fully controllable from the UI (add, reorder, nest, rename, remove) and drives Sphinx's native `toctree` system.
- Every structural aspect (categories, hierarchy, page ordering, TOC) must be manageable without manual file or folder editing.
- Priority: project structure and TOC management should be among the most polished parts of the UX.

## 5. Source Format Support

- Both RST and MyST Markdown are supported, since modern Sphinx supports both.
- The user chooses the format per project at creation time.
- Default: RST. MyST is opt-in.

## 6. Build and Hosting

- Scriptorium owns the full pipeline: authoring, conversion to RST/MyST, Sphinx build, and serving the built site.
- It is self-contained and has no dependency on Read the Docs infrastructure.
- Builds are slow and must run as background jobs so they never block the UI.
- Scriptorium is deployed by the people who use it, on their own servers (Section 8). cPanel/shared hosting was considered and ruled out as a runtime for the application because it is a poor fit for Python async backends, background build workers, and future real-time features.

## 7. Phasing

### Version 1 (in scope)
- WYSIWYG editor synced to Sphinx-valid source
- RST and MyST support (RST default, chosen per project)
- Project, category, hierarchy, and TOC management via UI
- Sphinx build pipeline run and served by Scriptorium
- Single-editor-at-a-time editing with version history
- Polished, enterprise-serious UI with scriptorium/grimoire character
- Installable on-premises as native Linux packages (subject to the decisions in Section 8)

### Later Phase A: Versioning and Branching (not in v1)
- Multiple versions and branches per project, driven by Git tags, similar to Read the Docs.
- Git mechanics must be abstracted from the user: a simple version picker and publishing experience, no raw Git operations.
- Open design question for the owner: the exact UX for versions over time (for example, a documented project releasing v1.0, v2.0, and so on). It should be sophisticated but easy to manage. Open Code researches and proposes options; the owner decides (Rule 4).
- Design v1 so this phase can be added without a rewrite.

### Later Phase B: Real-Time Collaboration (not in v1)
- Google Docs-style multi-user simultaneous editing.
- Design the v1 document model so a collaborative layer can be added later.

## 8. Distribution, Packaging, and Repository Strategy (Must Be Decided Before Implementation Proceeds Further)

This is a foundational, owner-level decision (Rule 4) that must be researched, proposed, discussed, and decided before feature implementation goes beyond the initial setup. It is not to be settled implicitly partway through the project.

### 8.1 Deployment Model

Scriptorium's primary deployment model is **on-premises, self-hosted**. Engineers or system administrators install and run it in their own environment and servers, similarly to how self-hosted platforms are typically deployed. This is the model to design and build for first.

A future transition toward a SaaS offering (a centrally hosted, publicly available version run by the owner or by other companies/entities) is a known future direction, not a current requirement. The on-premises architecture must not be designed in a way that forecloses an eventual SaaS path, but SaaS-specific concerns (multi-tenant isolation at scale, billing, centralized operations) are out of scope for now and are not to be built prematurely.

### 8.2 Distribution Format

- The primary distribution target is native Linux packages: **`.deb`** (Debian/Ubuntu family) and **`.rpm`** (RHEL/Fedora/openSUSE family).
- Installation should be "plug and play": a system administrator installs the package, and the application comes up correctly configured enough to begin setup, with proper accompanying documentation for configuring and running it on their own server.
- Open Code is to research and propose: how the application should be packaged (for example, as a systemd service, its process layout, where configuration, data, and logs live on disk following Linux filesystem conventions), how the frontend build is bundled and served, how the database connection and migrations are handled at install/upgrade time, and how configuration is supplied (config file, environment variables, or a setup wizard).
- Open Code is also to research and propose how packages are signed and how supply-chain integrity is ensured, since administrators will install them on their own servers.

### 8.3 Repository Structure

Open Code is to research and propose a repository strategy (monorepo vs. multiple repositories, and why), covering at minimum:
- Where the frontend, backend, and packaging/release tooling live
- How database schema migrations are tracked and versioned (noting that PostgreSQL itself is an external dependency, not something packaged by Scriptorium)
- How this structure supports building `.deb` and `.rpm` packages from CI
- How this structure keeps a future SaaS path open without being built for it now

### 8.4 Release and Package Hosting

- The owner has an existing domain, currently pointed at cPanel-based hosting, that can be used to host release packages and documentation. cPanel itself was already ruled out as an application runtime (Section 6), but the domain is available for static hosting purposes such as a package repository or a documentation/landing site.
- GitHub Releases is a candidate for hosting the actual package files.
- A proper APT-style and YUM/DNF-style package repository (so installs can use standard package manager commands) is a candidate for later, potentially served from the owner's domain.
- Open Code is to research and propose concrete options for both release hosting and, if desired, a proper package repository, with trade-offs, for the owner to decide.

### 8.5 Requirement

This entire section (8.1 through 8.4) must be researched by Open Code and presented to the owner as explicit options with a recommendation (per Rule 4), and a decision reached and recorded (per Rule 1.4), before implementation work proceeds past the initial project setup. This is treated as a first-order architectural decision, not something to resolve mid-project.

## 9. Technical Stack (decided by the owner)

The stack below is decided. Changing any part of it requires the owner's explicit approval (Rule 4). Versions follow Standing Rule 5.

**Frontend**
- React with TypeScript
- TipTap as the editor framework. Chosen over Lexical for maturity, gentler learning curve, strong React/TypeScript integration, and a plugin architecture suited to custom nodes that map to Sphinx directives (admonitions, code blocks, TOC elements).

**Backend**
- Python. Sphinx is a pure Python tool, so a Python backend can invoke it natively without reimplementation. Rust was considered and set aside for v1; it may be revisited later for a narrow performance-critical component, but only with the owner's approval.
- Web framework: FastAPI was suggested, but it is not final. Open Code presents the options and the owner chooses (Rule 4).
- Background job queue for Sphinx builds (Celery or comparable): options proposed to the owner.

**Database**
- PostgreSQL for structured data: users and permissions, project and category ownership, TOC and page metadata, build history and status, version history, and publish state.
- Document content itself is stored as source files, not as database rows. Open Code proposes storage approaches; the owner decides.

**Infrastructure and Deployment**
- Deployment target is on-premises Linux servers, distributed as `.deb` and `.rpm` packages. The packaging, process layout, and hosting approach are decided through Section 8.

## 10. Key Technical Challenges for Open Code to Research and Propose Solutions For

Each of these results in options presented to the owner, not in a unilateral choice (Rule 4).

- Reliable two-way mapping between the TipTap document model and RST/MyST (round-tripping, edge cases, directives).
- Representing the Sphinx project (`conf.py`, `toctree`, extensions) as UI-managed state.
- Sandboxing and isolating Sphinx builds safely, since user content drives builds.
- Theming of the published Sphinx output to match the Scriptorium identity.
- Storage and version-history design that will not block the future Git-tag versioning phase.
- Authentication, authorization, and multi-project tenancy.
- Packaging a multi-component application (frontend, backend, background workers, Sphinx build environment) into clean `.deb` and `.rpm` packages that install, upgrade, and uninstall safely (see Section 8).

## 11. Design and UX Priorities

- Ribbon- or toolbar-driven Word-like editor.
- Strong native support for code blocks, images, and admonitions.
- Classy, enterprise-serious look with an alchemical scriptorium character.
- Intuitive, fully UI-driven structure and TOC management.
- Overall: best-in-class UX for non-technical and technical authors alike.
- A smooth installation and first-run experience for system administrators.

## 12. Deliverables Requested from Open Code

Every deliverable below is presented to the owner for approval before it is treated as final (Rule 4).

1. Confirmation that the Standing Rules were read and understood.
2. Researched options, a recommendation, and a decision record for Section 8 (distribution, packaging, repository structure, and release hosting), resolved before implementation proceeds past initial setup.
3. The researched, verified version set for the full stack, with a compatibility matrix (Rule 5).
4. The foundation from Section 0a: `docs/` structure, `docs/brain/` with templates, `AGENTS.md`, onboarding docs, coding standards, and CI quality, security, docs, and brain gates.
5. A system architecture proposal, with options and a recommendation for each open design question.
6. A data model and storage design.
7. A threat model and risk list with mitigations, including the challenges in Section 10.
8. A phased implementation roadmap (v1 milestones, then Phases A and B).
9. Implementation of v1 after plan approval, with documentation, brain, and security checks maintained on every commit and push, and every decision approved by the owner along the way.
