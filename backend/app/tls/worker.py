"""Gunicorn worker that terminates HTTPS with the hardened TLS context (0040).

Gunicorn starts this worker with ``--certfile``/``--keyfile`` so a missing
certificate fails the boot loudly. The worker then replaces Uvicorn's
default context factory with :func:`app.tls.crypto.create_server_context`,
which enforces the approved protocol/cipher policy. Proxy headers stay
disabled: the socket peer is the only client address the application ever
sees (F-L1).
"""

from __future__ import annotations

import ssl
from typing import Any, ClassVar

from uvicorn_worker import UvicornWorker

from app.tls.crypto import create_server_context
from app.tls.state import cert_path, key_path


class TlsUvicornWorker(UvicornWorker):
    """Uvicorn worker with a built-in, hardened TLS server context."""

    CONFIG_KWARGS: ClassVar[dict[str, Any]] = {
        **UvicornWorker.CONFIG_KWARGS,
        "proxy_headers": False,
        "forwarded_allow_ips": None,
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if not self.cfg.is_ssl:
            raise RuntimeError(
                "TlsUvicornWorker requires --certfile and --keyfile; "
                "plaintext listeners are not supported (0040 F-A1)."
            )
        self.config.ssl_context_factory = _context_factory


def _context_factory() -> ssl.SSLContext:
    return create_server_context(cert_path(), key_path())
