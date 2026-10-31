# Roadmap — phases + gates (Q23)

Last updated: 2026-10-31 / Ref: editor/content completion tranche

- **M0 Foundation:** docs/brain/AGENTS, pins/locks, CI skeleton, nfpm skeleton, dev compose. Gate: all green.
- **M1 Core data + auth:** migrations, RBAC, audit. Gate: IDOR tests.
- **M2 Editor↔source:** TipTap v1 + RST/MyST export + round-trip suite. Gate: zero-warning suite. **Editor/content completion (2026-10-31):** React editor app (auth, dashboard, Athenaeum/build panel, tree, TipTap surface, history restore, single-file RST/MyST import), media images/GIF upload + authenticated preview + build copying, and `GET /auth/me`; frontend typecheck/build/lint/format/Vitest gates added to CI.
- **M3 Structure/TOC UX:** tree CRUD/reorder/nest + toctree/conf.py gen. Gate: UX acceptance.
- **M4 Build+serve+theme:** Celery → sandboxed Sphinx → artifacts + own
  Scriptorium theme. **C1–C4 complete/pushed 2026-10-24 (`1add6c8`, CI ×3):** build design/sandbox,
  build API, theme passes 0029–0034, packaging build venv + docutils probe.
  **Serving phase complete (0035, 2026-10-25):** owner-published
  latest/stable pointers over immutable numbered builds, private-default
  per-Athenaeum visibility, FastAPI `/a/...` serving, manifest-derived
  strict CSP, and bounded custom CSS. **URL-durability phase complete
  (0036, 2026-10-28):** owner-renamable public names, permanent aliases/
  tombstones, `308` redirects, no rebuild; Option 1 URL shape retained.
  Dedicated SEO phase (per-Athenaeum editorial controls) and distribution
  are the next phases; sequencing not yet ruled.
- **M5 Package+harden:** signed .deb/.rpm, setup/migrate, admin guide, SBOM/provenance. Gate: clean install/upgrade/uninstall ×4 distros.
- **Phase A:** versions/git-tags + picker (no v1 rewrite). **Phase B:** Yjs collab over JSON canonical.
- Open design Q (Phase A UX over time) stays owner-decided; v1 stays Git-ready.
