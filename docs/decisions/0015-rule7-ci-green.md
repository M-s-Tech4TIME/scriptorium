# 0015 — Standing Rule 7: CI-green after every push (owner-ordered)

Status: accepted | Date: 2026-10-16 | Approver: owner (new non-negotiable rule)
Context: Owner found CI red after bootstrap push; earlier rules required gates to
pass but never stated the check-and-fix loop explicitly. Gap now closed.
Decision: After every commit+push, check CI status. If red: stop new work,
diagnose root cause, fix properly on the appropriate branch (`dev`; `main` only
via ff release), re-push, re-verify green. Never leave CI red, never stack new
work on red CI, never "fix" by weakening gates without owner approval (Rule 4).
First application: fixed bootstrap red CI (YAML quoting + gitleaks OSS) on `dev`,
verified green (`9714cf1`: lint-type-test, security, packaging success).
Consequences: Joins Rules 1–6; in `AGENTS.md` Definition of Done +
`docs/development/standards.md`; slows throughput but keeps `main` releasable.
