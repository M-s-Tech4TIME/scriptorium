# Operations — install/upgrade (target, Q5/Q6)

Last updated: 2026-10-24 / Ref: M4-C4 packaging (0026; signed M5 package
pipeline still pending)

- **Package build:** run `packaging/scripts/build-venv.sh` before `nfpm
  package`; it creates `packaging/build-venv` from
  `packaging/build-requirements.lock` (Sphinx 9.1.0 / docutils 0.22.4 /
  MyST 5.1.0 only). nfpm installs it at `/opt/scriptorium/build-venv`;
  production sets `SC_BUILD_PYTHON=/opt/scriptorium/build-venv/bin/python`.
  The installed package never runs pip or reaches the network.
- **Install** `.deb`/`.rpm` (needs PG18 + Redis present): `postinst` creates
  the `scriptorium` user and dirs (`/opt`, `/etc/scriptorium` 0600,
  `/var/lib|log|cache/scriptorium`, including `artifacts/`), seeds
  `/etc/scriptorium/config.env` from the packaged example only when it
  does not exist, checks the isolated build venv, and runs `daemon-reload`.
  It never touches the DB.
- **Configure** `/etc/scriptorium/config.env` (0600) or use env overrides:
  `DATABASE_URL`, `SECRET_KEY`, `SCRIPTORIUM_COOKIE_SECURE`,
  `REDIS_URL` (limiter), `CELERY_BROKER_URL` (worker),
  `SC_BUILD_DISPATCH=celery`, `SC_BUILD_PYTHON`, `SC_ARTIFACT_ROOT`,
  `SC_BUILD_ROOT`, and the `SC_SPHINX_*` limits. The packaged example is
  at `/usr/share/doc/scriptorium/config.env.example`.
- **Initialise:** generate `SECRET_KEY` first
  (`python3 -c 'import secrets; print(secrets.token_urlsafe(48))'`) and
  put it in `config.env`; then `sudo -u scriptorium scriptorium-admin
  setup` (DB check) and `sudo -u scriptorium scriptorium-admin migrate`
  (idempotent Alembic; refuses PG<18). An empty key fails loud at auth
  time rather than accepting a placeholder.
- **Start:** `systemctl enable --now scriptorium-web scriptorium-worker`.
  Both units `Requires=redis.service` and start `After=redis.service`;
  `postinst` never migrates.
- **Upgrade:** package lays files, prints the migrate reminder; rollback =
  restore `/var/lib` + DB backup + previous package.
- **M5** adds signing/provenance, the full app-venv assembly, and the
  complete admin/upgrade guide; this page records the M4-C4 contract.
