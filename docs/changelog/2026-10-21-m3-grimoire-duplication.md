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

## CI lessons (post-push fix-ups `2c4a6d4`/`f3e7bc1`)

- The copy endpoint created no `Membership` row: every copy was an
  unreachable orphan even to its own duplicator (uniform 404) — caught
  in CI by the copy-of-copy case. Fix: mirror `create_grimoire`, the
  duplicator becomes the sole owner (ruling b).
- The copy's own v1 save must leave a history trace (the C5 invariant
  "every version leaves a trace"); the source's v1..vN provenance stays
  uncloned. Fix: one new `document_history` row per copied document.

## Gates

ruff check/format · mypy strict (41 files) · `pytest -W error` zero
warnings · `validate-docs.sh` · CI ×3 verified green on `f3e7bc1`
(Rule 7).

## Next

**M3 complete (C1–C6, every tranche green ×3).** Next: M4 builds
(gated Sphinx per 0017; packaging `After=redis` note) → dedicated
serving phase → dedicated URL-durability phase.
