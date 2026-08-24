"""Fingerprint key derivation.

Employee fingerprints are pseudonymous: we never embed an employee id or
email into text. Instead we derive a per-tenant, per-employee secret key and
embed only the statistical pattern that key induces over linguistic choices.

Chain of derivation (all HMAC/HKDF, domain separated):

    master_key
        -> tenant_secret = HKDF(master, "tracemark/tenant/v1" || tenant_id)
        -> subject_tag   = trunc(HMAC(tenant_secret, "subject-tag/v1" || ref), 16)
        -> employee_key  = HKDF(tenant_secret, "tracemark/fingerprint/v1" || subject_tag)
        -> model_key     = HKDF(employee_key, "tracemark/model-scope/v1" || scope)

``subject_tag`` is pseudonymous and safe to store in the database. The derived
fingerprint key is secret and never persisted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from tracemark.crypto.prf import hkdf, prf_bytes, pseudo_random_bit

_TAG_DOMAIN = b"subject-tag/v1"
_FINGERPRINT_DOMAIN = "tracemark/fingerprint/v1"
_MODEL_SCOPE_DOMAIN = "tracemark/model-scope/v1"
_TENANT_DOMAIN = "tracemark/tenant/v1"
_EXPECTED_BIT_DOMAIN = b"tracemark/expected-bit/v1"

_TAG_BYTES = 16
_TAG_HEX_LEN = 32

_SCOPE_NORMALIZER = re.compile(r"[^a-z0-9.-]")


@dataclass(frozen=True)
class FingerprintIdentity:
    tenant_id: UUID
    subject_tag: str
    model_scope: str | None = None


@dataclass(frozen=True)
class DerivedFingerprint:
    subject_tag: str
    key: bytes


def normalize_model_scope(scope: str) -> str:
    """Normalize a model scope to a stable canonical string.

    Lowercase, strip surrounding whitespace and collapse any character that
    is not alphanumeric, ``-`` or ``.`` to ``-``.
    """
    cleaned = _SCOPE_NORMALIZER.sub("-", scope.strip().lower())
    cleaned = re.sub(r"-+", "-", cleaned)
    return cleaned.strip("-")


def derive_tenant_secret(*, master_key: bytes, tenant_id: UUID) -> bytes:
    return hkdf(master_key, info=_TENANT_DOMAIN.encode() + tenant_id.bytes)


def derive_subject_tag(*, tenant_secret: bytes, subject_external_ref: str) -> str:
    """Deterministic 128-bit pseudonymous tag for a subject.

    The external reference (e.g. "employee-98372") never appears in output.
    """
    message = _TAG_DOMAIN + subject_external_ref.encode("utf-8")
    digest = prf_bytes(tenant_secret, message)[:_TAG_BYTES]
    return digest.hex()


def derive_key_from_subject_tag(*, tenant_secret: bytes, subject_tag: str) -> bytes:
    """Employee fingerprint key from a stored pseudonymous tag."""
    return hkdf(
        tenant_secret, info=_FINGERPRINT_DOMAIN.encode() + subject_tag.encode("ascii")
    )


def derive_fingerprint(
    *,
    master_key: bytes,
    tenant_id: UUID,
    subject_external_ref: str,
    model_scope: str | None = None,
) -> DerivedFingerprint:
    """Derive a stable pseudonymous employee fingerprint key.

    - Different tenants produce unrelated fingerprints.
    - Different employees produce unrelated fingerprints.
    - The same employee reproduces the same key.
    - An optional ``model_scope`` derives a separate subkey.
    - The external reference is never exposed.
    """
    tenant_secret = derive_tenant_secret(master_key=master_key, tenant_id=tenant_id)
    subject_tag = derive_subject_tag(
        tenant_secret=tenant_secret, subject_external_ref=subject_external_ref
    )
    employee_key = derive_key_from_subject_tag(
        tenant_secret=tenant_secret, subject_tag=subject_tag
    )
    if model_scope:
        normalized = normalize_model_scope(model_scope)
        key = hkdf(
            employee_key,
            info=_MODEL_SCOPE_DOMAIN.encode() + normalized.encode("ascii"),
        )
    else:
        key = employee_key
    return DerivedFingerprint(subject_tag=subject_tag, key=key)


def expected_bit(fingerprint_key: bytes, opportunity_id: bytes) -> int:
    """Deterministic pseudorandom bit for an opportunity under a key."""
    message = _EXPECTED_BIT_DOMAIN + opportunity_id
    return pseudo_random_bit(fingerprint_key, message)


def is_valid_subject_tag(tag: str) -> bool:
    return len(tag) == _TAG_HEX_LEN and all(c in "0123456789abcdef" for c in tag)
