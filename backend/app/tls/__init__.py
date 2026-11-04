"""Built-in TLS lifecycle (decision 0040, Q-SM-F = F-A…F-L).

The application terminates HTTPS itself. There is no required reverse
proxy and no plaintext application listener. This package owns the local
CA, leaf certificates, atomic install/rollback, the hardened TLS context,
the HTTP→HTTPS redirect listener, HSTS, and the operator-facing status
and verification data used by ``scriptorium-admin tls``.
"""

from __future__ import annotations

from app.tls.manager import (
    TlsError,
    TlsStatus,
    ca_export_bytes,
    generate,
    history,
    hsts,
    import_pair,
    prune,
    renew,
    rollback,
    status,
    verify,
)

__all__ = [
    "TlsError",
    "TlsStatus",
    "ca_export_bytes",
    "generate",
    "history",
    "hsts",
    "import_pair",
    "prune",
    "renew",
    "rollback",
    "status",
    "verify",
]
