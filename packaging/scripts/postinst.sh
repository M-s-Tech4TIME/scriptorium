#!/bin/sh
# postinst: create user/dirs/perms, seed config, check bundled runtime,
# daemon-reload. Never touches the DB (Q6/0001).
set -eu
id -u scriptorium >/dev/null 2>&1 || useradd --system --home /var/lib/scriptorium --shell /usr/sbin/nologin scriptorium
mkdir -p /opt/scriptorium /etc/scriptorium /var/lib/scriptorium/sources /var/lib/scriptorium/builds /var/lib/scriptorium/artifacts /var/lib/scriptorium/media /var/lib/scriptorium/uploads /var/lib/scriptorium/redis /var/log/scriptorium /var/cache/scriptorium
if [ ! -f /etc/scriptorium/config.env ] && [ -f /usr/share/doc/scriptorium/config.env.example ]; then
  install -m 0600 -o root -g root /usr/share/doc/scriptorium/config.env.example /etc/scriptorium/config.env
fi
if [ ! -f /etc/scriptorium/redis.conf ] && [ -f /usr/share/doc/scriptorium/redis.conf.example ]; then
  install -m 0640 -o root -g scriptorium /usr/share/doc/scriptorium/redis.conf.example /etc/scriptorium/redis.conf
fi
chmod 0600 /etc/scriptorium/config.env 2>/dev/null || true
for required in \
  /opt/scriptorium/runtime/python-3.14/bin/python3.14 \
  /opt/scriptorium/backend/.venv/bin/python \
  /opt/scriptorium/backend/.venv/bin/scriptorium-admin \
  /opt/scriptorium/build-venv/bin/python \
  /opt/scriptorium/redis/bin/redis-server; do
  if [ ! -x "$required" ]; then
    echo "ERROR: packaged runtime missing: $required — rebuild the package with packaging/scripts/*.sh" >&2
    exit 1
  fi
done
chown -R scriptorium:scriptorium /var/lib/scriptorium /var/log/scriptorium /var/cache/scriptorium
systemctl daemon-reload 2>/dev/null || true
echo "Scriptorium installed. Next: sudo -u scriptorium scriptorium-admin setup && sudo -u scriptorium scriptorium-admin migrate && systemctl enable --now scriptorium-redis scriptorium-web scriptorium-worker"
