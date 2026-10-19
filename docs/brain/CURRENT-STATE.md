# CURRENT-STATE

Last updated: 2026-10-20 / Ref: built on d5fb5cc (M2 conversion commit lands this state)

- **Phase:** M2 conversion layer COMPLETE in this commit; M3 (endpoints + RBAC
  wiring into routers) next.
- **Done (cumulative):** Q1–Q23 + Q-M2-1/Q-M2-2 approvals; Rules 1–7.
  M0 locks/tech docs; M1 schema+auth green (2539391, squashed M1 on `dev`,
  `main` frozen at `03f9466`); M2 commit A `ba153e9` (decision 0017 record,
  CI green ×3); M2 commit B `d5fb5cc` (refresh-token store, family-based
  reuse detection, CI green ×3 incl. live PG18 rotation/reuse tests);
  M2 commit C in this push (TipTap ↔ RST/MyST converters + tests).
- **In progress:** none — commit C fully shipped with docs + green local
  gates; verify CI after push.
- **Last commit:** D5FB5CC predecessors on `dev`; this commit = `feat: &&
  TipTap↔RST/MyST conversion (0017)`.
- **Remote:** `git@github.com:M-s-Tech4TIME/scriptorium.git` (public).
  `dev` carries M2; `main` stays at release point (ff-only).
- **Working branch:** `dev`.
- **Known/limitations (documented, not bugs):** docutils 0.22.4 inline
  markup does not nest — 0017 fail-loud matrix in
  `docs/technology/conversion.md`; RST writer rejects mark-run edge spaces,
  mark combinations, and heading level skips; MyST keeps them via HTML
  paths. Live-DB tests need PG schema at migration head `0002`.
