from __future__ import annotations

import os
from uuid import UUID

import pytest

# Isolate tests from any on-disk database: use a shared in-memory SQLite.
os.environ["TRACEMARK_DATABASE_URL"] = (
    "sqlite+aiosqlite:///file:tracemark_test?mode=memory&cache=shared&uri=true"
)

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
