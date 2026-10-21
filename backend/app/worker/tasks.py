"""Celery task — executes one build (M4-C3).

The task body shares `app.sphinx.execute` with inline dispatch, so
production and dev/CI run the identical code path (one implementation,
two schedulers). The single-argument form keeps the queue JSON-serial.
"""

from __future__ import annotations


def run_athenaeum_build(build_id: str) -> None:
    from app.sphinx.execute import execute_build_sync

    execute_build_sync(build_id)
