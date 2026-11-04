# Operations — install/upgrade (target, Q5/Q6)

Last updated: 2026-11-04 / Ref: decision 0040; M5 signed package pipeline
still pending

- **Package build:** run `packaging/scripts/fetch-python.sh`,
  `build-app-venv.sh`, `build-venv.sh` and `build-redis.sh` before
  `nfpm package`. They create the bundled Python 3.14.10 runtime, the app
  venv from `backend/requirements.prod.lock` (runtime-only), the isolated
  build venv from `packaging/build-requirements.lock` (Sphinx 9.2.0 /
  docutils 0.22.4 / MyST 5.1.0 only), and Redis 8.10.2. nfpm installs them
  at `/opt/scriptorium/runtime/python-3.14`,
  `/opt/scriptorium/backend/.venv`, `/opt/scriptorium/build-venv` and
  `/opt/scriptorium/redis`. Production sets
  `SC_BUILD_PYTHON=/opt/scriptorium/build-venv/bin/python`. The installed
  package never runs pip or reaches the network.
- **Install** `.deb`/`.rpm` (needs PG18): `postinst` creates the
  `scriptorium` group/user and dirs (`/opt`, `/etc/scriptorium`,
  `/etc/scriptorium/tls`, `/var/lib|log|cache/scriptorium`, including
  `artifacts/`, `media/`, `backups/`, and `redis/`), seeds
  `/etc/scriptorium/config.env` (`0600 scriptorium:scriptorium`) and
  `/etc/scriptorium/redis.conf` from the packaged examples only when they
  do not exist, applies `scriptorium:scriptorium` ownership recursively,
  forces `ca.key` back to `root:root 0600` when present, checks the
  bundled runtimes, runs `daemon-reload`, and enables the TLS renewal
  timer. It never touches the DB and never generates certificates.
- **Configure** `/etc/scriptorium/config.env` (0600) or use env overrides:
  `DATABASE_URL`, `SECRET_KEY`, `SCRIPTORIUM_COOKIE_SECURE`,
  `REDIS_URL` (limiter), `CELERY_BROKER_URL` (worker),
  `SC_BUILD_DISPATCH=celery`, `SC_BUILD_PYTHON`, `SC_ARTIFACT_ROOT`,
  `SC_BUILD_ROOT`, `SC_MEDIA_ROOT` (default `/var/lib/scriptorium/media`),
  `SC_BACKUP_DISPATCH=celery`, `SC_BACKUP_ROOT` (default
  `/var/lib/scriptorium/backups`), the optional `SC_BACKUP_*` size/entry/
  download-TTL overrides, the `SC_SPHINX_*` limits, and the built-in TLS
  keys:
  `SC_TLS_BIND` (default `0.0.0.0:443`), `SC_HTTP_HOST`
  (`0.0.0.0`), `SC_HTTP_PORT` (`80`), `SC_TLS_ROOT`
  (`/etc/scriptorium/tls`), optional `SC_TLS_CERT`/`SC_TLS_KEY`,
  `SC_TLS_REDIRECT_HOST`, and `SC_TLS_HSTS_MAX_AGE`. The packaged examples
  are at `/usr/share/doc/scriptorium/`. The shared loader does no shell
  evaluation; a real environment variable wins over the file.
- **Initialise (first run):**
  1. Generate `SECRET_KEY`
     (`/opt/scriptorium/runtime/python-3.14/bin/python3.14 -c 'import
     secrets; print(secrets.token_urlsafe(48))'`) and put it in
     `config.env`. An empty key fails loud at auth time.
  2. Issue TLS before enabling the web unit:
     `sudo scriptorium-admin tls generate --hostname docs.example.com`
     or `sudo scriptorium-admin tls import --cert fullchain.pem --key
     privkey.pem`; then `sudo scriptorium-admin tls verify`.
  3. `sudo scriptorium-admin setup` (read-only preflight: config, key,
     PG18, Alembic head/pending, roots, build Python, TLS).
  4. `sudo scriptorium-admin migrate` (idempotent Alembic; refuses PG<18).
  5. `sudo scriptorium-admin user create --email owner@example.com
     --display "Owner"` (TTY prompt or `--password-stdin`; 12–1024
     characters, Argon2id). There is no open registration.
- **Serve:** the web unit terminates HTTPS itself on `SC_TLS_BIND` with
  `app.tls.worker.TlsUvicornWorker`; `scriptorium-redirect.service`
  answers HTTP on `SC_HTTP_HOST:SC_HTTP_PORT` with a `308` to HTTPS. No
  reverse proxy is required and there is no plaintext application
  listener. Published sites are served at `/a/{public_slug}/`; private
  sites use the short-lived `/a` access cookie set by login/refresh; keep
  `SCRIPTORIUM_COOKIE_SECURE=true`. Public/private and publication
  pointers are owner API actions (0035), not config keys. Exported
  artifacts include `manifest.json`; a static host must apply the
  documented E2 headers itself.
- **Start:** `systemctl enable --now scriptorium-redis
  scriptorium-redirect scriptorium-web scriptorium-worker` and
  `scriptorium-tls-renew.timer`. The app units require
  `scriptorium-redis.service` and start after it; `postinst` never
  migrates. Both privileged ports use `CAP_NET_BIND_SERVICE`; services run
  as `scriptorium` with read-only `/opt` and `/etc`.
- **Ownership:** every Scriptorium-managed file/directory is
  `scriptorium:scriptorium`. Accepted exceptions: systemd unit files and
  package metadata (root), the external PostgreSQL data directory
  (`postgres`), and the local CA private key (`root:root 0600`).
- **Upgrade:** the package lays files and prints the migrate reminder; run
  `scriptorium-admin setup` then `scriptorium-admin migrate`. Rollback =
  restore `/var/lib` + DB backup + previous package. Keep the old host for
  a server move until its rollback window passes.
- **Server move:** see `docs/operations/server-move.md` (installed as
  `/usr/share/doc/scriptorium/server-move.md`). TLS lifecycle:
  `docs/operations/tls.md`.
- **M5** adds signing/provenance, the full admin/upgrade guide, and the
  signed package pipeline; this page records the current packaging
  contract.
