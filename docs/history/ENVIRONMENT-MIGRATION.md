# Environment migration — resume Scriptorium on a new machine

Last updated: 2026-11-04 / Ref: server-move/first-run + built-in TLS (0040)

This is the practical handoff for moving the development environment (or
a CI runner) to another machine/container without losing state or
re-litigating decisions. It records what is in git, what is deliberately
not in git, and the exact commands that prove the new environment is
healthy.

## 1. State snapshot

At the start of the 0040 closeout:

| Item | Value |
|---|---|
| Repository | `git@github.com:M-s-Tech4TIME/scriptorium.git` |
| Git root | the `scriptorium/` directory (the repo root contains only it) |
| Branch | `dev` |
| `dev` HEAD | `6e53875` (before the 0040 implementation commit) |
| `main` | `03f9466` (bootstrap; ancestor of `dev`) |
| Remote branches | `origin/dev` = `6e53875`, `origin/main` = `03f9466` |
| Python (local) | 3.14.5; CI uses 3.14.10 |
| Node | 26.13.0 LTS / npm 11.20.0 |
| PostgreSQL | 18.6 required; an older local PG cannot run the PG18 gate |
| Redis | 8.10.2 (bundled in packages; Docker image in dev/CI) |
| Package manager | nfpm 2.x (validated 2.48.0) |

At closeout the 0040 commit is pushed to `dev`, CI is verified green in
all three workflows, and `main` is fast-forwarded to the same commit so
both branches are byte-identical (decision 0013). `HANDOFF.md` records
the exact closeout hash and CI result.

## 2. What lives in git vs. what must be transferred

### In git (clone is enough)

- All source: `backend/`, `frontend/`, `packaging/`, `scripts/`.
- All documentation, decisions, changelogs, brain, and this history.
- Exact locks: `backend/requirements.lock`,
  `backend/requirements.prod.lock`,
  `packaging/build-requirements.lock`, `frontend/package-lock.json`.
- CI workflows, nfpm config, systemd units, example config.
- The local mypy stub `backend/typings/uvicorn_worker/__init__.pyi`.

### Not in git (transfer deliberately, or regenerate)

| Data | Why / handling |
|---|---|
| `/etc/scriptorium/config.env` | Contains `DATABASE_URL`, `SECRET_KEY`, Redis/broker URLs. Transfer over a secure channel or recreate; never commit. Keep `0600 scriptorium:scriptorium`. |
| PostgreSQL database | Dump/restore with `pg_dump -Fc` / `pg_restore`; same or newer PG major. For a supported site move use the 0039/0040 archive instead. |
| `/var/lib/scriptorium/artifacts/` | Built artifacts; normally regenerable, but a move may copy them. |
| `/var/lib/scriptorium/media/` | Uploaded images; back up with the DB. |
| `/var/lib/scriptorium/backups/` | Archives are secrets; transfer only if needed and verify SHA-256. |
| `/etc/scriptorium/tls/` | If clients must keep trusting the same CA, transfer the whole tree **including `ca.key` as a root-only secret**; otherwise generate a new CA on the new host and re-trust. |
| GitHub/CI secrets | Recreate in the repository settings; they are not in the working tree. |
| SSH keys / remote credentials | Recreate or restore from the operator's secure store. |
| `backend/.venv`, `frontend/node_modules`, `dist/` | Do not transfer; rebuild from locks. |

## 3. Prerequisites

- Git and SSH access to the GitHub remote.
- Python **3.14.x** (3.14.10 preferred; the packaged runtime is
  `/opt/scriptorium/runtime/python-3.14/bin/python3.14`).
- Node **26.13.0 LTS** and npm 11.20.0.
- PostgreSQL **18.6** (external; PG18 is exclusive per 0004).
- Redis **8.10.2** (Docker or a local server).
- nfpm 2.x if building packages; `gh` if verifying CI from the CLI.
- Optional: Docker/Podman for `docker compose up -d db redis`. In some
  sandboxes the Docker socket is denied; use external PG/Redis instead.

## 4. Clone and verify the exact state

```bash
git clone git@github.com:M-s-Tech4TIME/scriptorium.git
cd scriptorium
git fetch --all --prune
git checkout dev
git log --oneline -10
git status --short
```

The repo root contains only `scriptorium/` (decision 0012). If you are
already inside a checkout, confirm `pwd` ends in `/scriptorium` and that
`AGENTS.md` and `backend/` are direct children.

Do not start work on a dirty tree. If `git status` shows unexpected
changes, inspect them before deleting anything; they may be the previous
session's in-progress work.

## 5. Backend environment

```bash
cd backend
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.lock
python -c "import sys; print(sys.version)"
```

