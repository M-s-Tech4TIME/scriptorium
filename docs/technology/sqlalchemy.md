# Technology — SQLAlchemy 2.1.6 + Alembic 1.20.1 (+ asyncpg)

- Versions (locked): SQLAlchemy 2.1.6 (2026-10), Alembic 1.20.1
  (2026-09-11, needs SQLA ≥2.0), asyncpg 0.32.0.
- Why: 2.x API for models/migrations; async driver for FastAPI (decision 0005/0010).
- Used: `backend/app/models/`, `backend/alembic/` (M1). Migrations via explicit
  `scriptorium-admin migrate` (Q6); refuses PG <18.
- Verified: 2026-10-30 (PyPI/GitHub; lock resolved 2026-10-30).
