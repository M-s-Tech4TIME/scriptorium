# 2026-10-20 — Grimoire rename + categories schema (M3 C1)

- Terminology: "projects" are now **grimoires** throughout Scriptorium
  (owner decision 0018, Q-M3-5=A) — DB table, model, API paths, docs.
- Migration `0003_grimoires_categories`: renames `projects` → `grimoires`
  with full coherence — columns `project_id` → `grimoire_id`
  (memberships/nodes/builds/audit_log), constraint and index renames;
  adds `grimoire_categories` (per-user name+position, UNIQUE(user_id,name))
  and `grimoires.category_id` (NULL allowed; category delete → SET NULL
  ⇢ Uncategorized, Q-M3-6/7/8=A).
- Models: `Grimoire`, `GrimoireCategory`; `Membership.grimoire_id`,
  `Node.grimoire_id`, `Build.grimoire_id`, `AuditLog.grimoire_id`.
- `require_membership(grimoire_id, …)` renamed arg; IDOR semantics
  unchanged (outsiders get uniform 404).
- `test_migration` expected tables now 10 (incl. `grimoire_categories`);
  `test_rbac` uses `Grimoire`.
- Decision record: `docs/decisions/0018-m3-design.md` (also ratifies the
  M2 carry-overs: fail-loud matrix, CI mypy `--config-file`).
