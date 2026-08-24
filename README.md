# TraceMark

**Model-agnostic, post-generation forensic watermarking for LLM text.**

TraceMark sits between an application and an LLM provider. It rewrites
completed natural-language output using a constrained set of linguistic and
typographic alternatives — `red, white and blue` ↔ `red, white, and blue`,
`do not` ↔ `don't`, straight vs curly quotes, and so on. The choice at each
opportunity is *not random*: it is decided cryptographically by a secret
fingerprint key bound to an organization → employee → optional model scope.

Later, an organization can ask:

> Does this text carry one of our fingerprints? If so, which subject wrote
> it, and how strong is the evidence?

TraceMark does **not** claim to detect arbitrary AI text. It claims only:

> This text statistically matches a TraceMark fingerprint associated with
> this organization and subject.

---

## Why this design

- **No logits.** TraceMark works on finished text, so it works with any
  provider — OpenAI, Anthropic, DeepSeek, local models — with no model access.
- **No metadata.** No hidden characters, HTML comments or embedded IDs. The
  fingerprint lives entirely in the *statistical pattern* of ordinary
  linguistic choices.
- **Pseudonymous.** Employee identifiers never appear in text. Each subject
  has a derived, unlinkable fingerprint key; the mapping lives only in your
  database.
- **Statistical, not magical.** Detection reports how much evidence supports
  an attribution and refuses to guess when there is too little.

---

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
2. Each employee gets a stable **pseudonymous tag** — never their email or id —
   from which a fingerprint key is derived.
3. An optional model scope (e.g. `anthropic`) derives a separate subkey, so
   the same employee writing via Claude has a different pattern than via GPT.
4. For every eligible linguistic opportunity the encoder computes
   `expected_bit = HMAC-SHA256(fingerprint_key, opportunity_id)` and picks
   variant 0 or 1 accordingly.
5. Detection finds the same opportunities, decodes the observed bits, and
   scores each candidate by how many bits match the expected pattern.

Under unwatermarked text, an unrelated candidate matches ~50% of the time. A
correctly watermarked document matches far more. Detection therefore ranks the
true subject far above chance.

---

## Quick start

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
git clone git@github.com:colesnic/trace-mark.git
cd trace-mark

uv python install 3.12
uv sync --group dev

# Configuration (optional; sensible development defaults are used if omitted)
cp .env.example .env
#   set TRACEMARK_MASTER_KEY=<base64 32 bytes>
#   set TRACEMARK_ADMIN_TOKEN=<secret>

uv run alembic upgrade head

uv run uvicorn tracemark.main:app --reload
```

Open http://127.0.0.1:8000 for the interactive demo UI, or use the API:

### Create a tenant, subject and credential

```bash
uv run tracemark tenant create "Acme Corp"
uv run tracemark subject create --tenant <tenant-id> --external-ref employee-98372
uv run tracemark subject credential --tenant <tenant-id> --subject <subject-id>
#   -> token=...   (shown once; only its hash is stored)
```

### Watermark

```http
POST /v1/watermark
Authorization: Bearer <credential token>

{
  "text": "The company reviewed revenue, expenses and liabilities.",
  "policy": "balanced",
  "model_scope": "anthropic"
}
```

```json
{
  "text": "The company reviewed revenue, expenses, and liabilities.",
  "watermarked": true,
  "opportunities_found": 3,
  "transformations_applied": 3,
  "subject_tag": "c9b383c4ad260486508602f97d49df02"
}
```

### Detect

```http
POST /v1/detect
Authorization: Bearer <admin token>

{ "text": "...", "tenant_id": "<tenant-id>", "policy": "balanced" }
```

```json
{
  "detected": true,
  "usable_opportunities": 42,
  "best_candidate": {
    "subject_tag": "c9b383c4ad260486508602f97d49df02",
    "matches": 38,
    "match_rate": 0.9048,
    "p_value": 1.0e-7,
    "adjusted_p_value": 2.0e-5,
    "evidence_score": 7.0
  },
  "runner_up": { "subject_tag": "...", "match_rate": 0.57 }
}
```

### LLM proxy

```http
POST /v1/chat/completions
Authorization: Bearer <credential token>

{ "model": "deepseek/deepseek-chat",
  "messages": [{"role": "user", "content": "Summarize the report."}],
  "stream": false }
