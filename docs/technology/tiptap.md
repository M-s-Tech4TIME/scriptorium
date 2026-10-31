# Technology — TipTap 3.32.1 (+ Vite, ESLint, Vitest)

- Versions (locked): `@tiptap/core` + `starter-kit` **3.32.1**; Vite
  **8.3.5**, ESLint **10.13.0** (flat config), Prettier **3.9.10**,
  Vitest **5.0.5**, jsdom **30.1.3**, MSW **3.0.3**.
- Why: v3 stable headless editor; custom nodes map to Sphinx directives (M2);
  JSON canonical `tiptap@1` is Yjs-compatible for Phase B (decision 0010).
- Used: `frontend/src/editor/`; extensions allowlisted per directive (Rule 4).
- Verified: 2026-10-30 (npm/tiptap.dev; lock resolved 2026-10-30). `npm ci`,
  ESLint, Prettier check and `npm audit --audit-level=high` pass.
