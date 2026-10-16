# 0006 — TypeScript 7.0.2 owner override (Q16)

Status: accepted | Date: 2026-10-16 | Approver: owner (override vs LTS/proven rule)
Context: TS 7.0.2 (Jul 2026, Go rewrite, 3mo old, rootDir/types/strict defaults changed, prog. API unstable till 7.1) fails prolonged/proven test; 6.0.x bridge recommended.
Options: (A) 6.0.x now + 7.x lane vs (B) 7.0.2 now (owner chose B).
Decision: (B) Pin exact 7.0.2 + lockfile + explicit tsconfig + VS Code TS7 extension.
Consequences: 10x build speed; churn risk accepted on owner authority.
