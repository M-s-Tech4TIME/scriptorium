"""Celery worker package (M4, decision 0026 / 0005).

Production dispatch mode (`SC_BUILD_DISPATCH=celery`, the default) sends
`app.worker.tasks.run_athenaeum_build` through the broker; the systemd
worker unit must start after Redis (packaging note, M4-C4). Dev/CI uses
`SC_BUILD_DISPATCH=inline` (the request thread executes the build; see
app/sphinx/execute.py).
"""
