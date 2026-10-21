# TASKS

Last updated: 2026-10-21 / M4-C3 LANDED (1e1637e, CI ×3)

## In progress (max 1–2)
- Owner question: curated default theme base (0026 mandate 2) — ask
  before C4 packaging.
- M4-C4: packaging (build venv, worker After=redis, config keys) +
  0017 docutils-0.23 probe mechanics + M4-complete report.

## Todo (M4 next — C4 + phases)
- [ ] M4-C4 packaging: isolated build venv + `SC_BUILD_PYTHON`,
      unit `scriptorium-worker` `After=redis`, `config.env` build keys
      (`CELERY_BROKER_URL`, `SC_*`); 0017 docutils-0.23 probe
      mechanics; M4-complete report + brain.
- [ ] Serving phase (resolve Q-SERVE-A…E first) → dedicated phase
- [ ] URL-durability phase after serving
- [ ] Distribution phase (Q-DIST-A…D) + React shell format — concepts
      ratified in 0026, presented before implementation

- [x] Owner ruled M4 C2/C3 edge cases A/A/A 2026-10-21 (E1 422-empty,
      E2 skip+note, E3 409-serialization) — recorded 0026 §Edge rulings
- [x] M4-C2: deterministic sourcegen + 14 offline tests (3a15b52, ×3)
- [x] M4-C3: runner + Celery + build endpoints (c6c407d → fadef93 →
      1e1637e, ×3): E1/E3 live, numbering, artifact bytes, visibility,
      failed-run crash log, migration roundtrip vs library-era rows

## Done
- [x] M4-C1: decision 0026 + migration 0006 (build_number per-athenaeum,
      athenaeum FK, grimoire_key relaxed; legacy rows untouched) — staged
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
