# Compatibility matrix (frozen set, verified 2026-10-16; auth libs added 2026-10-16)

| Component | Pinned | Latest stable seen | Support | Verified source |
|---|---|---|---|---|
| Python | 3.12.x | 3.15.0 (2026-10-09) | to Oct 2028 | python.org |
| Sphinx | 9.1.0 | 9.1.0 (2025-12-31) | 9.x current | sphinx-doc.org/PyPI |
| docutils | 0.22.4 (0.23 gated) | 0.23 (2026-05-27) | current | PyPI |
| MyST-Parser | 5.1.0 | 5.1.0 (2026-05-13) | current, needs Sphinx ≥8<10 | PyPI/changelog |
| FastAPI | 0.143.0 | 0.143.0 (2026-10-08) | rolling — pin+lock | PyPI/GitHub |
| SQLAlchemy | 2.1.4 | 2.1.4 (2026-10-07) | needs Py ≥3.11 | PyPI/GitHub |
| Alembic | 1.20.0 | 1.20.0 (2026-09-11) | needs SQLA ≥2.0 | PyPI |
| Celery | 5.6.3 | 5.6.3 (5.7b1 excluded) | mature | PyPI/changelog |
| argon2-cffi | 25.1.0 | 25.1.0 | current | PyPI |
| PyJWT | 2.15.1 | 2.15.1 | current | PyPI |
| httpx (dev) | 0.28.1 | 0.28.1 | current | PyPI |
| Dramatiq (rejected alt) | 2.2.1 | 2.2.1 (2026-09-02) | active | PyPI |
| Node (build) | 24.x LTS (24.21.0) | 24 LTS / 26 Current | 24 to ~2028 | nodejs.org |
| React | 19.3.x | 19.3.1 | 19 supported, 18 security-only | npm/react.dev |
| TypeScript | 7.0.2 (owner override 0006) | 7.0.2 (2026-08-20) | current Go rewrite | npm/GitHub |
| TipTap | 3.31.x | 3.31.4 | v3 stable | npm/tiptap.dev |
| PostgreSQL | 18.x (18.6) exclusive | 18.6 / 19 RC1 excluded | 18 to 2030-11-14 | postgresql.org |
| Redis (broker) | 7.x | 7.x | mature | — verify at M1 lock |
| nfpm | 2.x | 2.x | current | goreleaser/nfpm |

Distro check: U24.04 Py3.12/PG16(+PGDG18) OK; D12 Py3.11/PG15(+PGDG18, bundled 3.12) OK;
RHEL9 Py3.9+3.11/3.12 AppStream + PG modules/PGDG OK; Fedora PG18 OK.
Trio risk: MyST 5.x upper-bounds docutils — 0.23 gated in CI (0003).
