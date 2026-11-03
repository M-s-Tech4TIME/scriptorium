"""Celery tasks (M4-C3, 0026; backup jobs, 0039).

The task bodies share `app.sphinx.execute` / `app.backup.execute` with
inline dispatch, so production and dev/CI run the identical code path
(one implementation, two schedulers). The single-argument form keeps the
queue JSON-serial. `shared_task` plus the app's `include=
["app.worker.tasks"]` registers the exact names the routers dispatch by;
the executor runs on Celery's default prefork pool, where blocking sync
work is safe.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from celery import shared_task

# Celery ships no py.typed marker; this local shim keeps the decorator
# typed (function in, same function out) without a suppression directive.
_F = TypeVar("_F", bound=Callable[..., Any])
_task: Callable[..., Callable[[_F], _F]] = shared_task


@_task(name="app.worker.tasks.run_athenaeum_build")
def run_athenaeum_build(build_id: str) -> None:
    from app.sphinx.execute import execute_build_sync

    execute_build_sync(build_id)


@_task(name="app.worker.tasks.run_backup_export")
def run_backup_export(job_id: str) -> None:
    from app.backup.execute import execute_export_sync

    execute_export_sync(job_id)


@_task(name="app.worker.tasks.run_backup_restore")
def run_backup_restore(job_id: str) -> None:
    from app.backup.execute import execute_restore_sync

    execute_restore_sync(job_id)
