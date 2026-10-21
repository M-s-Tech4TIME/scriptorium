# CURRENT-STATE

Last updated: 2026-10-21 / Ref: M3 COMPLETE — C1–C6 all green ×3

- **Phase:** **M3 done.** Tranches: C1 0018 design/rename (`c26cd7e`),
  C2 auth/sessions (`aee1872`), C2.5 login rate limiting 0019
  (`a6c17bb`), C3 categories/grimoires/members (`d62784e`), C3.5
  athenaeum layer 0020 (`4b57c82`+fixes), C3.6 renamable slugs 0021
  (`9fe1280`), C3.7 folio/chapter 0022 (`ab688dc`), C4 tree endpoints
  0023 (`3fbe4f8`+fix-ups), C5 folio documents 0024 (`5d8d08f`+fix-ups),
  C6 duplication 0025 (`5b5dee1`+fix-ups). Migrate head
  `0005foliochapter`; offline baseline `45 passed, 33 skipped`; 12 live
  API test cases green in CI. **Next: M4 builds** (gated Sphinx; 0017
  docutils gate; packaging `After=redis` note) → dedicated serving
  phase → dedicated URL-durability phase.
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
