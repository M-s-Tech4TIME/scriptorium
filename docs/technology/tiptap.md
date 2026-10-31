# Technology — TipTap 3.32.1 (+ Vite, ESLint, Vitest)

- Versions (locked): `@tiptap/core` + `starter-kit` + `extension-image`
  **3.32.1**; Vite
  **8.3.5**, ESLint **10.13.0** (flat config), Prettier **3.9.10**,
  Vitest **5.0.5**, jsdom **30.1.3**, MSW **3.0.3**.
- Why: v3 stable headless editor; custom nodes map to Sphinx directives (M2);
  JSON canonical `tiptap@1` is Yjs-compatible for Phase B (decision 0010).
- Used: `frontend/src/editor/`; extensions allowlisted per directive (Rule 4).
  Starter-kit covers the approved text/structure set; `extension-image` adds
  the V1 image node. Images must use canonical uploaded-media URLs; the
  editor resolves them to authenticated blob URLs for display and maps
  them back before saving.
- Verified: 2026-10-31 (npm/tiptap.dev; lock resolved 2026-10-31). `npm ci`,
  ESLint, Prettier check, `tsc --noEmit`, Vitest, production build, and
  `npm audit --audit-level=high` pass.
