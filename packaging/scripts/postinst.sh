#!/bin/sh
# postinst: create user/dirs/perms, seed config, check build venv, daemon-reload.
# Never touches the DB (Q6/0001).
set -eu
id -u scriptorium >/dev/null 2>&1 || useradd --system --home /var/lib/scriptorium --shell /usr/sbin/nologin scriptorium
mkdir -p /opt/scriptorium /etc/scriptorium /var/lib/scriptorium/sources /var/lib/scriptorium/builds /var/lib/scriptorium/artifacts /var/lib/scriptorium/uploads /var/log/scriptorium /var/cache/scriptorium
if [ ! -f /etc/scriptorium/config.env ] && [ -f /usr/share/doc/scriptorium/config.env.example ]; then
  install -m 0600 -o root -g root /usr/share/doc/scriptorium/config.env.example /etc/scriptorium/config.env
fi
chmod 0600 /etc/scriptorium/config.env 2>/dev/null || true
if [ ! -x /opt/scriptorium/build-venv/bin/python ]; then
  echo "ERROR: isolated build venv missing at /opt/scriptorium/build-venv — rebuild the package with packaging/scripts/build-venv.sh" >&2
  exit 1
fi
chown -R scriptorium:scriptorium /var/lib/scriptorium /var/log/scriptorium /var/cache/scriptorium
systemctl daemon-reload 2>/dev/null || true
echo "Scriptorium installed. Next: sudo -u scriptorium scriptorium-admin setup && sudo -u scriptorium scriptorium-admin migrate && systemctl enable --now scriptorium-web scriptorium-worker"
