# 2026-10-21 — 0020 athenaeum layer (C3.5): native library hierarchy

- Owner approved decision **0020** — the native ground-up hierarchy is
  `user → Athenaeums → categories → grimoires` ("Athenaeum" is the owner's
  chosen name for Library; one Athenaeum per product/company). All of
  Q-M3-9…13 = option A; micro-defaults approved with the set; adoption
  date recorded honestly in 0020 (0018's per-user categories superseded).
- C3.5 work, in owner plan order: decision record → migration
  `0004_athenaeums` (athenaeums table + `UNIQUE(owner_id, slug)`;
  per-user "Default" backfill; categories re-scoped `user_id` →
  `athenaeum_id` + `UNIQUE(athenaeum_id, name)`; grimoires pinned
  NOT NULL with deterministic owner-based backfill) → models
  (`Athenaeum`, FKs) → `routers/athenaeums.py` (list/create/get/patch/
  delete-refuse-409/`{id}/sidebar`) → `categories.py` re-homed to
  athenaeum paths → `grimoires.py` (create requires owned athenaeum,
  same-athenaeum category scoping, cross-Athenaeum PATCH move with
  `grimoire_moved` audit) → `main.py` mount → tests.
- Tests: `test_athenaeums_api.py` (4 live cases: lifecycle + per-owner
  slugs; delete-refusal → move → delete with audit counts; sidebar shape;
  move/scoping rejections 422/404) and `test_grimoires_api.py` rewritten
  for the native shape (categories under athenaeums, `_mk_lib` helper).
  `test_migration.py` EXPECTED_TABLES → 11.
- Docs: `data-model.md` (hierarchy + rejected alternative), `api.md`
  (restructured, athenaeums + re-homed categories + move semantics),
  `overview.md` canonical-model line, changelog
  `2026-10-21-m3-athenaeum-layer.md`, DECISIONS-INDEX, brain files.
- Local gates green: ruff, mypy strict 35 files, pytest `45 passed,
  23 skipped -W error`, validate-docs. CI ×3 verified green on `b6a453d`
  (Rule 7), after two test-only fix-ups:
  - dup-slug probe ran against a foreign athenaeum → 404 before the
    global slug check (probe as owner instead);
  - rbac fixture: direct-ORM `Grimoire` missing `athenaeum_id` (NOT NULL
    since 0004); and `User.id` is `None` until first flush (client-side
    column default applies at INSERT) — flush users before referencing
    their ids.
