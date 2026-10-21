# OPEN-QUESTIONS

Last updated: 2026-10-21 / Ref: 0026 staged — serving/distribution questions parked

| ID | Question | Blocks | Asked |
|---|---|---|---|
| Q-001 | `.github/` at `scriptorium/.github/` invisible to Actions — CLOSED as moot: re-root (Q-002A) puts workflows at repo root again. No shim needed. | — | closed 2026-10-16 |
| Q-002 | Login rate limiting: RESOLVED — owner approved Option B 2026-10-20 (in-app Redis fixed window, fail-closed; decision 0019). Implement before M4. | — | closed 2026-10-20 |
| Q-M3-16a–e | Duplication sub-decisions: RESOLVED by owner 2026-10-21 — caller-supplied slug w/ optional auto-suffix; owner-only roster; head-as-v1 (no history clone); any owned target library; copy-of-copy allowed. Decision 0025. | — | closed 2026-10-21 |
| Q-SERVE-A | What gets served — latest OK build only, or owner-selected published builds (stable/latest pointers)? | serving phase | 2026-10-21 |
| Q-SERVE-B | Visibility model — public vs authenticated (private) docs; per-Athenaeum toggle? | serving phase | 2026-10-21 |
| Q-SERVE-C | Serving mechanics — FastAPI static mount vs nginx alias; reading straight from the artifacts dir? | serving phase | 2026-10-21 |
| Q-SERVE-D | URL scheme — path shape under Scriptorium's origin; interplay with the URL-durability phase (renames, aliases). | serving/world phase | 2026-10-21 |
| Q-SERVE-E | Host security — recommended headers (CSP etc.) for served sites + a manifest shipped with exported artifacts; the custom-CSS sandbox contract (0026 mandate 2). | serving phase | 2026-10-21 |
| Q-DIST-A | Credential vault design for push targets — encryption at rest, minimal scope, rotation. | distribution phase | 2026-10-21 |
| Q-DIST-B | Delivery semantics — retries/backoff, per-target status log, "re-push latest" button rules. | distribution phase | 2026-10-21 |
| Q-DIST-C | Target roster priority + mode (repo backup vs Pages hosting) — GitHub → GitLab → SFTP → FTP? | distribution phase | 2026-10-21 |
| Q-DIST-D | React shell format spec — `content.json`/`site.json` schema, routing/404 fallback, CSP posture. | distribution phase | 2026-10-21 |

Notes: Q-SERVE/Q-DIST wording was drafted by the assistant from the
owner's rulings (placement + concepts ratified 2026-10-21, see decision
0026 phase-boundary section) — the owner may edit wording before any
resolution. None of these blocks M4 or later work until their phase.

M4-C2/C3 edge cases — RESOLVED by owner 2026-10-21 (**A/A/A**, recorded
in 0026 §Edge rulings): empty Athenaeum → 422 refusal; empty grimoire →
skipped + log note; one build at a time per Athenaeum, trigger while
queued/running → 409.

**Curated default theme base — OPEN (owner question, blocked).**
The C2/C3 conf.py placeholder is `alabaster` (builtin); the curated
default theme (0026 mandate 2) still needs the owner's base choice
before C4 packaging presents the theme story. Runner ethics and all
C3 mechanics are unaffected; parked at 0026 §C3 mechanics.

No other open questions.