```

Only plain natural-language assistant content is watermarked. JSON mode, tool
calls and code-dominated output are passed through untouched. Streaming is
explicitly unsupported in V1 (`stream=true` returns a clear error).

---

## CLI

```bash
uv run tracemark watermark  --subject <id> --policy balanced --text "..."
uv run tracemark detect     --tenant <id> --file sample.txt
uv run tracemark benchmark
uv run tracemark tenant create "Acme Corp"
uv run tracemark subject create --tenant <id> --external-ref employee-123
```

`tracemark benchmark` runs the full local benchmark (no external API calls)
and writes `benchmarks/results/report.md`.

---

## Tests, linting, type checks

```bash
uv run pytest          # 150+ unit, integration and property-based tests
uv run ruff check .
uv run mypy src
```

CI runs all three on every push/PR (no API keys required).

---

## Benchmarks (honest numbers)

Measured on an Apple M3 Pro (see `benchmarks/results/report.md`):

| Attack | mean match rate | detected fraction |
|--------|-----------------|-------------------|
| original | 0.99 | 0.75 |
| 10–30% sentence deletion | 0.99 | 0.50–0.75 |
| typography normalization | 0.97 | 0.75 |
| sentence reorder / whitespace | 0.99 | 0.75 |
| contraction normalization | 0.69 | 0.00 |
| serial-comma normalization | 0.79 | 0.00 |
| lowercase | 0.61 | 0.00 |

Normalization attacks that expand contractions or strip serial commas
destroy those specific channels — this is honest: an adversary who
normalizes the text removes the signal. Deletion and reordering barely hurt
because opportunity identities are computed from *sentence-local* canonical
context.

Latency on the same machine: **~10 ms @ 100 words, ~44 ms @ 500 words,
~88 ms @ 1,000 words** for watermark or detect.

---

## Limitations (please read)

TraceMark **cannot** detect arbitrary use of ChatGPT or Claude.

- Text must have originally passed through TraceMark for a TraceMark
  fingerprint to exist.
- Heavy rewriting, translation, or normalization of every watermark channel
  can destroy the signal.
- Short documents may not contain enough opportunities for reliable
  attribution. TraceMark returns `insufficient_evidence` instead of guessing.
- Detection is **statistical evidence, not absolute proof.** It cannot
  attribute a document to a person with certainty, and a document's author is
  only ever as certain as the evidence.
- Employees who route around the gateway entirely are invisible.
- Anyone with access to the master keys can forge or read fingerprints;
  malicious insiders are out of scope (see `docs/threat-model.md`).

---

## Development setup

```bash
uv python install 3.12
uv sync --group dev        # production deps + pytest/hypothesis/mypy/ruff
uv run alembic upgrade head
uv run uvicorn tracemark.main:app --reload
```

PostgreSQL is supported for production (`docker-compose.yml` starts one):

```bash
docker compose up -d postgres
TRACEMARK_DATABASE_URL=postgresql+asyncpg://tracemark:tracemark@localhost:5432/tracemark \
  uv run alembic upgrade head
```

## Documentation

- `docs/architecture.md` — component design, data flow, Mermaid diagrams
- `docs/threat-model.md` — what TraceMark does and does not protect against
- `docs/phase4-report.md` — the core fingerprinting experiment and results
- `docs/engineering-report.md` — full engineering report: risks, limitations,
  benchmarks, results, and the rationale behind every architectural decision
- `docs/research-v2-report.md` — V2 research sprint: real-corpus validation
  (Enron/HC3/Newsgroups), statistical null calibration, candidate-scale and
  length thresholds, commercial viability assessment
- `docs/api.md` — full API reference

## V2 research (2026)

The V2 research sprint measured TraceMark against 415k+ real emails, 85k HC3
QA answers and 17k newsgroup posts. Headline findings are in
`docs/research-v2-report.md`; raw machine-readable results live in
`benchmarks/results/v2/`. Re-run everything with:

```bash
uv run python -m tracemark.benchmarks.scripts.fetch_corpora --corpus enron
uv run python -m tracemark.benchmarks.scripts.prepare_corpora --all
uv run python -m tracemark.benchmarks.report_v2
```

## License

Apache-2.0.
