#!/bin/sh
# postinst: create user/group/dirs, apply scriptorium:scriptorium ownership,
# seed config, check bundled runtime, daemon-reload. Never touches the DB
# (Q6/0001) and never generates TLS material (an explicit operator action).
set -eu

if ! getent group scriptorium >/dev/null 2>&1; then
  groupadd --system scriptorium
fi
if ! id -u scriptorium >/dev/null 2>&1; then
  useradd --system --gid scriptorium --home /var/lib/scriptorium \
    --shell /usr/sbin/nologin scriptorium
fi

mkdir -p /opt/scriptorium /etc/scriptorium /etc/scriptorium/tls \
  /var/lib/scriptorium/sources /var/lib/scriptorium/builds \
  /var/lib/scriptorium/artifacts /var/lib/scriptorium/media \
  /var/lib/scriptorium/uploads /var/lib/scriptorium/backups \
  /var/lib/scriptorium/backups/tmp /var/lib/scriptorium/redis \
  /var/log/scriptorium /var/cache/scriptorium

if [ ! -f /etc/scriptorium/config.env ] && [ -f /usr/share/doc/scriptorium/config.env.example ]; then
  install -m 0600 -o scriptorium -g scriptorium \
    /usr/share/doc/scriptorium/config.env.example /etc/scriptorium/config.env
fi
if [ ! -f /etc/scriptorium/redis.conf ] && [ -f /usr/share/doc/scriptorium/redis.conf.example ]; then
  install -m 0640 -o scriptorium -g scriptorium \
    /usr/share/doc/scriptorium/redis.conf.example /etc/scriptorium/redis.conf
fi

# Owner ruling: every Scriptorium-managed file/directory is
# scriptorium:scriptorium. The sole TLS exception is the local CA private
# key, which stays root:root 0600 (decision 0040 O1/F-B1).
chown -R scriptorium:scriptorium /opt/scriptorium /etc/scriptorium \
  /var/lib/scriptorium /var/log/scriptorium /var/cache/scriptorium
chmod 0600 /etc/scriptorium/config.env 2>/dev/null || true
if [ -f /etc/scriptorium/tls/ca.key ]; then
  chown root:root /etc/scriptorium/tls/ca.key
  chmod 0600 /etc/scriptorium/tls/ca.key
fi

for required in \
  /opt/scriptorium/runtime/python-3.14/bin/python3.14 \
  /opt/scriptorium/backend/.venv/bin/python \
  /opt/scriptorium/backend/.venv/bin/scriptorium-admin \
  /opt/scriptorium/backend/.venv/bin/uvicorn \
  /opt/scriptorium/build-venv/bin/python \
  /opt/scriptorium/redis/bin/redis-server; do
  if [ ! -x "$required" ]; then
    echo "ERROR: packaged runtime missing: $required — rebuild the package with packaging/scripts/*.sh" >&2
    exit 1
  fi
done

systemctl daemon-reload 2>/dev/null || true
systemctl enable scriptorium-tls-renew.timer 2>/dev/null || true
echo "Scriptorium installed."
echo "Next:"
echo "  sudo scriptorium-admin setup"
echo "  sudo scriptorium-admin tls generate --hostname <public-host>"
echo "  sudo scriptorium-admin migrate"
echo "  sudo scriptorium-admin user create --email <owner-email> --display <name>"
echo "  sudo systemctl enable --now scriptorium-redis scriptorium-redirect scriptorium-web scriptorium-worker"
