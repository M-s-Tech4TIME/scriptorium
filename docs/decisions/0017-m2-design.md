# 0017 — M2 design: refresh-token store + TipTap↔RST/MyST conversion

Date: 2026-10-19 · Status: **accepted** · Approver: owner · Supersedes: none

## Decisions approved by the owner (2026-10-19)
1. **M1 retro-approvals:** outsiders receive HTTP 404 (not 403) in `require_membership`
   (existence hidden — IDOR), and the 2026-10-16 `dev` squash remains canonical history.
2. **Q-M2-2 = A:** refresh-token reuse detection is **family-based**: every refresh token
   carries `fam` + `jti` claims; presenting an already-rotated/unknown token revokes the
   *entire* family (server-side state) and forces re-login.
3. **Q-M2-1 = A:** converter covers **exactly the TipTap starter-kit 3.31.4 set** —
   doc, paragraph, heading(1–6), bulletList/orderedList(+`start`)/listItem, codeBlock,
   blockquote, hardBreak, horizontalRule, text with marks bold/italic/strike/code/link/
   underline. Tables/images arrive only when the editor enables those extensions.
4. **Q-M2-3:** MyST export emits CommonMark (+ `{code-block}`-free fenced code); detail
   discretion delegated, confirmed by approval.

## Refresh-token store (approved)
New table `refresh_tokens` (migration `0002`): `id` UUID PK, `user_id` FK→users CASCADE,
`family` UUID indexed, `jti` UUID unique, `parent_jti` UUID nullable, `expires_at`,
`created_at`, `revoked_at` nullable, `revoked_reason` nullable CHECK
(`rotated|reuse|logout`). Token *material* is never stored — only identifiers/state
(Rule 2). Rotation: old row revoked (`rotated`), new row inserted, same family.
Reuse (revoked-or-unknown `jti` presented): revoke whole family → 401 everywhere.

## Converter design (informed by verified parser probes, docutils 0.22.4 / myst-parser 5.1.0)
- **Import:** RST (docutils parser) or MyST (`myst_parser.parsers.docutils_.Parser`) →
  docutils doctree → TipTap JSON (`tiptap@1`). One doctree walker serves both formats —
  myst-parser and docutils produce the same node shapes (`literal_block` language in
  `classes`, `enumerated_list` start attr, `reference` refuri/refid, `line_block`).
- **Export:** hand-rolled TipTap JSON → RST and → MyST writers (no new dependencies).
- **Verified parser facts the design relies on:**
  - docutils/myst `.. code:: python` / ``` fenced code → `literal_block` with language in
    `classes` (e.g. `['code','python']`); no-language literal blocks have no marker class.
  - MyST `~~strike~~` is **not** parsed by myst-parser 5.1.0 (remains literal text);
    inline raw HTML survives as `raw(format='html')` nodes → strike/underline round-trip
    in MyST via `<s>`/`<u>` HTML markers; `<br />` maps to hardBreak.
  - docutils custom roles (`.. role:: strike|underline`) hold **plain text only** —
    nested inline markup inside a role is not parsed. Writer order is therefore
    code > link > bold > italic > strike > underline, and a `{code+strike}` (or
    `{code+underline}`) run pair is **unrepresentable in plain RST** — the RST writer
    raises a typed `ConversionError` (fail-loud, Rule 6); the MyST writer handles it via
    HTML markers.
  - `:title-ref:` etc. unknown roles produce docutils level-3 `system_message` → import
    fails loudly (no silent data loss).
- **Aura nodes** (`system_message`, `comment`, `target`, `pending`,
  `substitution_definition`, `raw` with non-mappable content) are dropped/ignored by
  design; **unmapped content nodes raise** `ConversionError` (approved fail-loud stance).
- **Canonical forms:** round-trip canon sorts mark sets, drops empty paragraphs
  (RST cannot express them), omits `start` when 1, and omits falsy code languages.
- **M2 gate (roadmap):** the round-trip suite runs with **zero warnings** — enforced by
  `pytest -W error` in the CI backend job. Full Sphinx `-W` builds of *user* content are
  the M4 gate (sandboxed build milestone); the docs/ tree itself is validated by
  scripts/validate-docs.sh, not Sphinx.
- **mypy:** docutils/myst-parser lack typing metadata for parts of the public API used;
  per-module `ignore_missing_imports` overrides added in `backend/pyproject.toml`
  (no library code silenced at runtime — only mypy import resolution).

## Consequences
- Zero new runtime dependencies (all converters built on already-pinned libraries).
- Import of documents using constructs outside the approved set (tables, images,
  footnotes, citations, directives) fails loudly with a message naming the construct —
  deliberate data-integrity choice over silent degradation.
