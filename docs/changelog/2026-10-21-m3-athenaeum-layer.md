# 2026-10-21 — M3 C3.5: Athenaeum layer as the native library hierarchy (0020)

Commits: `4b57c82` (feature) + `30dd8b4`, `b6a453d` (CI-lesson fixes) ·
Author: alsechemist (with OpenCode) · Milestone M3, tranche C3.5 · CI ×3 verified green

## What changed

Native organizational ground-up per decision **0020** (owner-approved,
all option A): the canonical hierarchy is now
`user → Athenaeums → categories → grimoires`, replacing 0018's per-user
categories (which 0020 explicitly supersedes).

- **Decision:** `docs/decisions/0020-athenaeum-layer.md` (Q-M3-9…13=A recorded
  verbatim, micro-defaults + test plan).
- **Migration `0004_athenaeums`** (append-only, 0001–0003 untouched):
  creates `athenaeums` (`UNIQUE(owner_id, slug)`), backfills one **"Default"**
  Athenaum per user, re-scopes `grimoire_categories` to `athenaeum_id`
  (`user_id` dropped, `UNIQUE(athenaeum_id, name)`), and pins every grimoire
  to its Athenaeum (`NOT NULL`, deterministic backfill: owner's library by
  `created_by`, else the oldest Default).
- **Models:** `Athenaeum`, `Grimoire.athenaeum_id`, `GrimoireCategory.athenaeum_id`.
- **Router `athenaeums.py`:** GET (own list) / POST (slug allowlist, per-owner
  dup → 409) / GET+PATCH (title rename; slug immutable — mirrors 0018
  grimoire slugs) / DELETE **refused 409 while it holds grimoires** (Q-M3-11;
  refusal writes no audit row) / GET `/{id}/sidebar` — one nested call for
  the sidebar (Q-M3-13): categories → grimoires + `uncategorized` bucket.
- **`categories.py` re-homed** to `/api/v1/athenaeums/{athenaeum_id}/categories`
  with owner-of-athenaeum access; category-of-another-athenaeum is a uniform 404.
- **`grimoires.py`:** create requires an owned `athenaeum_id` (missing → 422,
  foreign → 404); category validation scopes to **that same Athenaeum**;
  PATCH gains cross-Athenaeum move (owner of the target; `null` → 422;
  same-id no-op; audit `grimoire_moved`); list/detail rows include `athenaeum_id`.
- **`main.py`:** athenaeums router mounted.
- **Audit actions:** `athenaeum_created|patched|deleted`, `grimoire_moved`.
- **Docs:** `data-model.md` restructured around the hierarchy (+ rejected
  alternative recorded), `api.md` full restructure, `overview.md` canonical-model line,
  `test_migration.py` EXPECTED_TABLES → 11 tables.

## Tests

- `tests/test_athenaeums_api.py` (4 live-PG cases): lifecycle + per-owner
  slug uniqueness + foreign-id 404; delete-refusal → grimoire move → delete
  (audit asserted); sidebar nesting + uncategorized; grimoire scoping
  (422/404 stranger/cross-category 404) + move rejections (stranger 404,
  null target 422, happy move + audit).
- `tests/test_grimoires_api.py` rewritten for the native shape (same 5 live
  cases: categories under the athenaeum paths with insert-displacement
  reorder, create validation + creator owner membership, owner-only PATCH
  with explicit uncategorize, member flows, delete cascades).
- Offline gate stays `45 passed, 23 skipped` (live cases `needs_db`).

## CI lessons (post-push fixes, root-caused, no product-code changes)

- `4b57c82` first run: lint-type-test failed on 3 test bugs:
  - duplicate-slug probe used a *stranger* against my athenaeum —
    ownership `404` fires before the global slug check → probe as the
    owner (foreign-athenaeum probe kept as its own `404` case);
  - `test_rbac` fixture inserted `Grimoire` rows directly without
    `athenaeum_id` (NOT NULL since 0004) → fixed, then again with PK
    timing: ORM client-side column defaults (`default=uuid.uuid4`)
    apply **at first flush** — `User.id` is `None` until flushed, so
    referencing `me.id` in a same-batch `Athenaeum` insert violated
    NOT NULL → flush users first (`30dd8b4`, `b6a453d`).
- The athenaeum router, migration 0004 and all 4 new athenaeum cases
  passed on the first live run.

## Gates

ruff check/format · mypy strict (35 files) · `pytest -W error` zero warnings ·
`validate-docs.sh` · CI ×3 verified green on `b6a453d` (Rule 7).
