# CURRENT-STATE

Last updated: 2026-10-16 / Ref: 2539391 (M1 auth squashed, CI green, on dev)

- **Phase:** M0 COMPLETE; M1 schema+auth DONE (RBAC wiring into routers comes with M3 endpoints).
- **Done:** Q1–Q23 + Rules 1–7. Auth libs A/A/A. Gitleaks false-positive purged (dev squash, main untouched).
- **In progress:** Awaiting owner retro-approval: outsider-404 + refresh-store parked (M2).
- **Done:** Q1–Q23 + Rules 1–7 (0015). Repo live `M-s-Tech4TIME/scriptorium` (public, proprietary).
  Bootstrap red CI fixed on `dev` — green since `9714cf1`.
- **In progress:** M1 plan proposal (migrations + RBAC design — Rule 4 approval before code).
- **Broken/known:** Nothing runnable yet (skeletons only). No backend/frontend code yet.
- **Last commit:** `d21dbc8` M0 locks (on `dev`; `main` stays at `03f9466` release point).
- **Remote:** `git@github.com:M-s-Tech4TIME/scriptorium.git` (public).
  `main` = `dev` = `03f9466` at bootstrap push. `main` protection: linear history on,
  force push off, deletions off (ff-only releases via CLI).
- **Working branch:** `dev` (all new work here; `main` advances only at releases).
