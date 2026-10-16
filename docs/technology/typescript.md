# Technology — TypeScript 7.0.2 (owner override, decision 0006)

- Version (locked): 7.0.2 (2026-08-20, Go rewrite). `strict` + `noUncheckedIndexedAccess`;
  explicit `rootDir: ./src`, `types: [node, vite/client]` (7.x changed defaults).
- Why: owner chose 7.x over 6.0.x lane despite 3mo age (0006); ~10x builds.
  Risk accepted: prog. API unstable till 7.1; exact pin + lock.
- Used: `frontend/` (`tsconfig.json`, `tsc --noEmit`, VS Code TS7 extension).
- Verified: 2026-10-16 (npm/GitHub; lock resolved 2026-10-16).
