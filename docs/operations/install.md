# Operations — install/upgrade (target, Q5/Q6)

Last updated: 2026-10-30 / Ref: stack-upgrade phase (0037); M5 signed
package pipeline still pending

- **Package build:** run `packaging/scripts/fetch-python.sh`,
  `build-app-venv.sh`, `build-venv.sh` and `build-redis.sh` before
  `nfpm package`. They create the bundled Python 3.14.10 runtime, the app
  venv from `backend/requirements.prod.lock` (runtime-only), the isolated build venv from
  `packaging/build-requirements.lock` (Sphinx 9.2.0 / docutils 0.22.4 /
  MyST 5.1.0 only), and Redis 8.10.2. nfpm installs them at
  `/opt/scriptorium/runtime/python-3.14`, `/opt/scriptorium/backend/.venv`,
  `/opt/scriptorium/build-venv` and `/opt/scriptorium/redis`. Production
  sets `SC_BUILD_PYTHON=/opt/scriptorium/build-venv/bin/python`. The
  installed package never runs pip or reaches the network.
- **Install** `.deb`/`.rpm` (needs PG18): `postinst` creates the
  `scriptorium` user and dirs (`/opt`, `/etc/scriptorium` 0600,
  `/var/lib|log|cache/scriptorium`, including `artifacts/` and `redis/`),
  seeds `/etc/scriptorium/config.env` and `/etc/scriptorium/redis.conf`
  from the packaged examples only when they do not exist, checks the
  bundled runtimes, and runs `daemon-reload`. It never touches the DB.
- **Configure** `/etc/scriptorium/config.env` (0600) or use env overrides:
  `DATABASE_URL`, `SECRET_KEY`, `SCRIPTORIUM_COOKIE_SECURE`,
  `REDIS_URL` (limiter), `CELERY_BROKER_URL` (worker),
  `SC_BUILD_DISPATCH=celery`, `SC_BUILD_PYTHON`, `SC_ARTIFACT_ROOT`,
  `SC_BUILD_ROOT`, and the `SC_SPHINX_*` limits. The packaged examples
  are at `/usr/share/doc/scriptorium/`.
- **Initialise:** generate `SECRET_KEY` first
  (`/opt/scriptorium/runtime/python-3.14/bin/python3.14 -c 'import secrets;
  print(secrets.token_urlsafe(48))'`) and put it in `config.env`; then
  `sudo -u scriptorium scriptorium-admin setup` (DB check) and
  `sudo -u scriptorium scriptorium-admin migrate` (idempotent Alembic;
  refuses PG<18). An empty key fails loud at auth time rather than
  accepting a placeholder.
- **Serve:** published sites are served by the web unit at
  `/a/{public_slug}/`; no nginx alias is required for v1. Private sites
  use the short-lived `/a` access cookie set by login/refresh; keep
  `SCRIPTORIUM_COOKIE_SECURE=true` behind HTTPS. Public/private and
  publication pointers are owner API actions (0035), not config keys.
  Exported artifacts include `manifest.json`; a static host must apply the
  documented E2 headers itself.
- **Start:** `systemctl enable --now scriptorium-redis scriptorium-web
  scriptorium-worker`. Both app units `Requires=scriptorium-redis.service`
  and start after it; `postinst` never migrates.
- **Upgrade:** package lays files, prints the migrate reminder; rollback =
  restore `/var/lib` + DB backup + previous package.
- **M5** adds signing/provenance, the full admin/upgrade guide, and the
  signed package pipeline; this page records the current packaging
  contract.
