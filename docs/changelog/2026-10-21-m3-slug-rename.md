# 2026-10-21 — M3 C3.6: slugs renamable across the library hierarchy (0021)

Commits: this tranche · Author: alsechemist (with OpenCode) · Milestone M3, tranche C3.6

## What changed

The owner ratified **0021** — every layer's URL-name is renamable:

- **Decision:** `docs/decisions/0021-slug-rename-policy.md` (D0=B ruling +
  0018 amendment; broken-URL durability explicitly deferred to its later
  dedicated phase).
- **`PATCH /athenaeums/{id}`** gains `{slug?}` (title optional now, both
  presence-checked): per-owner uniqueness → `409`; `[a-z0-9-]+` or explicit
  `null` → `422`; audit `athenaeum_patched` meta records what changed.
- **`PATCH /grimoires/{id}`** gains `{slug?}`: global slug uniqueness →
  `409` (self excluded from the collision query); regex/`null` → `422`;
  `grimoire_patched` meta records it. `grimoire_moved` remains
  Athenaeum-move-only.
- Renames are pure column updates — no schema change, no new audit
  actions, nothing slug-derived exists (broken-URL work is a later
  dedicated phase).
- **Tests:** `test_slug_rename_policy_athenaeums` (rename incl. freed-slug
  reuse, `null` → 422, collision → 409, regex → 422, foreign → 404) and
  `test_slug_rename_policy_grimoires` (same policy + global collision +
  audit). Offline now `45 passed, 25 skipped`.
- **Docs:** api.md PATCH rows, data-model slug wording, 0021 record, brain.

## Next

C3.7 — folio/chapter rename (0005 migration, decision 0022), then C4 tree.
