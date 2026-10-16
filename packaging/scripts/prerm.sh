#!/bin/sh
# prerm: stop/disable units only. Never drops data or DB (Q6).
set -eu
systemctl stop scriptorium-web scriptorium-worker 2>/dev/null || true
systemctl disable scriptorium-web scriptorium-worker 2>/dev/null || true
echo "Scriptorium services stopped. Data in /var/lib/scriptorium and PG DB preserved."
