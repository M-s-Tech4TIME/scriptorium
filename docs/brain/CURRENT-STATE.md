# CURRENT-STATE

Last updated: 2026-10-21 / Ref: M4-C3 LANDED (1e1637e, CI ×3)

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
  **Next: M4-C4** (build venv + packaging config, worker `After=redis`,
  0017 docutils-0.23 probe mechanics, M4-complete report) — **after the
  owner answers the curated-theme-base question** (parked; mandate 2)
  → serving phase (Q-SERVE-A…E) → URL durability → Distribution
  (Q-DIST-A…D).
- **Owner decisions:** 0018 (grimoire rename, per-user categories, auth
  semantics) → **amended by 0020 (2026-10-21):** native hierarchy — categories
  per-Athenaeum (Q-M3-9=A), `grimoires.athenaeum_id` NOT NULL (Q-M3-10=A),
  delete refuses 409 while grimoires remain (Q-M3-11=A), sharing stays
  grimoire-level (Q-M3-12=A), nested sidebar endpoint (Q-M3-13=A).
  Micro-defaults: per-owner slug uniqueness, migration backfills "Default"
  per user, athenaeum slug immutable (mirrors 0018 grimoire slugs),
  audit `athenaeum_*` + `grimoire_moved`.
- **Done (cumulative):** Q1–Q23 + Q-M2-1/2 + Q-M3-1…8 + Q-002=B(0019) +
  Q-M3-9…13=A(0020) + Q-M3-16a–e=A(0025) + Q-M4-P1…P4 + E1–E3(0026);
  Rules 1–7. M0 locks; M1 green (2539391); M2 A–C green; M3 C1–C6 green
  ×3; M4 C1 `2aed3ef` + C2 `3a15b52` + C3 `1e1637e` green ×3.
- **Last commit:** `1e1637e` (m4-c3 roundtrip fixes, green ×3) atop
  `fadef93` (suite secret fix) + `c6c407d` (m4-c3 feature tranche).
- **Remote:** `git@github.com:M-s-Tech4TIME/scriptorium.git` (public).
  `dev` carries M3 complete + M4 in progress; `main` stays at release
  point (ff-only).
- **Known/limitations (documented, not bugs):** docutils 0.22.4 inline
  markup does not nest — 0017 fail-loud matrix in
  `docs/technology/conversion.md`; RST writer rejects mark-run edge spaces,
  mark combinations, and heading level skips; MyST keeps them via HTML
  paths. Live-DB tests migrate to the current head (`0006buildsite`).
