from __future__ import annotations

from uuid import UUID

import pytest

from tracemark.crypto.fingerprint import derive_fingerprint
from tracemark.watermark.policy import WatermarkPolicy
from tracemark.watermark.rules.base import get_registry

TENANT = UUID("11111111-1111-1111-1111-111111111111")
MASTER_KEY = b"\x42" * 32


@pytest.fixture(scope="session")
def nlp():
    from tracemark.watermark.engine import get_nlp

    return get_nlp()


@pytest.fixture(scope="session")
def registry():
    return get_registry()


@pytest.fixture(scope="session")
def balanced_policy() -> WatermarkPolicy:
    return WatermarkPolicy.from_name("balanced")


@pytest.fixture(scope="session")
def strict_policy() -> WatermarkPolicy:
    return WatermarkPolicy.from_name("strict")


@pytest.fixture(scope="session")
def alice_key() -> bytes:
    return derive_fingerprint(
        master_key=MASTER_KEY, tenant_id=TENANT, subject_external_ref="alice"
    ).key


@pytest.fixture(scope="session")
def bob_key() -> bytes:
    return derive_fingerprint(
        master_key=MASTER_KEY, tenant_id=TENANT, subject_external_ref="bob"
    ).key
