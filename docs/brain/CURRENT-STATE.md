# CURRENT-STATE

Last updated: 2026-10-20 / Ref: be1a220 (M2 conversion green) + M3 C1 staged

- **Phase:** M3 underway. C1 green (c26cd7e); C2 green (aee1872). C2.5
  staged: decision 0019 login rate limiter (Q-002=B, Redis fixed window,
  fail-closed). C3–C5 queued (grimoire/category/tree/document endpoints).
- **Owner decisions:** 0018 accepted 2026-10-20 — grimoire terminology
  (full rename incl. DB), per-user categories (delete → Uncategorized,
  NULL allowed), login/refresh/logout only + CLI seeds, expected_version→409,
  server-derived source cache, atomic sibling reorder. M2 carry-overs
  (fail-loud matrix; CI mypy --config-file) ratified.
- **Done (cumulative):** Q1–Q23 + Q-M2-1/Q-M2-2 + Q-M3-1…8 + Q-002=B(0019);
  Rules 1–7. M0 locks/tech docs; M1 schema+auth green (2539391); M2 A-C
  `ba153e9`/`d5fb5cc`/`be1a220`; M3 C1 `c26cd7e`, C2 `aee1872` green ×3.
  C2.5 staged (login limiter).
- **Last commit:** `aee1872` (C2 auth endpoints); C2.5 commit adds on top.
- **Remote:** `git@github.com:M-s-Tech4TIME/scriptorium.git` (public).
  `dev` carries M2 + M3-in-progress; `main` stays at release point (ff-only).
- **Known/limitations (documented, not bugs):** docutils 0.22.4 inline
  markup does not nest — 0017 fail-loud matrix in
  `docs/technology/conversion.md`; RST writer rejects mark-run edge spaces,
  mark combinations, and heading level skips; MyST keeps them via HTML
  paths. Live-DB tests need PG schema at migration head `0003`.
