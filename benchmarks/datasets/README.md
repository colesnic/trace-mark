# Public benchmark datasets

TraceMark V2 uses public corpora to validate the watermark at realistic
scale. **Raw data is never committed to git**; it lives under the
gitignored `.data/` directory. Only aggregate statistics, anonymized
identifiers and small synthetic fixtures are committed.

## Sources

| Corpus | Contents | Use in TraceMark | License / usage notes |
|--------|----------|------------------|------------------------|
| **Enron** (CMU, 2015) | ~500k real business emails, ~150 employees | Author-style bias, opportunity density, realistic enterprise text, repeated-author analysis | Public research corpus (CMU). **Privacy-sensitive**: treat as confidential, never send to external LLMs, use anonymized author ids in results. |
| **HC3** (Hello-SimpleAI) | Human vs ChatGPT answers across finance, medicine, open_qa, reddit_eli5, wiki_csai | Compare watermark statistics on human vs machine source text | Public HF dataset. Attribution required per HF terms. |
| **M4** (shotan23) | Multi-generator, multi-domain, multi-lingual machine text | Machine-text density/calibration by generator | Gated on HF; ingests a local mirror when present. |
| **20 Newsgroups** | ~20k informal human posts, many authors/topics | Informal human writing, author variety | Standard public dataset (qwone.com). |
| **synthetic** | Deterministic generated docs | Unit tests, CI, null cross-checks, no download | TraceMark-generated; see `corpora/synthetic.py`. |

## Provenance

| Corpus | Source URL | Version | Fetched |
|--------|-----------|---------|---------|
| Enron | https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz | enron_mail_20150507 | 2026-08-24 |
| HC3 | https://huggingface.co/datasets/Hello-SimpleAI/HC3 | main (jsonl) | 2026-08-24 |
| M4 | https://huggingface.co/datasets/shotan23/M4-Machine-Generated-Text | gated | n/a |
| 20 Newsgroups | https://qwone.com/~jason/20Newsgroups/20news-bydate.tar.gz | bydate | 2026-08-24 |

## Layout

```
.data/
  raw/
    enron/enron_mail_20150507.tar.gz
    hc3/hc3_<domain>.jsonl
    newsgroups/20news-bydate.tar.gz
  processed/
    <corpus>.jsonl      # cleaned, anonymized CorpusDocument records
```

## Fetching and preparing

```bash
python -m tracemark.benchmarks.scripts.fetch_corpora --corpus enron
python -m tracemark.benchmarks.scripts.prepare_corpora --all
```

Checksums: Enron tarball MD5 `SHA256` is computed at prepare time and stored
in the corpus metadata when available.
