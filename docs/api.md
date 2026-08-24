# TraceMark API

Base URL: `http://127.0.0.1:8000`. All endpoints except `/` and `/healthz`
require a Bearer token.

Interactive docs: http://127.0.0.1:8000/docs (OpenAPI).

---

## POST /v1/watermark

Watermark a finished text with the fingerprint bound to the caller's
credential. The subject identity comes from the token — never from the body.

Headers: `Authorization: Bearer <subject credential token>`

```json
{
  "text": "The committee reviewed the annual report, the budget and the forecast.",
  "policy": "balanced",
  "model_scope": "anthropic"
}
```

`policy`: `strict` | `balanced` | `experimental`. `model_scope` is optional.

```json
{
  "text": "The committee reviewed the annual report, the budget and the forecast.",
  "watermarked": true,
  "opportunities_found": 1,
  "transformations_applied": 1,
  "subject_tag": "c9b383c4ad260486508602f97d49df02",
  "transformations": [
    {
      "rule_id": "serial_comma",
      "original": " and",
      "replacement": ", and",
      "bit": 1,
      "start": 47,
      "end": 51
    }
  ]
}
```

`transformations` is a debug view of exactly what changed. Secret key
material is never returned.

---

## POST /v1/detect

Test suspect text against every active subject of a tenant.

Headers: `Authorization: Bearer <admin token>`

```json
{
  "text": "…suspect text…",
  "tenant_id": "183d5ed3-ce0d-4d8a-b9aa-14254be96dd4",
  "policy": "balanced"
}
```

```json
{
  "detected": true,
  "usable_opportunities": 42,
  "best_candidate": {
    "subject_tag": "c9b383c4ad260486508602f97d49df02",
    "model_scope": null,
    "subject": { "id": "…", "external_ref": "employee-98372" },
    "opportunities": 42,
    "matches": 38,
    "match_rate": 0.9048,
    "p_value": 1.0e-7,
    "adjusted_p_value": 2.0e-5,
    "evidence_score": 7.0
  },
  "runner_up": { "subject_tag": "…", "match_rate": 0.57 },
  "candidates_tested": 7,
  "reason": "detected"
}
```

`subject` (the identity mapping) is only returned to authorized admin
callers. When evidence is insufficient the endpoint returns
`detected: false` with `reason: "insufficient_evidence"` rather than guessing.

---

## POST /v1/chat/completions

OpenAI-compatible LLM proxy. The model id routes by prefix:
`openai/…`, `deepseek/…`, `anthropic/…`.

Headers: `Authorization: Bearer <subject credential token>`

```json
{
  "model": "deepseek/deepseek-chat",
  "messages": [{ "role": "user", "content": "Summarize the report." }],
  "stream": false
}
```

- Plain assistant natural-language content is watermarked.
- JSON mode (`response_format.type = json_object`), tool calls and
  code-dominated responses are passed through unmodified.
- `stream: true` returns HTTP 400 with an explicit "not supported" message.

---

## Admin

All admin endpoints require `Authorization: Bearer <admin token>`
(development default `dev-admin-token`).

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/admin/tenants` | `{"name": "Acme Corp"}` → tenant |
| GET | `/v1/admin/tenants/{tenant_id}` | tenant details |
| POST | `/v1/admin/tenants/{tenant_id}/subjects` | `{"external_ref": "employee-1"}` → subject |
| GET | `/v1/admin/tenants/{tenant_id}/subjects` | list subjects |
| POST | `/v1/admin/tenants/{tenant_id}/subjects/{subject_id}/credentials` | create credential, returns `{"token": "…"}` once |

---

## Error responses

- `401` — missing/invalid bearer token
- `404` — unknown tenant/subject
- `422` — validation error or unknown policy
- `400` — streaming not supported (proxy)
- `502` — upstream LLM provider failure (proxy)

## Errors you will NOT see

TraceMark never returns an employee attribution with `detected: true` for a
document with too few opportunities. It returns `insufficient_evidence`
instead.
