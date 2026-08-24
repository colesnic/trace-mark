# TraceMark

**Model-agnostic, post-generation forensic watermarking for LLM text.**

TraceMark sits between an application and an LLM provider. It rewrites
completed natural-language output using a constrained set of linguistic and
typographic alternatives — `red, white and blue` ↔ `red, white, and blue`,
`do not` ↔ `don't`, straight vs curly quotes, and so on. The choice at each
opportunity is decided cryptographically by a secret fingerprint key bound to
an organization → employee → optional model scope.

TraceMark does **not** claim to detect arbitrary AI text. It claims only that
a document statistically matches a TraceMark fingerprint associated with a
specific organization and subject — and it refuses to guess when there isn't
enough evidence.

---

## Why this design

TraceMark operates after generation, so it doesn't require logits or changes
to the model provider. Employee identity is represented by a derived key
rather than embedded metadata, and attribution comes from aggregate bit
matches rather than a recoverable ID. Detection reports how much evidence
supports an attribution and returns `insufficient_evidence` when there is too
little.

## Architecture

```
Client ──► TraceMark Gateway ──► OpenAI / Anthropic / DeepSeek
              │                        │
              └────────── model response
              │
              ▼
        Watermark engine
        (linguistic rules + keyed bits)
              │
              ▼
        Watermarked response ──► Client
```

Components (see `docs/architecture.md`):

| Component | Responsibility |
|-----------|----------------|
| `crypto/` | HMAC/HKDF key derivation, pseudorandom bits |
| `watermark/` | rule registry, canonicalization, protection, encoder, detector, scoring |
| `providers/` | OpenAI-compatible and Anthropic adapters |
| `api/` | `/v1/watermark`, `/v1/detect`, `/v1/chat/completions`, admin, demo UI |
| `db/` | Tenant, Subject, ApiCredential, GenerationEvent (SQLite / Postgres) |

## How the fingerprint works

1. A master key (from your environment or KMS) derives a per-tenant secret.
2. Each employee gets a stable pseudonymous tag — never their email or id —
   from which a fingerprint key is derived.
3. An optional model scope (e.g. `anthropic`) derives a separate subkey, so
   the same employee writing via Claude has a different pattern than via GPT.
4. For every eligible linguistic opportunity the encoder computes
   `expected_bit = HMAC-SHA256(fingerprint_key, opportunity_id)` and picks
   variant 0 or 1 accordingly.
5. Detection finds the same opportunities, decodes the observed bits, and
   scores each candidate by how many bits match the expected pattern.

Under unwatermarked text, an unrelated candidate matches ~50% of the time. A
correctly watermarked document matches far more.

---

## Quick start

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
git clone git@github.com:colesnic/trace-mark.git
cd trace-mark

uv python install 3.12
uv sync --group dev

cp .env.example .env   # optional; development defaults work out of the box

uv run alembic upgrade head
uv run uvicorn tracemark.main:app --reload
```

Open http://127.0.0.1:8000 for the interactive demo UI.

CLI quick path:

```bash
uv run tracemark tenant create "Acme Corp"
uv run tracemark subject create --tenant <id> --external-ref employee-123
uv run tracemark watermark  --subject <id> --text "..."
uv run tracemark detect     --tenant <id> --file sample.txt
uv run tracemark benchmark
```

Full API examples (watermark / detect / proxy / admin): `docs/api.md`.

PostgreSQL for production (`docker-compose.yml`):

```bash
docker compose up -d postgres
TRACEMARK_DATABASE_URL=postgresql+asyncpg://tracemark:tracemark@localhost:5432/tracemark \
  uv run alembic upgrade head
```

## Tests, linting, type checks

```bash
uv run pytest          # 170+ unit, integration and property-based tests
uv run ruff check .
uv run mypy src
```

CI runs all three on every push/PR (no API keys required).

---

## Benchmarks

Measured on an Apple M3 Pro. Headline attack-survival numbers (synthetic V1
corpus):

| Attack | mean match rate | detected fraction |
|--------|-----------------|-------------------|
| original | 0.99 | 0.75 |
| 10–30% sentence deletion | 0.99 | 0.50–0.75 |
| typography normalization | 0.97 | 0.75 |
| sentence reorder / whitespace | 0.99 | 0.75 |
| contraction normalization | 0.69 | 0.00 |
| serial-comma normalization | 0.79 | 0.00 |
| lowercase | 0.61 | 0.00 |

Normalization attacks that expand contractions or strip serial commas remove
those channels. Deletion and reordering barely hurt because opportunity
identities are computed from sentence-local canonical context.

The V2 research sprint (518K+ real documents from Enron, HC3 and 20
Newsgroups) found real text is roughly 10× less watermarkable than synthetic
prose: ~1.3–2.0 opportunities per 100 words, so reliable attribution needs
~1,000–2,000-word documents. Full results: `docs/research-v2-report.md`.

Latency: **~10 ms @ 100 words, ~44 ms @ 500 words, ~88 ms @ 1,000 words** for
watermark or detect; ~0.3–0.65 s to score a document against 10,000
candidate fingerprints.

---

## Limitations

- Text must have originally passed through TraceMark for a TraceMark
  fingerprint to exist.
- Heavy rewriting, translation, or normalizing every watermark channel
  destroys the signal.
- Short documents may not contain enough opportunities for reliable
  attribution; TraceMark returns `insufficient_evidence` rather than guessing.
- Employees who route around the gateway are invisible.
- Anyone holding the master keys can forge or strip fingerprints; malicious
  insiders are out of scope (see `docs/threat-model.md`).

---

## Documentation

- `docs/architecture.md` — component design, data flow, Mermaid diagrams
- `docs/api.md` — full API reference
- `docs/threat-model.md` — what TraceMark does and does not protect against
- `docs/research-v2-report.md` — V2 research sprint: real-corpus validation,
  statistical null calibration, candidate-scale and length thresholds,
  commercial viability assessment
- `docs/engineering-report.md` — risks, limitations, benchmarks, and the
  rationale behind every architectural decision

## V2 research (2026)

Measured against 415,671 Enron emails, 85,431 HC3 QA answers and 17,429
newsgroup posts, with up to 10,000 candidate fingerprints. Re-run everything
with:

```bash
uv run python -m tracemark.benchmarks.scripts.fetch_corpora --corpus enron
uv run python -m tracemark.benchmarks.scripts.prepare_corpora --all
uv run python -m tracemark.benchmarks.report_v2
```

## License

Apache-2.0.
