# 0005 — Framework / queue / storage (Q13/Q14/Q17)

Status: accepted | Date: 2026-10-16 | Approver: owner
Context: §9 open items; owner LTS/proven lens.
Options: Framework — FastAPI 0.143 pinned vs Django 5.2 LTS vs Flask/Litestar (rejected: wiring / too new).
Queue — Celery 5.6.3+Redis (15yr proven) vs Dramatiq 2.2.1 vs ARQ/RQ (least proven).
Storage — fs+DB metadata vs bare-Git-now (heavier v1) vs DB-rows (contradicts brief).
Decision: FastAPI pinned; Celery+Redis; `/var/lib/scriptorium/{sources,builds,uploads}` + DB metadata + history table, Git-ready for Phase A.
Consequences: FastAPI 0.x rolling risk handled by pin+lock+quarterly upgrades; Celery config weight accepted.
