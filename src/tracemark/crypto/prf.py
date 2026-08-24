"""Low-level pseudorandom primitives built on HMAC-SHA256 / HKDF-SHA256.

No custom cryptography. Domain-separated everywhere so one key never serves
two unrelated purposes.
"""

from __future__ import annotations

import hashlib
import hmac

_EMPTY = b""

# 256-bit salt length for HKDF.
_SALT_LEN = 32


def hkdf(
    ikm: bytes,
    *,
    info: bytes,
    length: int = 32,
) -> bytes:
    """HKDF-SHA256 key derivation with domain-separated ``info``."""
    salt = hashlib.sha256(b"tracemark-hkdf-salt" + _EMPTY).digest()[: _SALT_LEN]
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    output = b""
    t = b""
    counter = 1
    while len(output) < length:
        t = hmac.new(prk, t + info + bytes([counter]), hashlib.sha256).digest()
        output += t
        counter += 1
    return output[:length]


def prf_bytes(key: bytes, message: bytes) -> bytes:
    """HMAC-SHA256(key, message)."""
    return hmac.new(key, message, hashlib.sha256).digest()


def pseudo_random_bit(key: bytes, message: bytes) -> int:
    """Return a single deterministic pseudorandom bit from an HMAC-SHA256.

    The message is expected to already be domain-separated by the caller.
    """
    digest = hmac.new(key, message, hashlib.sha256).digest()
    return digest[0] & 1


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()
