"""API credential token handling.

Raw tokens are shown once at creation; only a SHA-256 hash is persisted.
"""

from __future__ import annotations

import hashlib
import secrets

_TOKEN_BYTES = 32


def generate_token() -> str:
    """Generate a new random API token (shown once)."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Stable SHA-256 hex digest of a raw token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return secrets.compare_digest(a, b)
