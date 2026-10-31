# Getting started (local dev)

Last updated: 2026-10-30 / Ref: stack-upgrade phase (0037)

## Prereqs (frozen versions)

- Python **3.14.10** (the package build fetches it via
  `packaging/scripts/fetch-python.sh`; local dev can use any 3.14.x).
- Node **26.13.0 LTS** + npm 11.20.0.
- PostgreSQL **18.6**.
- Redis **8.10.2** (Docker or the bundled runtime).
- nfpm 2.x, git.

## Clone + run

```bash
git clone <repo> && cd project-scriptorium/scriptorium
docker compose up -d db redis   # PG18.6 + Redis 8.10.2
cd backend
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r requirements.lock
cd ../frontend
npm ci
npm run dev
```

## Test / build / package

```bash
# backend
cd backend
pytest -W error
ruff check .
ruff format --check .
mypy --config-file pyproject.toml .
# frontend
cd ../frontend
npm run lint
npm run format:check
npm audit --audit-level=high
# package runtimes (M5)
cd ..
packaging/scripts/fetch-python.sh
packaging/scripts/build-app-venv.sh
packaging/scripts/build-venv.sh
packaging/scripts/build-redis.sh
nfpm package --config packaging/nfpm.yaml --target dist/
```

## First admin flow (M5 target, Q5/Q6)

Install `.deb`/`.rpm` → `sudo -u scriptorium scriptorium-admin setup` →
`sudo -u scriptorium scriptorium-admin migrate` → `systemctl enable --now
scriptorium-redis scriptorium-web scriptorium-worker`.
`postinst` never auto-touches the DB.
