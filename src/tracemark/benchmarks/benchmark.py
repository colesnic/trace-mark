"""Basic attribution benchmark — the core proof that fingerprints survive.

Expanded in the Phase 8 benchmark suite; this module must never require
external LLM API calls.
"""

from __future__ import annotations

import random
from uuid import UUID

from tracemark.crypto.fingerprint import derive_fingerprint
from tracemark.watermark.detector import (
    FingerprintCandidate,
    detect_fingerprint,
)
from tracemark.watermark.engine import apply_watermark
from tracemark.watermark.policy import WatermarkPolicy

TENANT = UUID("11111111-1111-1111-1111-111111111111")
MASTER = b"\x42" * 32

_SENTENCES = [
    "The committee reviewed the annual report, the budget and the forecast.",
    "We do not believe the new policy is fair, and we will not accept it.",
    "The manager said... \u201cThis is a great opportunity, isn\u2019t it?\u201d",
    "It was a red, white and blue flag \u2014 it really was a sight to behold.",
    "The plan covers revenue, expenses and liabilities for the coming year.",
    "We do not think the deadline is realistic, and we cannot meet it.",
    "The report included sales, marketing and operations data.",
    "She was tired, hungry and frustrated after the long meeting.",
    "The board will not approve the merger, and it will not reverse course.",
    "Our system supports Linux, macOS and Windows without issue.",
    "The team analyzed cost, quality and timing trade-offs.",
    "We do not expect growth this quarter, and we will not raise guidance.",
    "The flag had red, white and blue stripes.",
    "It was a difficult, complex and risky decision \u2014 we knew it.",
    "The paper reviews methods, results and limitations.",
    "They were not ready for the launch, and they did not have a backup.",
    "The proposal includes scope, schedule and budget.",
    "We do not see a path forward, and we will not pretend otherwise.",
    "The menu offered soup, salad and sandwiches for lunch.",
]


def run_benchmark() -> str:
    """Run a synthetic Alice/Bob/random attribution benchmark and report."""
    random.seed(7)
    alice = derive_fingerprint(master_key=MASTER, tenant_id=TENANT, subject_external_ref="alice")
    bob = derive_fingerprint(master_key=MASTER, tenant_id=TENANT, subject_external_ref="bob")

    text = " ".join(_SENTENCES) * 2
    policy = WatermarkPolicy.from_name("balanced")

    result = apply_watermark(text=text, fingerprint_key=alice.key, policy=policy)

    candidates: list[FingerprintCandidate] = [
        FingerprintCandidate(alice.subject_tag, None, alice.key),
        FingerprintCandidate(bob.subject_tag, None, bob.key),
    ]
    for i in range(5):
        candidates.append(FingerprintCandidate(f"rand-{i}", None, random.randbytes(32)))

    det = detect_fingerprint(text=result.text, candidates=candidates, policy=policy)

    alice_row = next(c for c in det.scores if c.subject_tag == alice.subject_tag)
    bob_row = next(c for c in det.scores if c.subject_tag == bob.subject_tag)
    if det.best_candidate is None:
        best_row = det.scores[0]
    else:
        best_row = next(
            c for c in det.scores if c.subject_tag == det.best_candidate.subject_tag
        )

    lines = [
        "TraceMark attribution benchmark",
        "===============================",
        f"words: {len(text.split())}",
        f"opportunities found: {result.opportunities_found}",
        f"transformations applied: {result.transformations_applied}",
        "",
        f"correct candidate (Alice): matches={alice_row.matches:3} "
        f"rate={alice_row.match_rate:.3f} adj_p={alice_row.adjusted_p_value:.2e} "
        f"evidence={alice_row.evidence_score:.1f}",
        f"unrelated candidate (Bob): matches={bob_row.matches:3} "
        f"rate={bob_row.match_rate:.3f} adj_p={bob_row.adjusted_p_value:.2e}",
        f"best overall:                 {best_row.subject_tag} rate={best_row.match_rate:.3f} "
        f"evidence={best_row.evidence_score:.1f}",
        f"detected={det.detected} reason={det.reason}",
    ]
    ok = det.detected and best_row.subject_tag == alice.subject_tag
    lines.append("")
    lines.append("RESULT: " + ("PASS" if ok else "FAIL"))
    return "\n".join(lines)
