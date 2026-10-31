"""HTTP security contract for served artifacts (decision 0035 E2).

The generated site is static, so the serving host owns the headers. This
module builds one policy from the artifact manifest:

- scripts: same-origin plus the exact hashes of the theme's two inline
  bootstrap blocks (panel state + search map), never ``'unsafe-inline'``;
- styles: same-origin external CSS only (custom CSS is a file);
- images/fonts: same-origin (plus ``data:`` for the theme's inline SVG
  masks, which are local data, not network requests);
- connections: same-origin only (the first-party search fetches its own
  artifact pages);
- no framing, objects, or base-URI rewriting.

The same headers apply to public and private sites. Private sites add
``X-Robots-Tag`` and a private cache policy in the router.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.serving.manifest import manifest_script_hashes

# The theme's local data-URL masks are the only non-'self' image source.
CSP_BASE = (
    "default-src 'none'; "
    "script-src 'self'{script_hashes}; "
    "script-src-attr 'none'; "
    "style-src 'self'; "
    "style-src-attr 'none'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "media-src 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'none'; "
    "form-action 'self'; "
    "worker-src 'none'"
)

SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=(), "
        "interest-cohort=()"
    ),
    "X-Frame-Options": "DENY",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
}


def content_security_policy(manifest: Mapping[str, Any]) -> str:
    hashes = manifest_script_hashes(dict(manifest))
    suffix = "".join(f" '{value}'" for value in hashes)
    return CSP_BASE.format(script_hashes=suffix)


def artifact_headers(
    manifest: Mapping[str, Any],
    *,
    immutable: bool,
    private: bool,
) -> dict[str, str]:
    """Return the full response header set for one artifact file."""
    headers = dict(SECURITY_HEADERS)
    headers["Content-Security-Policy"] = content_security_policy(manifest)
    if private:
        headers["Cache-Control"] = "private, no-store"
        headers["X-Robots-Tag"] = "noindex, nofollow"
        headers["Vary"] = "Cookie"
    elif immutable:
        headers["Cache-Control"] = "public, max-age=31536000, immutable"
    else:
        headers["Cache-Control"] = "no-cache"
    return headers
