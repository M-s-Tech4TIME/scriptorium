# Getting started (local dev, M0)

Last updated: 2026-10-16 / Ref: uncommitted

## Prereqs (frozen versions)
Python 3.12.x, Node 24 LTS, PostgreSQL 18, Redis 7+, nfpm 2.x, git.

## Clone + run (M0 skeleton → M1)
```bash
git clone <repo> && cd project-scriptorium
docker compose up -d db redis   # PG18 + Redis, see docker-compose.yml (M0)
cd backend && python3.12 -m venv .venv && source .venv/bin/activate
pip install -e .[dev]           # pins in backend/pyproject.toml (M0)
cd ../frontend && npm ci && npm run dev
```

## Test / build / package
```bash
# backend (M1+)
pytest -W error && ruff check . && mypy --strict .
# frontend (M2+)
npm run lint && npm run typecheck && npm test
# packages (M5, skeleton M0)
nfpm package --config packaging/nfpm.yaml --target dist/
```

## First admin flow (M5 target, Q5/Q6)
Install `.deb`/`.rpm` → `sudo -u scriptorium scriptorium-admin setup` →
`sudo -u scriptorium scriptorium-admin migrate` → `systemctl enable --now scriptorium-web scriptorium-worker`.
`postinst` never auto-touches the DB.
