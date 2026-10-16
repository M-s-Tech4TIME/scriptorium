# 0002 — Distro baselines

Status: accepted | Date: 2026-10-16 | Approver: owner
Context: Rule 5.3 requires verifying against target distros' system libs.
Options: (A) Ubuntu 24.04 LTS + Debian 12 + RHEL 9 + Fedora 41/43-44 + openSUSE Leap 15.6 vs (B) narrower (Ubuntu-only).
Decision: (A). Consequences: Python 3.12 max-common; PG18 via PGDG where needed; CI matrix covers deb+.rpm families.
