"""Public URL-name namespace constants (0036/0039).

The registry is global. Both ordinary rename/create and restore must use the
same advisory lock and reserved-word set, or two allocation paths could race
or disagree about what counts as free.
"""

from __future__ import annotations

import re

PUBLIC_NAME_RE = re.compile(r"[a-z0-9-]+")
RESERVED_PUBLIC_SLUGS = frozenset({"latest", "stable", "b", "_static", "api"})
PUBLIC_NAMES_LOCK = int.from_bytes(b"SDNS", "big", signed=True)


def valid_public_name(slug: str) -> bool:
    return bool(PUBLIC_NAME_RE.fullmatch(slug))
