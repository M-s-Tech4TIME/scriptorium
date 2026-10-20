# TASKS

Last updated: 2026-10-21 / M3 C3.5 staged with this sync

## In progress (max 1–2)
- (none)

## Todo (M3 next)
- [ ] C4 tree endpoints: GET `/grimoires/{id}/tree`, node create/move/rename/delete —
      atomic sibling reorder (Q-M3-4=A), slugs `[a-z0-9-]+`, per-sibling-set uniqueness
- [ ] C5 document endpoints (expected_version→409, history append, import→422)
- [ ] M3-complete report after C5 green
- [ ] Runner/doc pipeline (M4): gated Sphinx builds; docutils 0.23 gate
      recorded in 0017; packaging `After=redis` systemd note.

## Done
- [x] M0 locks + technology/*.md (requirements.lock, package-lock.json)
- [x] M1 migrations + RBAC + IDOR tests (2539391)
- [x] M2: 0017 record (ba153e9), refresh store (d5fb5cc), conversion (be1a220)
- [x] M3 C1: 0018 record + grimoire rename + categories schema (c26cd7e)
- [x] M3 C2: auth/session endpoints + live API tests (aee1872)
- [x] M3 C2.5: decision 0019 + login rate limiter (a6c17bb, green ×3)
- [x] M3 C3: categories/grimoires/members endpoints + audit (d62784e)
- [x] Owner call: 0020 athenaeum layer (Q-M3-9…13=A) approved 2026-10-21
- [x] M3 C3.5: migration 0004 + athenaeum router + re-homing + move + tests
      (4b57c82 + CI fixes 30dd8b4/b6a453d — green ×3)
- [x] Q1–Q23 (2026-10-16); Q-M2-1/2 (2026-10-19); Q-M3-1…8 + Q-002 (2026-10-20);
      Q-M3-9…13 (2026-10-21)

## Blocked
- (none)
