"""Celery discovery module (the `-A app.worker` skeleton file).

Celery's `find_app` resolves `-A app.worker` by trying the package's
`app`/`celery` attributes and then the `app.worker.celery` submodule — so
this file instantiates the app exactly the way the standard skeleton does.
It runs ONLY in the worker process (systemd unit) or an explicit `celery`
invocation; the web app and dev/CI inline dispatch never import it.
"""

from app.worker.celery_app import build_app

app = build_app()
