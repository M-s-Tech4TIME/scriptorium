# Operations — install/upgrade (target, Q5/Q6)

Last updated: 2026-10-16 / Ref: uncommitted (M5 implements)

- Install `.deb`/`.rpm` (needs PG18 + Redis present): creates `scriptorium` user, dirs
  (`/opt`, `/etc/scriptorium` 0600, `/var/lib|log|cache/scriptorium`), `daemon-reload`.
- Configure `/etc/scriptorium/config.env` (DB_URL, SECRET_KEY) or env override.
- `sudo -u scriptorium scriptorium-admin setup` (secret, DB check) then
  `sudo -u scriptorium scriptorium-admin migrate` (idempotent Alembic; refuses PG<18).
- `systemctl enable --now scriptorium-web scriptorium-worker`. `postinst` never migrates.
- Upgrade: package lays files, prints migrate reminder; rollback = restore `/var/lib` + DB backup + previous package.
- Full admin guide lands in M5.
