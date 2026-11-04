"""Minimal type surface for the pinned ``uvicorn-worker`` package.

The package ships no ``py.typed`` marker. Scriptorium subclasses one
worker class and reads/writes only ``CONFIG_KWARGS``, ``cfg``, and
``config`` (decision 0040 F-H1), so this stub intentionally stays tiny.
"""

from typing import Any, ClassVar

class UvicornWorker:
    CONFIG_KWARGS: ClassVar[dict[str, Any]]
    cfg: Any
    config: Any
    log: Any
    timeout: int
    max_requests: int
    callback_notify: Any
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
