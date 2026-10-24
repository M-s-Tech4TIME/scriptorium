# TASKS

Last updated: 2026-10-24 / 2680738 0034 pushed, CI ×3; M4-C4 complete (commit/push next)

## In progress (max 1–2)
- M4-C3.5 complete: 0034 pushed as `2680738` (panel placeholder only →
  "Search"; code-language outer-wrapper fix + "Code" fallback; pager
  inside `.sd-reading-main`; pre-paint collapsed panel marker so pager
  navigation never flashes; Node/theme-build regression tests). Preview
  #6 approved; preview #7 browser-verified; CI green ×3.
- M4-C4 complete: isolated build venv + 27-pin engine lock, config
  example/queue keys, both units `Requires=redis`/`After=redis`,
  postinst artifacts/config seed/build-venv check, manual docutils-0.23
  probe (58 passed; pin stays 0.22.4), M4 report, packaging tests
  (suite 87 passed / 36 skipped). Commit + CI ×3 next.

## Todo (M4 next — phases)
- [x] M4-C3.5 baseline: 0029 + 0030 + 0031 + 0032 committed/pushed as
      `b15446f`, CI green ×3 (lint-type-test, security, packaging).
- [x] Commit Standing Rule 8 (0033) — approved wording, docs/governance.
- [x] Implement 0034 fixes + regression tests + preview #6.
- [x] Fix collapsed-panel flash on pager navigation (pre-paint marker) +
      preview #7 browser verification.
- [x] 0034 accepted + committed (includes Rule 8).
- [x] Push `dev` with Rule 8 + 0034 → CI green ×3 (`2680738`).
- [x] M4-C4 packaging: isolated build venv + `SC_BUILD_PYTHON`,
      both units `Requires=redis`/`After=redis`, `config.env` build keys
      (`CELERY_BROKER_URL`, `SC_*`); 0017 docutils-0.23 probe
      mechanics; M4 report + brain.
- [ ] Commit + push M4-C4 → CI green ×3.
- [ ] Serving phase (resolve Q-SERVE-A…E first) → dedicated phase
      (brand injection + custom-CSS hooks land here, 0027)
- [ ] URL-durability phase after serving
- [ ] Distribution phase (Q-DIST-A…D) + React shell format — concepts
      ratified in 0026, presented before implementation

- [x] M4-C3.5 code tranche: theme package + sourcegen + runner +
      loader (75/36 before feedback pass) + offline-but-real
      regression + AA contrast tests — committed in the `b15446f` stack
- [x] 0032 third feedback batch (2026-10-23/24): unified first-party
      search (phrase-first/all-word/full-page), dialog centring + x,
      clear-only field, weight 800, `#D8E7DD` inline, split toggles,
      scrollspy title, island contract, link crawl, h2 `base_level`
      fix — committed/pushed in `b15446f`; suite 80/36 at that point;
      preview #5 approved
- [x] M4-C3.5 preview #1 owner review + seven rulings (decision 0029,
      2026-10-22): all approved; Tabler kept ("Tabler it is"); credit
      holder = librarian display name; date = engine last-updated
- [x] Owner ruled the theme 2026-10-21 (decision 0027): Scriptorium's
      own from-scratch theme, full engine inheritance, engine-JS
      vendoring + pinned DOM contracts — record tranche committed
      (OPEN-QUESTIONS Q-C3.5-A resolved; brief delivered for the
      external design consult)
- [x] Design consult received 2026-10-21/22; owner approved the full
      design-baseline sheet 2026-10-22 (decision 0028): Tabler inline
      sprite, custom Pygments style, first-party copy script (0027 JS
      clause amended), zero extensions v1, fixed scheme, no logo v1;
      exceptions ruled: 11-anchor per-type callout palette (blue/violet,
      body ink uniform) + all-caps bold verdigris category labels —
      record tranche committed
- [x] Owner ruled M4 C2/C3 edge cases A/A/A 2026-10-21 (E1 422-empty,
      E2 skip+note, E3 409-serialization) — recorded 0026 §Edge rulings
- [x] Owner ruled typography 2026-10-23 (decision 0030): vendored
      Inter (Option B, sans "Notion look", Google Fonts source),
      fallback = ruled UI sans stack; RTD chain considered + dropped —
      record tranche committed with this sync
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
