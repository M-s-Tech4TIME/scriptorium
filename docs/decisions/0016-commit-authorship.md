# 0016 — Commit authorship: author=alsechemist + Co-authored-by OpenCode

Status: accepted | Date: 2026-10-16 | Approver: owner
Context: Bootstrap commits were authored by phantom `OpenCode <opencode@local>`,
unlinked on GitHub (owner asked why history shows only OpenCode).
Options: (A) author=alsechemist + `Co-authored-by: OpenCode` trailer (chosen);
(B) leave phantom author (rejected); (C) rewrite past history (rejected —
force-push vs `main` protection, not worth it for bootstrap commits).
Decision: (A). Repo-local identity `alsechemist` +
`239932722+alsechemist@users.noreply.github.com` (privacy); every agent commit
carries `Co-authored-by: OpenCode <opencode@local>`. Global git identity untouched.
Past commits stay as-is. Convention is standing until owner changes it.
