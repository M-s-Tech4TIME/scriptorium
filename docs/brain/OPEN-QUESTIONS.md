# OPEN-QUESTIONS

Last updated: 2026-10-21 / Ref: C5 green (034db20); Q-M3-16 sub-decisions parked for C6

| ID | Question | Blocks | Asked |
|---|---|---|---|
| Q-001 | `.github/` at `scriptorium/.github/` invisible to Actions — CLOSED as moot: re-root (Q-002A) puts workflows at repo root again. No shim needed. | — | closed 2026-10-16 |
| Q-002 | Login rate limiting: RESOLVED — owner approved Option B 2026-10-20 (in-app Redis fixed window, fail-closed; decision 0019). Implement before M4. | — | closed 2026-10-20 |
| Q-M3-16a | Duplication slug source: **caller-supplied `slug`** in the copy body (409 on bump) vs auto-suffix (`-copy-2`) vs both (default auto, override allowed). | C6 | 2026-10-21 |
| Q-M3-16b | Duplication scope of members: **owner only** (copy owned by duplicator; fresh roster) vs full member-list clone incl. roles. | C6 | 2026-10-21 |
| Q-M3-16c | Document history in the copy: **current version only** (copy starts at v1 with the head content) vs full history clone (v1..vN reproduced). | C6 | 2026-10-21 |
| Q-M3-16d | Cross-Athenaeum copies: **caller must own the target Athenaeum too** (copy body takes optional `athenaeum_id`) vs always same-Athenaeum. | C6 | 2026-10-21 |
| Q-M3-16e | Copy-of-copy: **allowed** (chain of independent deep copies; no lineage tracking in M3) vs refuse copying a copy. | C6 | 2026-10-21 |

Q-M3-16 rationale (single-section ruling, 0022): "same book on two
shelves" is served by independent editable copies, not shared membership.
All five sub-decisions have safe defaults drafted in the C6 plan; owner
rules before the router is authored.
