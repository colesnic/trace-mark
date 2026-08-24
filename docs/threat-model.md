# TraceMark threat model

## What TraceMark protects against

TraceMark is designed for the scenario where text **genuinely passes through
the gateway** and later needs forensic attribution within an organization:

- **Metadata-stripping copy/paste.** Pasting a chat response into an email or
  document strips invisible metadata and authorship fields. The linguistic
  fingerprint survives because it is embedded in the text itself.
- **Partial document reuse.** Copying a few paragraphs out of a longer
  watermarked document preserves sentence-local opportunities in the copied
  region.
- **Ordinary editing.** Deleting sentences, reordering paragraphs, or
  adjusting whitespace barely affects the fingerprint (see the benchmark
  results), because opportunity identities derive from sentence-local
  canonical context rather than document offsets.
- **Loss of immediate gateway logs.** Even if the gateway's audit logs are
  lost or the response was saved elsewhere, the fingerprint can still be
  matched against subject keys later.
- **After-the-fact attribution.** A document produced last month can be
  tested against today's candidate list without any prior state.

### Threat-relevant property: pseudonymity

Subject fingerprint keys are derived, not literal identities. An employee's
name or email never appears in watermarked text. Even if an attacker
recovers a fingerprint key, the pseudonymous tag gives them nothing directly;
the tag → employee mapping lives in the organization's database.

## What TraceMark does NOT inherently solve

Be explicit about these. None of the following are guarantees:

- **Employees bypassing TraceMark entirely.** If an employee calls the LLM
  provider directly, there is no fingerprint and nothing to detect. TraceMark
  only helps when the gateway is the *enforced* path for generation.
- **Heavy adversarial paraphrasing.** An LLM (or human) asked to rewrite
  the text into completely different words will destroy the signal. TraceMark
  is *not* robust to unrestricted paraphrase. The benchmark reports survival
  honestly; heavy paraphrase is not even claimed.
- **Complete retyping / translation round-trips.** Translating the text to
  another language and back removes essentially all the specific linguistic
  choices the fingerprint relies on.
- **Normalization of all watermark channels.** An adversary who knows the
  rules can systematically expand contractions, remove serial commas, and
  normalize typography. This destroys those channels. TraceMark cannot detect
  text whose watermark channels have all been normalized away.
- **Zero-knowledge or unknown-text watermarking.** TraceMark can only say
  whether text matches *known* candidate fingerprints for *your* subjects.
  It cannot watermark text that was never processed, and it cannot identify
  text written by people outside your organization.
- **Malicious insiders with access to secret keys.** Anyone holding the
  master key or a subject's fingerprint key can forge text that attributes
  to that subject, or strip a known key's pattern. Key custody is a
  separate, first-class security problem.
- **Deterministic author identification.** Statistical attribution is
  probabilistic. It cannot prove authorship; it reports evidence strength.
  A short or heavily edited document may legitimately be unattributeable,
  and TraceMark will say so (`insufficient_evidence`).

## Privacy considerations for employee-level fingerprints

- **Pseudonymous by design.** Only a derived tag is exposed in the database
  and in detection output; the tag-to-employee mapping is the organization's
  own lookup table.
- **Detection output should be authorization-gated.** The API returns the
  pseudonymous tag by default; mapping it to an employee identity should be
  restricted to authorized administrators. Never return a raw external
  reference (`employee-98372`) to unauthenticated callers.
- **Audit hashes only.** By default TraceMark stores only hashes of prompts
  and outputs, never raw content (raw retention is opt-in and
  development-only).
- **Statistical side channels.** A strong fingerprint is a strong signal.
  An organization that can detect fingerprints can also notice *which*
  employees produced which documents — which is exactly the intended use, but
  should be governed by policy, not left implicit.

## Key-handling notes

- The master key is read from environment configuration and never stored in
  the database. The abstraction is designed so a cloud KMS can later supply
  the root secret without changing the model layer.
- API credentials store only SHA-256 hashes of tokens. Raw tokens are shown
  exactly once at creation.
- Secrets must never be logged. TraceMark's structured logs carry request
  IDs, tenant IDs, pseudonymous tags, provider/model, latency and counts —
  never keys, tokens, or raw content.