`requirements.lock` is the dev/test/full lock (includes ruff, mypy,
pytest, httpx, cryptography, uvicorn-worker). The runtime package uses
`requirements.prod.lock`; do not install the prod lock into the dev venv
unless you are specifically reproducing the packaged runtime.

Regenerating locks (only after an owner-approved dependency change):

```bash
# See the header of each lock for the exact uv command/version.
uv pip compile backend/pyproject.toml -o backend/requirements.lock
uv pip compile backend/pyproject.toml --no-dev -o backend/requirements.prod.lock
```

The project uses exact pins and committed locks (Rule 5). Never hand-edit
a lock.

## 6. Frontend environment

```bash
cd frontend
npm ci
npm run typecheck
```

`npm ci` is mandatory (not `npm install`) so `package-lock.json` is
authoritative. `typescript-eslint` still excludes TypeScript 7.0.2, so
`npm run lint` covers JavaScript/config only; `tsc --noEmit`
(`npm run typecheck`) is the TypeScript gate. This is a recorded scoped
exception, not a reason to change the stack.

## 7. Local services and environment variables

Set these in the shell or in `/etc/scriptorium/config.env` (the shared
loader reads the file without shell evaluation; a real environment
variable wins):

```bash
export DATABASE_URL='postgresql+asyncpg://scriptorium:scriptorium@127.0.0.1:5432/scriptorium'
export REDIS_URL='redis://127.0.0.1:6379/1'
export CELERY_BROKER_URL='redis://127.0.0.1:6379/0'
export SECRET_KEY='<fresh 48-byte URL-safe token>'
export SCRIPTORIUM_COOKIE_SECURE=false   # local HTTP dev; true in production
export SC_BUILD_DISPATCH=inline          # or celery with a running worker
export SC_BACKUP_DISPATCH=inline
```

Generate a local secret without committing it:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

With Docker:

```bash
docker compose up -d db redis
```

If Docker is unavailable (common in restricted sandboxes), point
`DATABASE_URL`/`REDIS_URL` at external services. Tests that need a live
database or Redis skip when `DATABASE_URL`/`REDIS_URL` are unset; that is
expected locally but is **not** a substitute for CI coverage.

### PostgreSQL 18 note

`migrate` and `setup` refuse PostgreSQL below 18. A local PG16 can run
some tests but will fail the PG18 version gate and cannot be used to
declare the environment healthy. Use PG18.6 (the CI service image is
`postgres:18.6`).

## 8. Full local gates

Run from the repo root unless noted.

```bash
# Backend
cd backend
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy --config-file pyproject.toml .
.venv/bin/python -m pytest -W error

# Frontend
cd ../frontend
npm run typecheck
npm run lint
npm run format:check
npm test
npm run build
npm audit --audit-level=high

# Docs/brain + packaging contract
cd ..
bash scripts/validate-docs.sh
cd backend && .venv/bin/python -m pytest tests/test_packaging.py -W error
```

Expected local behavior:

- Backend: all non-live tests pass; live-DB/Redis tests skip without
  services. At the 0040 implementation point the local run was
  **169 passed, 51 skipped** (PG18/Redis unavailable). CI runs the live
  suite with no such skips.
- Frontend: typecheck/lint/format/Vitest/build/audit pass.
- Docs validator: structure and `Last updated:` headers pass.
- Packaging contract: unit/config/doc/lock assertions pass.

`pytest -W error` is non-negotiable (Rule 6). Do not add a warning filter
or a `# type: ignore`/`noqa` without an owner-approved decision record,
a scoped allowlist, and an expiry.

## 9. TLS without root (local smoke test)

The TLS manager accepts a non-default `SC_TLS_ROOT`, so you can exercise
the whole lifecycle unprivileged:

```bash
export SC_TLS_ROOT=/tmp/opencode/tls-smoke
rm -rf "$SC_TLS_ROOT"
.venv/bin/python -m app.cli tls generate --hostname localhost --no-reload
.venv/bin/python -m app.cli tls status
.venv/bin/python -m app.cli tls verify
.venv/bin/python -m app.cli tls renew --force --no-reload
.venv/bin/python -m app.cli tls history
.venv/bin/python -m app.cli tls rollback --no-reload
.venv/bin/python -m app.cli tls prune --keep 2
```

The default `/etc/scriptorium/tls` CA creation needs root because
`ca.key` is `root:root 0600` (0040 O1). `--no-reload` avoids systemd and
is for tests/staging only.

## 10. Packaging build (optional)

The target host never runs pip; the package build does. On a build host:

```bash
packaging/scripts/fetch-python.sh
packaging/scripts/build-app-venv.sh
packaging/scripts/build-venv.sh
packaging/scripts/build-redis.sh
nfpm package --config packaging/nfpm.yaml --target dist/
```

