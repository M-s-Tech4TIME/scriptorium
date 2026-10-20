# TASKS

Last updated: 2026-10-20 / M3 C1 staged with this sync

## In progress (max 1–2)
- (none — M2 complete with this commit)

## Todo (M3 next)
- [ ] C2 auth/session endpoints (login/refresh/logout + cookie plumbing)
- [ ] C3 categories + grimoires + memberships endpoints (+audit)
- [ ] C4 tree endpoints (atomic sibling reorder)
- [ ] C5 document endpoints (expected_version→409, history, import→422)
- [ ] Runner/doc pipeline (M4): gated Sphinx builds; docutils 0.23 gate
      recorded in 0017.

## Done
- [x] M0 locks + technology/*.md (requirements.lock, package-lock.json)
- [x] M1 migrations + RBAC + IDOR tests (2539391)
- [x] M2: 0017 record (ba153e9), refresh store (d5fb5cc), conversion (be1a220)
- [x] M3 C1: 0018 record + grimoire rename + categories schema (this commit)
- [x] Q1–Q23 (2026-10-16); Q-M2-1/2 (2026-10-19); Q-M3-1…8 (2026-10-20)

## Blocked
- (none)
