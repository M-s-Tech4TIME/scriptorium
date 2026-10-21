# CURRENT-STATE

Last updated: 2026-10-22 / Ref: 0028 recorded (design baseline) — C3.5 code next

- **Phase:** **M4-C3 landed.** M4-C1 (`2aed3ef`): decision 0026
  (per-Athenaeum site P1, manual trigger P2, subprocess sandbox P3,
  keep-all versions P4; reconciliation: staging keyed by grimoire id
  inside each build, artifact keyed by Athenaeum; design mandates:
  artifact security parity + structure-locked/skin-open) + migration
  0006 (`builds.build_number` per-Athenaeum counter, `athenaeum_id` FK,
  `grimoire_id` relaxed nullable, `ck_builds_site`,
  `uq_builds_athenaeum_number`). Edge rulings owner A/A/A (`7d14f3a`,
  0026 §Edge rulings): E1 empty athenaeum → 422; E2 empty book → skip +
  note; E3 one build per Athenaeum (409 while queued/running, C3
  enforces). M4-C2 (`3a15b52`, CI ×3): `app/sphinx/sourcegen.py` —
  pure deterministic staging: per-book dirs, `toctree` masters (RST,
  always), MyST-conditional `conf.py`, bodies direct from canonical
  TipTap, fail-loud `StagingError`; disclosed micro-defaults: `index-p`
  leaf mangle, toctree-title `«»` sanitize, `alabaster` interim theme.
  M4-C3 (`c6c407d` + `fadef93` + `1e1637e`, CI ×3): 
  `app/sphinx/runner.py` sandbox (whitelist env, RLIMIT cpu/as/fsize/
  core, 900 s, `sphinx -W -b html`), `app/sphinx/execute.py` shared
  executor (fresh engine/orderly disposal; queued→running→ok|failed),
  `app/worker/` celery (queue `scriptorium`, `CELERY_BROKER_URL`
  fail-loud), `app/routers/builds.py` POST owner-only (E1 422, E3 409,
  advisory-locked `max+1`) + GET member-visible; CI live suites prove
  E1/E3/numbering/artifact/failed-log + migration roundtrip vs
  library-era rows. **CI-discovered staging rulings** in 0026 (absolute
  `</docname>` refs, generated top sections, MyST fenced toctree,
  downgrade mirror, save-path exporter guarantee).
  Q-SERVE-A…E + Q-DIST-A…D parked. Migrate head `0006buildsite`;
  offline baseline **`66 passed, 36 skipped`** (C2 added 14 cases, C3
  +10: 7 offline + 3 live); live cases exercise the real sandbox.
  M3 was C1–C6 all green ×3 (typical refs: C6 `5b5dee1`, close-out
  `5f97463`).
  **Decision 0027 recorded (2026-10-21):** the theme is Scriptorium's
  **own, from scratch** — no builtin/third-party template inheritance,
  `theme.conf` no parent — while the Sphinx **engine** is fully
  inherited/utilized incl. engine-JS vendoring
  (`searchtools/doctools/sphinx_highlight/language_data`) at build time
  and DOM contracts pinned to it. Third-party candidates
  (furo/rtd/alabaster-as-final) presented and rejected. **Decision 0028
  recorded (2026-10-22):** the design baseline is implementation-ready —
  consult tokens accepted (fixed dark-forest chrome + cream paper,
  `[data-theme]` reserved), Tabler inline-SVG sprite (16 icons), custom
  Pygments `Style`, **first-party copy script** (0027 JS clause
  amended: engine assets + one disclosed first-party `scriptorium.js`),
  zero asset-injecting extensions v1, 11-anchor per-type callout
  palette (`--sd-adm-<type>-{rule,bg,ink}`, body ink uniform
  `--sd-page-ink`), all-caps bold verdigris category labels (D15
  owner-revision), WCAG AA pair list (test-pinned in C3.5), exact
  engine-JS vendoring mechanics verified (3 vendored + `language_data.js`
  builder-emitted) and the search DOM contract pinned off the vendored
  `searchtools.js`. **Next: M4-C3.5 code tranche, then M4-C4** (build
  venv + packaging config, worker `After=redis`, 0017 docutils-0.23
  probe mechanics, M4-complete report) → serving phase (Q-SERVE-A…E) →
  URL durability → Distribution (Q-DIST-A…D).
- **Owner decisions:** 0018 (grimoire rename, per-user categories, auth
  semantics) → **amended by 0020 (2026-10-21):** native hierarchy — categories
  per-Athenaeum (Q-M3-9=A), `grimoires.athenaeum_id` NOT NULL (Q-M3-10=A),
  delete refuses 409 while grimoires remain (Q-M3-11=A), sharing stays
  grimoire-level (Q-M3-12=A), nested sidebar endpoint (Q-M3-13=A).
  Micro-defaults: per-owner slug uniqueness, migration backfills "Default"
  per user, athenaeum slug immutable (mirrors 0018 grimoire slugs),
  audit `athenaeum_*` + `grimoire_moved`. **0027 (2026-10-21):** own
  from-scratch theme + full engine inheritance
  (education-before-ruling; plan ratified before implementation).
  **0028 (2026-10-22):** theme design baseline — ①A icons, ②A Pygments
  style, ③B first-party copy script (0027 JS clause amended), ⑤ zero
  extensions v1, ⑥1 fixed scheme, ⑥2 no logo v1, ⑥3 icon breadth;
  exceptions: 11-anchor per-type callout palette (blue/violet added,
  uniform body ink), all-caps bold verdigris category labels (D15
  revision). All on the consult/gap-inventory basis.
- **Done (cumulative):** Q1–Q23 + Q-M2-1/2 + Q-M3-1…8 + Q-002=B(0019) +
  Q-M3-9…13=A(0020) + Q-M3-16a–e=A(0025) + Q-M4-P1…P4 + E1–E3(0026) +
  theme ruling(0027) + design baseline(0028);
  Rules 1–7. M0 locks; M1 green (2539391); M2 A–C green; M3 C1–C6 green
  ×3; M4 C1 `2aed3ef` + C2 `3a15b52` + C3 `1e1637e` green ×3; 0027
  record tranche staged.
- **Last commit:** `52a2124` (0027 theme-ruling record, docs-only,
  green ×3) atop `7e61646` (brain sync) + `1e1637e` (m4-c3 fixes).
  **0028 record tranche staged on top** (docs-only, next commit).
- **Remote:** `git@github.com:M-s-Tech4TIME/scriptorium.git` (public).
  `dev` carries M3 complete + M4 in progress; `main` stays at release
  point (ff-only).
- **Known/limitations (documented, not bugs):** docutils 0.22.4 inline
  markup does not nest — 0017 fail-loud matrix in
  `docs/technology/conversion.md`; RST writer rejects mark-run edge spaces,
  mark combinations, and heading level skips; MyST keeps them via HTML
  paths. Live-DB tests migrate to the current head (`0006buildsite`).
