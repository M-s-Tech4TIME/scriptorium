# DECISIONS-INDEX

Last updated: 2026-10-28 / Ref: URL-durability phase (0036)

| ID | One-line | Status | Date | Approver |
|---|---|---|---|---|
| 0001 | Section 8 distribution/packaging/repo (Q1–Q9 monorepo/nfpm/systemd/FHS/migrate/bundled/GPG/Releases) | accepted | 2026-10-16 | owner |
| 0002 | Distro baselines (Ubuntu 24.04, Debian 12, RHEL 9, Fedora, Leap 15.6) | accepted | 2026-10-16 | owner |
| 0003 | Version set Rule 5 (Q10–Q12: Py3.12, docutils gate, proceed §9) | accepted | 2026-10-16 | owner |
| 0004 | PG 18.x exclusive + LTS/proven principle (Q15) | accepted | 2026-10-16 | owner |
| 0005 | Framework/queue/storage (Q13 FastAPI, Q14 Celery+Redis, Q17 fs+DB) | accepted | 2026-10-16 | owner |
| 0006 | TS 7.0.2 owner override (Q16 vs LTS rule) | accepted | 2026-10-16 | owner |
| 0007 | Docs/brain/AGENTS foundation, Markdown-only | accepted | 2026-10-16 | owner |
| 0008 | Standards/gates Q18 (mypy+Conventional+trunk+5 gates) | accepted | 2026-10-16 | owner |
| 0009 | Standing Rule 6 zero-skipped-warnings (Q19) | accepted | 2026-10-16 | owner |
| 0010 | Arch/data-model/threat Q20–Q22 (JSON canonical, tree schema) | accepted | 2026-10-16 | owner |
| 0011 | Roadmap Q23 (M0–M5 + A/B) | accepted | 2026-10-16 | owner |
| 0012 | Work under scriptorium/ subdir (amends 0001 layout; .github issue → Q-001) | accepted | 2026-10-16 | owner |
| 0013 | Branching: ff-only release promotion (amends 0008; main+dev identical) | accepted | 2026-10-16 | owner |
| 0014 | Proprietary license (NOTICE), public-for-CI, Tech4TIME attribution | accepted | 2026-10-16 | owner |
| 0015 | Standing Rule 7: CI-green after every push | accepted | 2026-10-16 | owner |
| 0016 | Authorship: author=alsechemist + Co-authored-by OpenCode | accepted | 2026-10-16 | owner |
| 0017 | M2 design (retro 404/squash; refresh family store; starter-kit scope; MyST HTML markers) | accepted | 2026-10-19 | owner |
| 0018 | M3 design: grimoire rename (full, incl. DB), per-user categories, auth/document/tree API semantics | accepted | 2026-10-20 | owner |
| 0019 | Login rate limiting (Q-002=B): app-level Redis fixed window, fail-closed, XFF untrusted | accepted | 2026-10-20 | owner |
| 0020 | Athenaeum layer = native hierarchy (Q-M3-9…13=A): athenaeums→categories→grimoires, delete-refusal, grimoire-level sharing, nested sidebar | accepted | 2026-10-21 | owner |
| 0021 | Slugs renamable at every layer (D0=B, amends 0018); uniform 409/422 rules; URL durability deferred to its own phase | accepted | 2026-10-21 | owner |
| 0022 | Folio + chapter vocabulary (Q-M3-14=A; amends 0010 kinds); single-membership confirmed; duplication ≠ membership | accepted | 2026-10-21 | owner |
| 0023 | Tree endpoints (D1=A delete-refusal, D2=A owner-only): chapters/folios, cycle guard, displacement reorder, nesting unrestricted (RTD) | accepted | 2026-10-21 | owner |
| 0024 | Folio documents: expected_version→409, version+history append, server-derived source cache, import→422, editor/owner saves | accepted | 2026-10-21 | owner |
| 0025 | Grimoire duplication (Q-M3-16a–e): caller-slug w/ auto-suffix, owner-only roster, head-as-v1, any owned target lib, copy-of-copy allowed | accepted | 2026-10-21 | owner |
| 0026 | M4 build design (Q-M4-P1…P4): per-Athenaeum sites, manual trigger, subprocess sandbox, keep-all + numbered builds; artifact = portable static site; design mandates (security parity, skin-open); C4 implementation note 2026-10-24 (isolated build venv, config keys, Redis ordering, docutils probe) | accepted | 2026-10-21 | owner |
| 0027 | M4-C3.5 theme: Scriptorium's own, from scratch (no builtin/third-party inheritance); full engine inheritance incl. vendored engine JS + pinned DOM contracts; brand hooks serving-phase | accepted | 2026-10-21 | owner |
| 0028 | M4-C3.5 design baseline: consult tokens accepted (fixed dark-chrome/cream scheme), Tabler inline-SVG sprite (16 icons), 11-anchor per-type callout palette (`--sd-adm-*`), custom Pygments style, first-party copy script (0027 JS clause amended), zero extensions v1, all-caps bold verdigris category labels (D15 revised) | accepted | 2026-10-22 | owner |
| 0029 | C3.5 preview-feedback rulings: link-icon anchors at every heading level (Tabler kept), search hits = scope + heading chain + matched snippet (island + same-origin extraction), code-block chrome w/ language + persistent copy, green Previous/Next pager, footer bar removed + Index under search + per-page credit (librarian display name, engine last-updated date), wide-left reading + On-This-Page rail, inspection fixture | accepted | 2026-10-22 | owner |
| 0030 | Theme typography: vendored Inter (variable, latin, Google Fonts source per owner) replaces the serif reading face — body + headings; fallback = ruled UI sans stack (RTD chain considered and dropped); OFL 1.1 vendored + NOTICE row; AA untouched | accepted | 2026-10-23 | owner |
| 0031 | Theme second-feedback batch: fluid width (no cap), RTD-style search dialog over engine index (grimoire chips, keyboard bar, Ctrl+K), icy-green inline-code/download chips, weight-700 headings, wine/plum danger + skull, first-leaf book rows + hidden staged toctrees (chapters are folios), sticky collapsible panel (persisted), scrollspy rewrite, copy→check; pathto resource-mode sidebar-link bug fixed | accepted | 2026-10-23 | owner |
| 0032 | Theme third-feedback batch: one first-party search (on-demand sectioning, phrase-first, all-word highlight, full-page takeover), centred dialog + x close, clear-only panel field, weight 800, split panel controls, scrollspy title, island contract fix, link-integrity crawl, h2 `base_level` staging fix; amends 0027/0028/0031 | accepted | 2026-10-23 | owner |
| 0033 | Standing Rule 8: Regression Integrity (No Collateral Breakage) — project-wide obligation to preserve all approved behavior, with pre-change impact review, full gates + browser checks, regression tests, and owner-approved breaking-change plans | accepted | 2026-10-24 | owner |
| 0034 | Theme fourth-feedback batch: panel placeholder only, code-language label fix with `Code` fallback, pager inside `.sd-reading-main`, and pre-paint collapsed-panel state so pager navigation never flashes the panel open; Node/theme-build/browser regressions | accepted | 2026-10-24 | owner |
| 0035 | Serving phase (A2/B3/C1/D1/E2): owner-published latest/stable pointers over immutable numbered builds, private-by-default per-Athenaeum visibility with owner/member access, FastAPI artifact serving, strict manifest-derived CSP, and bounded namespaced custom CSS; D1 public-name immutability amended by 0036; distribution remains later | accepted | 2026-10-24 | owner |
| 0036 | URL durability (A1/B1/C1/D1/E1/F1): owner-renamable public name, single `public_names` registry, permanent aliases/tombstones, owner-only rename API, `308` aliases after auth with path/query preservation and flattening, no rebuild; Option 1 URL shape retained; page-path aliases and SEO deferred | accepted | 2026-10-28 | owner |

Full records: `docs/decisions/0001-*.md` … `0036-*.md`.
Pending: none.

Last updated: 2026-10-28 / Ref: 0036 URL durability recorded
