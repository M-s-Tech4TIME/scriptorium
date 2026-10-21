# TASKS

Last updated: 2026-10-21 / M3 COMPLETE (all tranches green ×3)

## In progress (max 1–2)
- (none — M3 closed; awaiting M4 start after owner's read of the report)

## Todo (M4 next)
- [ ] M4 builds: gated Sphinx builds; docutils 0.23 gate per 0017;
      packaging `After=redis` systemd note; sources jail keyed by
      grimoire id (vetoable micro-default)
- [ ] Dedicated phase: serving as a website (granularity/visibility/
      mechanics/URL-scheme decisions to present first)
- [ ] Dedicated phase: URL durability after renames (aliases/redirects,
      immutable build identity)
- [ ] Runner/doc pipeline (M4): gated Sphinx builds; docutils 0.23 gate
      recorded in 0017; packaging `After=redis` systemd note.
- [ ] Later dedicated phases: serving-as-website; URL durability
      (aliases/redirects + immutable build identity) after renames.

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
- [x] M3 C3.6: renamable slugs everywhere (0021; 9fe1280 green ×3)
- [x] M3 C3.7: folio/chapter vocabulary + migration 0005 (0022; ab688dc green ×3)
- [x] M3 C4: tree endpoints, D1/D2 rulings (0023; 3fbe4f8 + fix-ups, green ×3)
- [x] M3 C5: folio documents, concurrency/import/history (0024; green ×3)
- [x] Owner ruled Q-M3-16a–e 2026-10-21 (duplication design)
- [x] M3 C6: grimoire duplication (0025) — staged with this sync
- [x] M3 COMPLETE 2026-10-21: C1–C6 green ×3; duplication fix-ups landed
      (owner membership + copy's own v1 history trace); Q-M3-16a–e closed
- [x] Owner rulings 2026-10-21: D0=B renamable slugs (0021), grimoire-slug
      0018-amendment, single section membership confirmed, chapters (0022),
      duplication phase (Q-M3-16 later), D1=A/D2=A tree semantics
- [x] Q1–Q23 (2026-10-16); Q-M2-1/2 (2026-10-19); Q-M3-1…8 + Q-002 (2026-10-20);
      Q-M3-9…13 (2026-10-21)

## Blocked
- (none)
