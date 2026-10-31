# Technology — React 19.3.1 + router/query/form stack

- Versions (locked `frontend/package-lock.json`): React + React-DOM
  **19.3.1**; React Router **8.5.1**; TanStack Query **5.105.0**;
  React Hook Form **7.91.0**; Zod **4.6.7**; `@hookform/resolvers` **6.0.2**.
  19 is the only actively supported major (18 security-only since Dec 2024).
- Why: current supported React line; TipTap 3 targets 19. React Router 8 and
  TanStack Query 5 provide the routing/data layer; RHF + Zod give typed
  editor forms and validation.
- Used: `frontend/src/` (editor + TOC UX, M2–M3).
- Verified: 2026-10-30 (npm/react.dev; lock resolved 2026-10-30). See
  `docs/technology/frontend.md` for the full support matrix and policy.