This produces the bundled Python 3.14.10 runtime, app venv from
`requirements.prod.lock`, engine-only build venv from
`build-requirements.lock`, and Redis 8.10.2. Package installation is
covered by `docs/operations/install.md`; TLS by
`docs/operations/tls.md`; server move by
`docs/operations/server-move.md`.

## 11. CI verification and branch sync

After pushing `dev`:

```bash
gh run list --branch dev --limit 5
gh run watch <run-id>
```

All three workflows must be green: `lint-type-test`, `security`,
`packaging`. If red, stop new work, fix on `dev`, re-push, and re-verify
(Rule 7). Do not stack work on red CI.

Once `dev` is green, fast-forward `main` (ff-only, 0013) and push:

```bash
git checkout main
git merge --ff-only dev
git push origin main
git checkout dev
git rev-parse main dev origin/main origin/dev
```

All four hashes must match. If `main` has diverged, stop and investigate;
do not force-push or rewrite it.

## 12. Migration checklist

- [ ] Clone and check out `dev` at the recorded closeout commit.
- [ ] Confirm Python 3.14.x, Node 26.13.0/npm 11.20.0, PG18.6, Redis 8.10.2, nfpm 2.x.
- [ ] Create `backend/.venv` and install `requirements.lock`.
- [ ] Run `npm ci` in `frontend/`.
- [ ] Set `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `SECRET_KEY`, dispatch modes.
- [ ] Start PG18/Redis (Docker or external) and confirm connectivity.
- [ ] Run the full local gates; record pass/skip counts.
- [ ] Run the unprivileged TLS smoke test.
- [ ] `git status --short` is clean; `git log -1` matches the handoff.
- [ ] Read `AGENTS.md`, `docs/brain/README.md`, `PROJECT-SUMMARY.md`, `CURRENT-STATE.md`, `HANDOFF.md`, `TASKS.md`, `OPEN-QUESTIONS.md`.
- [ ] Continue only from `HANDOFF.md`; do not start deferred phases without owner rulings.
- [ ] If CI is needed, authenticate `gh` and verify all three workflows after any push.

## 13. Gotchas that have bitten before

- **Docker socket denied / no local PG18:** live tests skip; CI is the
  live gate. Do not “fix” skips by weakening tests.
- **Test ordering and `SECRET_KEY`:** `tests/test_auth_api.py` sets a
  dummy `SECRET_KEY` at import time. A config test that calls
  `get_setting("SECRET_KEY")` can therefore bypass file parsing. Test
  the loader with `load_config()` or an unset key; this was a real
  local failure fixed in the 0040 tranche.
- **Config precedence:** a present-but-empty environment variable wins
  over the file, deliberately, so `SECRET_KEY=` fails loud. Do not
  “helpfully” fall back to the file.
- **Mypy and `uvicorn-worker`:** the package has no `py.typed`; the local
  stub in `backend/typings/` plus `mypy_path = "typings"` is the
  approved mechanism. Do not add a broad `ignore_missing_imports`.
- **Ruff/Python 3.14 syntax:** the formatter may emit PEP 758
  unparenthesized `except A, B:`; that is valid on 3.14. Keep the
  configured target version and run the project's ruff, not an older one.
- **PG18 exclusivity:** Alembic/migrate/setup reject older majors. A
  PG16 local cluster is useful for some unit tests only.
- **Frontend ESLint:** `typescript-eslint` does not support TS 7.0.2;
  ESLint is JS/config-only and `tsc --noEmit` is the type gate. Do not
  downgrade TypeScript to make ESLint happy.
- **docutils:** stay at 0.22.4 until MyST lifts its `<0.23` cap and the
  owner approves a bump; the manual probe is the gate.
- **Archives/TLS keys are secrets:** never commit, never paste into
  brain/logs, and delete temporary copies after verification.
- **`main`/`dev` identity:** promotion is ff-only; both branches must
  point at the same commit after closeout. Never force-push `main`.

## 14. Where to look next

- Product/architecture: `docs/architecture/overview.md`, `data-model.md`,
  `api.md`.
- Current stack: `docs/technology/compatibility-matrix.md`.
- TLS: `docs/technology/tls.md`, `docs/operations/tls.md`, decision 0040.
- First run/move: `docs/operations/install.md`,
  `docs/operations/server-move.md`, decision 0040.
- Decisions: `docs/decisions/`, `docs/brain/DECISIONS-INDEX.md`.
- Live state: `docs/brain/CURRENT-STATE.md`, `HANDOFF.md`, `TASKS.md`,
  `OPEN-QUESTIONS.md`.
- Narrative: `docs/history/PROJECT-HISTORY.md` and `docs/changelog/`.
