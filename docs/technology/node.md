# Technology — Node 26.13.0 LTS (build-time only)

- Version: **26.13.0 LTS** with bundled npm 11.20.0. Node 26 entered LTS in
  October 2026; the line is supported into 2029.
- Why: the current LTS line, required by Vite 8 / Vitest 5 / ESLint 10 and
  the approved frontend stack. Node is never shipped in `.deb`/`.rpm`; it is
  a build-host and CI tool only.
- Used: `frontend/` build, tests, lint and format. `frontend/package.json`
  pins `engines.node` to `26.x` and `packageManager` to `npm@11.20.0`.
- CI: `.github/workflows/lint-type-test.yml` and `security.yml` pin
  `actions/setup-node@v7` with `node-version: "26.13.0"` and npm cache.
- Verification: 2026-10-30 — Node v26.13.0 / npm 11.20.0; `npm ci`,
  `npm run lint`, `npm run format:check` and `npm audit --audit-level=high`
  pass (0 vulnerabilities).
