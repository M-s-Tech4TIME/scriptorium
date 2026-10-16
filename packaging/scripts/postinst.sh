#!/bin/sh
# postinst: create user/dirs/perms + daemon-reload ONLY. Never touches the DB (Q6/0001).
set -eu
id -u scriptorium >/dev/null 2>&1 || useradd --system --home /var/lib/scriptorium --shell /usr/sbin/nologin scriptorium
mkdir -p /opt/scriptorium /etc/scriptorium /var/lib/scriptorium/sources /var/lib/scriptorium/builds /var/lib/scriptorium/uploads /var/log/scriptorium /var/cache/scriptorium
chmod 0600 /etc/scriptorium/config.env 2>/dev/null || true
chown -R scriptorium:scriptorium /var/lib/scriptorium /var/log/scriptorium /var/cache/scriptorium
systemctl daemon-reload 2>/dev/null || true
echo "Scriptorium installed. Next: sudo -u scriptorium scriptorium-admin setup && sudo -u scriptorium scriptorium-admin migrate && systemctl enable --now scriptorium-web scriptorium-worker"
