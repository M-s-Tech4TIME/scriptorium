# MODULE-NOTES — frontend (planned, M2)

Last updated: 2026-10-30 / Ref: stack-upgrade phase 0037
- Purpose: React 19.3.1 + TypeScript 7.0.2 + TipTap 3.32.1 WYSIWYG + TOC
  management UX.
- Key files: `frontend/src/{editor,components/toc,pages}/`.
- Toolchain: Node 26.13.0 LTS / npm 11.20.0, Vite 8.3.5, Vitest 5.0.5,
  ESLint 10.13.0, Prettier 3.9.10, Playwright 1.64.1, Testing Library
  16.3.3, axe-core 4.14.0.
- Data/form layer: React Router 8.5.1, TanStack Query 5.105.0, React Hook
  Form 7.91.0, Zod 4.6.7, Radix primitives (latest, exact pins).
- Invariants: strict + noUncheckedIndexedAccess; schema `tiptap@1`; no
  `any` without approval; no CDN/remote assets; WCAG AA target.
- Lint caveat: typescript-eslint 8.72.1 excludes TS 7, so ESLint covers
  JS/config only; `tsc --noEmit` is the type gate.
- Source tree is not yet created; stack/lock/support matrix are in place.
