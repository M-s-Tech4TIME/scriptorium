# 2026-10-21 — M3 C6: grimoire duplication (0025)

Commits: this tranche · Author: alsechemist (with OpenCode) · Milestone M3, tranche C6

## What changed

The owner ruled all five parked sub-decisions (Q-M3-16a–e) and the deep
copy is live as `POST /api/v1/grimoires/{grimoire_id}/duplicate` in
`routers/grimoires.py`, recorded as decision **0025**:

- **a — slug:** caller-supplied (regex `422`, global collision `409`) or
  auto-derived when omitted (`source-slug-copy`, then `-copy-2`, …,
  attempt cap 100 → `409`).
- **b — members:** fresh roster; the duplicator is the copy's sole owner
  (copies start private — sharing is a deliberate act).
- **c — history:** each folio document copied at its **head content as
  v1** (cached source kept); `document_history` is not cloned — the
  original's provenance stays its own.
- **d — libraries:** optional `athenaeum_id` (default = source's);
  foreign target → `404`, mirroring the ratified move rule.
- **e — copy-of-copy:** allowed, no lineage tracking in M3.
- Deep copy in one transaction: grimoire (source_format/theme kept,
  title defaults to `"<title> (copy)"`; same-library copies inherit the
  source's category, cross-library land Uncategorized), nodes copied
  parent-first under a fresh id map with explicit ids (client-side
  column defaults land at flush — b6a453d lesson), documents per
  `node_id IN (…)`; a source-tree cycle (API-impossible) would abort
  with `409` rather than silently drop nodes. Source stays untouched.
- **Role:** owner-only on the source (disclosed micro-default per
  D2=A); audit `grimoire_duplicated`.
- **Docs:** 0025 record, api.md duplicate row + audit footer, changelog,
  brain (OPEN-QUESTIONS closed, DECISIONS-INDEX).

## Tests

`tests/test_duplicate_api.py` (2 live-PG cases): deep-copy fidelity
(tree shapes equal with fresh ids, document head as v1, history [1],
fresh owner roster, source untouched, themed/category fields) and the
rule set (auto-suffix derivation ×2, explicit collision 409, regex 422,
cross-library + category reset, foreign target/source 404, editor 403,
copy-of-copy 201, audit). Offline `45 passed, 33 skipped`.

## Next

M3 complete — M4 builds (gated Sphinx builds; docutils 0.23 gate per
0017; packaging `After=redis` note) → dedicated serving phase →
dedicated URL-durability phase.
