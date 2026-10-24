# Roadmap — phases + gates (Q23)

Last updated: 2026-10-24 / Ref: M4-C4 implementation

- **M0 Foundation:** docs/brain/AGENTS, pins/locks, CI skeleton, nfpm skeleton, dev compose. Gate: all green.
- **M1 Core data + auth:** migrations, RBAC, audit. Gate: IDOR tests.
- **M2 Editor↔source:** TipTap v1 + RST/MyST export + round-trip suite. Gate: zero-warning suite.
- **M3 Structure/TOC UX:** tree CRUD/reorder/nest + toctree/conf.py gen. Gate: UX acceptance.
- **M4 Build+serve+theme:** Celery → sandboxed Sphinx → artifacts + own
  Scriptorium theme. **C1–C4 complete 2026-10-24:** build design/sandbox,
  build API, theme passes 0029–0034, packaging build venv + docutils probe.
  Serving phase (Q-SERVE-A…E) is next; the M4 report records gate evidence
  and remaining serving scope.
- **M5 Package+harden:** signed .deb/.rpm, setup/migrate, admin guide, SBOM/provenance. Gate: clean install/upgrade/uninstall ×4 distros.
- **Phase A:** versions/git-tags + picker (no v1 rewrite). **Phase B:** Yjs collab over JSON canonical.
- Open design Q (Phase A UX over time) stays owner-decided; v1 stays Git-ready.
