"""Celery application wiring (0005: Celery 5.6.3 + Redis broker).

The broker URL comes from `CELERY_BROKER_URL` (or `/etc/scriptorium/
config.env` in packaged form) only when dispatch mode is `celery` —
dev/CI inline mode never touches the broker (fail-loud elsewhere).
"""

from __future__ import annotations

from celery import Celery

from app.config import get_setting


def _broker_url() -> str:
    url = get_setting("CELERY_BROKER_URL")
    if not url:
        raise RuntimeError(
            "CELERY_BROKER_URL is not set (env or /etc/scriptorium/config.env)."
        )
    return url


def build_app() -> Celery:
    app = Celery("scriptorium", broker=_broker_url(), include=["app.worker.tasks"])
    app.conf.update(
        task_default_queue="scriptorium",
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        broker_connection_retry_on_startup=True,
    )
    return app


_app: Celery | None = None


def get_app() -> Celery:
    global _app
    if _app is None:
        _app = build_app()
    return _app


def reset_app() -> None:
    global _app
    _app = None
