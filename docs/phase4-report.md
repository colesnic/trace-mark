# Phase 4 — Core Experiment Report

Date: 2026-08-24 · Machine: Apple M3 Pro, 18 GB, macOS · Python 3.12

## Experiment

1. Build a 441-word business document rich in transformable linguistic
   opportunities (lists, contractions, quotes, ellipses, em dashes).
2. Watermark it with employee **Alice**'s fingerprint (balanced policy).
3. Detect among **Alice**, **Bob**, and 5 random synthetic fingerprints.

## Results

- **Tests passed:** 122 (`pytest`), ruff clean, mypy clean.
- **Rules implemented:** quotes, apostrophes, ellipsis, dash_style,
  serial_comma, contractions, abbreviations, complementizer_that, markdown.
- **Example original:**
  > The committee reviewed the annual report, the budget and the forecast.
- **Example watermarked:**
  > We do not believe the new policy is fair, and we will not accept it.
  > The manager said… "This is a great opportunity, isn't it?" …
  > (Multiple list conjunctions, contractions and ellipses flipped to Alice's
  > deterministic bit pattern.)
- **Usable opportunities:** 56

| Candidate | Matches | Match rate | raw p       | adjusted p | evidence |
|-----------|---------|-----------|-------------|-----------|----------|
| **Alice** | 56      | 1.000     | 1.39e-17    | 9.71e-17   | **16.0** |
| rand-1    | 36      | 0.643     | 2.20e-02    | 1.54e-01   | 0.81     |
| rand-3    | 32      | 0.571     | 1.75e-01    | 1.00e+00   | -0.00    |
| rand-4    | 28      | 0.500     | 5.53e-01    | 1.00e+00   | -0.00    |
| rand-0    | 26      | 0.464     | 7.48e-01    | 1.00e+00   | -0.00    |
| rand-2    | 24      | 0.429     | 8.86e-01    | 1.00e+00   | -0.00    |
| Bob       | 22      | 0.393     | 9.59e-01    | 1.00e+00   | -0.00    |

**Detection:** `detected=True`, best candidate Alice, reason `detected`.

Alice's match rate is 100%; every unrelated candidate sits near chance
(~43–64%) and none passes multiple-testing correction. The evidence gap
between Alice and the runner-up is 15.2, far above the separation threshold.

## Latency (per operation, 441 words, ~56 opportunities)

| Operation | p50   | p95   |
|-----------|-------|-------|
| Watermark | 41 ms | 42 ms |
| Detect    | 43 ms | 43 ms |

Both are comfortably below the sub-100 ms goal for ordinary business
responses on this machine.

## Problems / limitations discovered

1. **Occurrence-index ordering bug:** the contractions rule originally
   assigned occurrence indices in scan order (contracted forms before
   expanded forms) rather than text order, which silently broke
   encode/detect ID agreement for mixed-form sentences. Fixed by sorting
   matches by position before counting. This was caught by the detection
   integration tests — exactly the kind of encode/detect asymmetry the
   canonical-context design is meant to prevent.
2. **Document-wide vs sentence-local token indices:** the serial-comma rule
   initially mixed index spaces, missing opportunities in sentences after
   the first. Now fully doc-wide.
3. **Ellipsis asymmetry:** the rule initially only found `...`, not `…`,
   breaking decode of already-ellipsized text. Both forms are now matched.
4. **Conservative serial-comma rule:** proper-noun lists (e.g. "Alice, Bob
   and Carol") are deliberately rejected to avoid appositive false
   positives. This reduces opportunity density in name-heavy documents.
5. **Opportunity density** (~1 per 8 words here) is the fundamental limit:
   short documents (< 20 opportunities) are correctly reported as
   `insufficient_evidence` rather than attributed.
6. **Nested spans** (e.g. an apostrophe inside a quoted span) are dropped by
   overlap resolution; conservative but slightly reduces yield.
