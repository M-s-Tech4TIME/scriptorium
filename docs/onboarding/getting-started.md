# Getting started (local dev)

Last updated: 2026-11-04 / Ref: server-move/first-run + built-in TLS (0040)

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
npm run typecheck
npm run lint
npm run format:check
npm test
npm run build
npm audit --audit-level=high
# docs/packaging contract
cd ..
bash scripts/validate-docs.sh
pytest backend/tests/test_packaging.py -W error
# package runtimes (M5)
packaging/scripts/fetch-python.sh
packaging/scripts/build-app-venv.sh
packaging/scripts/build-venv.sh
packaging/scripts/build-redis.sh
nfpm package --config packaging/nfpm.yaml --target dist/
```

## First-run flow (current, 0040)

On a packaged host:

```bash
# 1. Configure /etc/scriptorium/config.env (0600) with DATABASE_URL,
#    a fresh SECRET_KEY, cookie security, Redis, SC_* roots, and TLS keys.
# 2. Issue TLS before enabling the web unit:
sudo scriptorium-admin tls generate --hostname docs.example.com
#    or: sudo scriptorium-admin tls import --cert fullchain.pem --key privkey.pem
sudo scriptorium-admin tls verify
# 3. Read-only preflight, then schema and first account:
sudo scriptorium-admin setup
sudo scriptorium-admin migrate
sudo scriptorium-admin user create --email owner@example.com --display "Owner"
# 4. Start the stack (HTTPS 443 + HTTP→HTTPS 308 on 80):
sudo systemctl enable --now scriptorium-redis scriptorium-redirect \
  scriptorium-web scriptorium-worker scriptorium-tls-renew.timer
```

There is no open registration and no plaintext application listener.
`postinst` never migrates or generates certificates. For local development
without packaging, set the same variables in your shell and run the CLI
from the backend venv; the TLS commands accept a non-default
`SC_TLS_ROOT` so they can be exercised unprivileged. See
`docs/operations/install.md`, `docs/operations/tls.md`, and
`docs/operations/server-move.md`.
