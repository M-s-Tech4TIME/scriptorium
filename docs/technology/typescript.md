# Technology — TypeScript 7.0.2 (owner override, decision 0006)

- Version (locked): **7.0.2** (2026-08-20, Go rewrite). `strict` +
  `noUncheckedIndexedAccess`; explicit `rootDir: ./src`,
  `types: [node, vite/client]` (7.x changed defaults).
- Why: owner chose 7.x over the 6.0.x lane despite its age (0006); ~10x
  builds. Risk accepted: programmatic API unstable until 7.1; exact pin +
  lock.
- Used: `frontend/` (`tsconfig.json`, `tsc --noEmit`, VS Code TS7 extension).
- Lint caveat: `typescript-eslint 8.72.1` declares
  `typescript >=4.8.4 <6.1.0`, so it cannot lint the pinned TS 7 compiler.
  ESLint therefore lints JavaScript/config only; TypeScript correctness is
  gated by `tsc --noEmit`. Revisit when typescript-eslint widens its peer
  range. This is a documented, scoped exception — not a silent suppression.
- Verified: 2026-10-30 (npm/GitHub; lock resolved 2026-10-30).
