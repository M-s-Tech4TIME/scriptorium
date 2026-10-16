# 0004 — PostgreSQL 18.x exclusive (Q15)

Status: accepted | Date: 2026-10-16 | Approver: owner
Context: PG external; need one certified line (5-yr policy: 18 → 2030-11-14, current 18.6).
Options: (A) Require 18.x exclusively vs (B) support 15–18 (4x matrix).
Decision: (A). `migrate` refuses <18; docs point to PGDG where distro default older.
Consequences: Simplest matrix; more install friction on Debian 12/Ubuntu 24.04/RHEL 9 defaults (documented).
