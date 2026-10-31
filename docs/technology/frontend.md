# Frontend support matrix and dependency policy

Last updated: 2026-10-31 / Ref: editor/content completion tranche

## Runtime and toolchain

| Item | Pin | Notes |
|---|---|---|
| Node | 26.13.0 LTS | Build/test only; never shipped |
| npm | 11.20.0 | Bundled with Node 26.13.0; `packageManager` pin |
| React / React DOM | 19.3.1 | Only actively supported major |
| TypeScript | 7.0.2 | Owner override 0006; `tsc --noEmit` is the type gate |
| Vite | 8.3.5 | Build/dev server |
| Vitest | 5.0.5 | Unit/component tests |
| jsdom | 30.1.3 | DOM test environment |
| MSW | 3.0.3 | Network mocks |
| Testing Library | 16.3.3 | Component tests |
| Playwright | 1.64.1 | Browser/E2E tests |
| axe-core | 4.14.0 | Accessibility checks |
| ESLint | 10.13.0 | Flat config; JS/config only until typescript-eslint supports TS 7 |
| Prettier | 3.9.10 | Format gate |

## Application libraries

| Item | Pin | Notes |
|---|---|---|
| TipTap | 3.32.1 | Headless editor; JSON canonical `tiptap@1` |
| React Router | 8.5.1 | Routing |
| TanStack Query | 5.105.0 | Server state |
| React Hook Form | 7.91.0 | Forms |
| Zod | 4.6.7 | Validation |
| `@hookform/resolvers` | 6.0.2 | RHF/Zod bridge |
| Radix primitives | latest per primitive, exact pins | Dialog, menu, tabs, tooltip, toast, popover, select, switch, checkbox, radio, accordion, alert-dialog, label, separator, slot |
| Tabler icons | 3.50.0 | MIT; public theme sprite remains 3.36.0 |
| DOMPurify | 3.4.17 | Sanitization boundary |
| date-fns | 4.4.0 | Dates |
| nanoid | 6.0.2 | IDs |
| clsx | 2.1.1 | Class composition |

## Application shell (V1)

- `src/main.tsx` — `createBrowserRouter`; authenticated routes are lazy
  chunks so the TipTap editor does not load on the login/dashboard path.
- `src/auth/AuthProvider.tsx` — access token lives in memory only; boot
  refreshes via the HttpOnly cookie, then calls `GET /auth/me`.
- `src/api/client.ts` — typed API wrapper, single-flight refresh on `401`,
  `ApiError` with FastAPI `detail` extraction, authenticated media blob
  fetch.
- `src/pages/` — login, dashboard, Athenaeum (grimoires + builds +
  publication settings), grimoire editor.
- `src/editor/EditorSurface.tsx` — TipTap 3 starter-kit + image extension;
  toolbar covers headings, marks, lists, quote, code, rule, link, image,
  undo/redo. `Ctrl/Cmd+S` saves.
- `src/editor/TreePanel.tsx` — tree CRUD; `src/editor/HistoryPanel.tsx` —
  history detail + restore; `src/editor/media.ts` — canonical media URL ↔
  blob URL mapping so the editor never sends blob URLs to the API.
- `src/pages/GrimoirePage.tsx` — document load/save with
  `expected_version`, 409 conflict reload/overwrite, single-file
  RST/MyST import, source preview, unsaved-change guard, history restore.

## Gates

`npm run lint`, `npm run format:check`, `npm run typecheck`,
`npm test`, `npm run build`, and `npm audit --audit-level=high` all run in
CI. Vitest covers slug/date helpers, media URL mapping/cleanup, and API
auth refresh/error handling.

## Browser support

| Browser | Supported |
|---|---|
| Chrome / Edge | latest 2 stable |
| Firefox | latest 2 stable |
| Safari | latest 2 stable |
| iOS Safari | 18+ |
| Android Chrome | latest stable |
| Internet Explorer | not supported |

## Security and upgrade policy

- `package-lock.json` is committed; every direct dependency is an exact pin.
- `npm audit --audit-level=high` is blocking in CI and the security workflow.
- Weekly Dependabot updates for npm, pip, GitHub Actions and Docker.
- Quarterly upgrade window; security SLA: critical 24h, high 7d, medium 30d,
  low next quarter.
- CycloneDX SBOM and license checks are release-gate requirements.
- No CDN, remote fonts, remote scripts or runtime third-party assets; the
  public theme vendors its own fonts/icons.
- TypeScript is checked by `tsc --noEmit`; ESLint currently covers
  JavaScript/config only because `typescript-eslint 8.72.1` declares
  `typescript >=4.8.4 <6.1.0`. Revisit when that peer range widens.
- Accessibility: WCAG AA is the target; axe-core is part of the test stack.
