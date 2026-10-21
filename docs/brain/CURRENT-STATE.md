# CURRENT-STATE

Last updated: 2026-10-21 / Ref: C5 green (`034db20`) — C6 parked (Rule 4)

- **Phase:** M3 nearly done — C1–C5 all green ×3 (C4 and C5 each needed
  live-path fix-ups; lessons recorded in their changelogs). Remaining:
  **C6 grimoire duplication — BLOCKED on Q-M3-16a–e** (five sub-decisions
  parked in OPEN-QUESTIONS; owner rules, then decision 0025 + router +
  tests), then the M3-complete report. Migrate head `0005foliochapter`;
  offline baseline `45 passed, 31 skipped`.
- **Owner decisions:** 0018 (grimoire rename, per-user categories, auth
  semantics) → **amended by 0020 (2026-10-21):** native hierarchy — categories
  per-Athenaeum (Q-M3-9=A), `grimoires.athenaeum_id` NOT NULL (Q-M3-10=A),
  delete refuses 409 while grimoires remain (Q-M3-11=A), sharing stays
  grimoire-level (Q-M3-12=A), nested sidebar endpoint (Q-M3-13=A).
  Micro-defaults: per-owner slug uniqueness, migration backfills "Default"
  per user, athenaeum slug immutable (mirrors 0018 grimoire slugs),
  audit `athenaeum_*` + `grimoire_moved`.
- **Done (cumulative):** Q1–Q23 + Q-M2-1/2 + Q-M3-1…8 + Q-002=B(0019) +
  Q-M3-9…13=A(0020); Rules 1–7. M0 locks; M1 green (2539391); M2 A–C; M3
  C1 `c26cd7e`, C2 `aee1872`, C2.5 `a6c17bb`, C3 `d62784e` green ×3.
- **Last commit:** `b6a453d` (docs-sync for C3.5 green) on top of `4b57c82`+
  `30dd8b4`.
- **Remote:** `git@github.com:M-s-Tech4TIME/scriptorium.git` (public).
  `dev` carries M2 + M3-in-progress; `main` stays at release point (ff-only).
- **Known/limitations (documented, not bugs):** docutils 0.22.4 inline
  markup does not nest — 0017 fail-loud matrix in
  `docs/technology/conversion.md`; RST writer rejects mark-run edge spaces,
  mark combinations, and heading level skips; MyST keeps them via HTML
  paths. Live-DB tests need PG schema at migration head `0004athenaeum`.
