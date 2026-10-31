# MODULE-NOTES — frontend (V1 app)

Last updated: 2026-10-31 / Ref: editor/content completion 0038

- Purpose: React 19.3.1 + TypeScript 7.0.2 + TipTap 3.32.1 WYSIWYG,
  tree/TOC management, publishing controls, and media upload UX.
- Key files:
  - `frontend/src/main.tsx` — lazy `createBrowserRouter` routes;
  - `frontend/src/auth/AuthProvider.tsx` — memory-only access token,
    refresh-cookie bootstrap, `/auth/me`;
  - `frontend/src/api/client.ts` — typed wrapper, single-flight refresh,
    `ApiError`, authenticated media blob fetch;
  - `frontend/src/pages/` — login, dashboard, Athenaeum, grimoire editor;
  - `frontend/src/editor/EditorSurface.tsx` — TipTap starter-kit + image;
  - `frontend/src/editor/TreePanel.tsx`, `HistoryPanel.tsx`, `media.ts`.
- Toolchain: Node 26.13.0 LTS / npm 11.20.0, Vite 8.3.5, Vitest 5.0.5,
  ESLint 10.13.0, Prettier 3.9.10, Playwright 1.64.1, Testing Library
  16.3.3, axe-core 4.14.0.
- Data/form layer: React Router 8.5.1, TanStack Query 5.105.0, React Hook
  Form 7.91.0, Zod 4.6.7, Radix primitives (latest, exact pins).
- Invariants: strict + `noUncheckedIndexedAccess`; schema `tiptap@1`; no
  `any` without approval; no CDN/remote assets; WCAG AA target; canonical
  media URLs are `/_static/media/{uuid}.{ext}` and saves never send
  `blob:` URLs.
- Gates: `npm run lint`, `format:check`, `typecheck`, `test`, `build`,
  and `npm audit --audit-level=high`; CI runs all six.
- Lint caveat: typescript-eslint 8.72.1 excludes TS 7, so ESLint covers
  JS/config only; `tsc --noEmit` is the type gate.
- Tests: `src/lib/format.test.ts`, `src/editor/media.test.ts`,
  `src/api/client.test.ts`.
- Unsaved changes: `useBlocker` guards SPA route changes and
  `beforeunload` guards full-page unloads.
