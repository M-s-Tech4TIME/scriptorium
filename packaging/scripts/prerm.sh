#!/bin/sh
# prerm: stop/disable units only. Never drops data or DB (Q6).
set -eu
systemctl disable --now scriptorium-tls-renew.timer 2>/dev/null || true
systemctl stop scriptorium-redirect scriptorium-web scriptorium-worker \
  scriptorium-redis 2>/dev/null || true
systemctl disable scriptorium-redirect scriptorium-web scriptorium-worker \
  scriptorium-redis 2>/dev/null || true
echo "Scriptorium services stopped. Data in /var/lib/scriptorium and PG DB preserved."
