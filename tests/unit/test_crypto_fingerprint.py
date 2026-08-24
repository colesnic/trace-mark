from uuid import UUID

from tracemark.crypto.fingerprint import (
    derive_fingerprint,
    derive_subject_tag,
    derive_tenant_secret,
    expected_bit,
    is_valid_subject_tag,
    normalize_model_scope,
)

MASTER = b"\x42" * 32
TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = UUID("22222222-2222-2222-2222-222222222222")


def test_same_tenant_and_employee_yields_same_key() -> None:
    fp1 = derive_fingerprint(
        master_key=MASTER, tenant_id=TENANT_A, subject_external_ref="employee-1"
    )
    fp2 = derive_fingerprint(
        master_key=MASTER, tenant_id=TENANT_A, subject_external_ref="employee-1"
    )
    assert fp1.key == fp2.key
    assert fp1.subject_tag == fp2.subject_tag


def test_different_employee_yields_different_key() -> None:
    a = derive_fingerprint(
        master_key=MASTER, tenant_id=TENANT_A, subject_external_ref="alice"
    )
    b = derive_fingerprint(
        master_key=MASTER, tenant_id=TENANT_A, subject_external_ref="bob"
    )
    assert a.key != b.key
    assert a.subject_tag != b.subject_tag


def test_different_tenant_yields_different_key() -> None:
    a = derive_fingerprint(
        master_key=MASTER, tenant_id=TENANT_A, subject_external_ref="employee-1"
    )
    b = derive_fingerprint(
        master_key=MASTER, tenant_id=TENANT_B, subject_external_ref="employee-1"
    )
    assert a.key != b.key
    assert a.subject_tag != b.subject_tag


def test_different_tenant_tags_do_not_leak_identity() -> None:
    a = derive_fingerprint(
        master_key=MASTER, tenant_id=TENANT_A, subject_external_ref="alice@example.com"
    )
    b = derive_fingerprint(
        master_key=MASTER, tenant_id=TENANT_B, subject_external_ref="alice@example.com"
    )
    assert a.subject_tag != b.subject_tag
    assert "alice" not in a.subject_tag


def test_same_employee_different_model_scope_yields_different_key() -> None:
    base = derive_fingerprint(
        master_key=MASTER, tenant_id=TENANT_A, subject_external_ref="alice"
    )
    openai = derive_fingerprint(
        master_key=MASTER,
        tenant_id=TENANT_A,
        subject_external_ref="alice",
        model_scope="openai",
    )
    anthropic = derive_fingerprint(
        master_key=MASTER,
        tenant_id=TENANT_A,
        subject_external_ref="alice",
        model_scope="anthropic",
    )
    assert base.key != openai.key
    assert openai.key != anthropic.key


def test_no_employee_identity_in_key_metadata() -> None:
    fp = derive_fingerprint(
        master_key=MASTER,
        tenant_id=TENANT_A,
        subject_external_ref="employee-98372",
        model_scope="anthropic",
    )
    assert "employee-98372" not in fp.subject_tag
    assert "98372" not in fp.subject_tag


def test_expected_bit_deterministic() -> None:
    key = b"\x11" * 32
    ident = b"opportunity/1"
    assert expected_bit(key, ident) == expected_bit(key, ident)
    assert expected_bit(key, ident) in (0, 1)


def test_expected_bit_differs_across_keys_and_ids() -> None:
    key_a = b"\x11" * 32
    key_b = b"\x22" * 32
    id_1 = b"opp/1"
    id_2 = b"opp/2"
    bits = {
        expected_bit(key_a, id_1),
        expected_bit(key_a, id_2),
        expected_bit(key_b, id_1),
        expected_bit(key_b, id_2),
    }
    # Over a full byte the sequence of four bits should rarely all collide.
    assert len(bits) > 1


def test_subject_tag_is_hex_pseudonym() -> None:
    tag = derive_subject_tag(
        tenant_secret=derive_tenant_secret(master_key=MASTER, tenant_id=TENANT_A),
        subject_external_ref="employee-98372",
    )
    assert is_valid_subject_tag(tag)


def test_normalize_model_scope() -> None:
    assert normalize_model_scope("  OpenAI  ") == "openai"
    assert normalize_model_scope("DeepSeek-V4-Flash") == "deepseek-v4-flash"
    assert normalize_model_scope("Anthropic / claude") == "anthropic-claude"


def test_fingerprint_key_length() -> None:
    fp = derive_fingerprint(
        master_key=MASTER, tenant_id=TENANT_A, subject_external_ref="alice"
    )
    assert len(fp.key) == 32


def test_master_key_change_changes_everything() -> None:
    a = derive_fingerprint(
        master_key=b"\x01" * 32, tenant_id=TENANT_A, subject_external_ref="alice"
    )
    b = derive_fingerprint(
        master_key=b"\x02" * 32, tenant_id=TENANT_A, subject_external_ref="alice"
    )
    assert a.key != b.key
    assert a.subject_tag != b.subject_tag
