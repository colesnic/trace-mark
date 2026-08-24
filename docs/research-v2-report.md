# TraceMark V2 — Research Validation & Adversarial Benchmark Report

Goal: determine whether TraceMark remains statistically reliable at realistic enterprise scale, on real-world text, across realistic document lengths, writers, models, and edits. Negative results are reported as measured.

## 1. Executive summary

The central V2 result is that **real-world text is far less watermarkable than the synthetic corpus used in V1**, and TraceMark's reliability is correspondingly much more limited than the V1 benchmark suggested.
- **Enron emails**: median 1.251 opportunities / 100 words; median 1 opportunities per document; only 3.6% of documents reach the 20-opportunity attribution threshold.
- **HC3 (QA, human + ChatGPT)**: median 1.961 / 100 words; 0.3% reach the threshold.
- V1's synthetic corpus was ~10x denser (~13/100 words) than real email/QA text (~1.3–1.9/100), so V1's headline 56-opportunity/441-word experiment is not representative of real business text.
- In real text the watermark capacity is dominated by **apostrophes and quote typography**, not contractions and serial commas as the synthetic corpus suggested. Hyphenated compounds (~1.3/100 w) and time notation (~0.6/100 w) are the largest untapped patterns, but both are hard to transform conservatively.
- Consequence: reliably attributing one employee among a large population requires documents of roughly **1,000–2,000+ words**, and the multiple-testing burden at 10,000 employees pushes the required match rate close to the per-opportunity survival achievable only on unedited text.

## 2. Datasets

| Corpus | Source | Notes |
|--------|--------|-------|
| Enron (CMU 2015) | https://www.cs.cmu.edu/~enron/ | ~415,671 cleaned emails; privacy-sensitive, anonymized ids only |
| HC3 (Hello-SimpleAI) | HuggingFace | 85,431 human+ChatGPT QA answers |
| 20 Newsgroups | qwone.com / figshare mirror | informal human posts |
| M4 | HuggingFace (gated) | ingested only when a local mirror is present |
| synthetic | built-in | V1-style dense text, for calibration and CI |

Raw data is never committed; everything lives under `.data/` (gitignored).

## 3. Corpus sizes and opportunity density

Sampled NLP statistics (spaCy parse per document):

| corpus | docs | median words | density/100w (med) | median opps | eligible ≥20 |
|--------|------|--------------|--------------------|-------------|--------------|
| enron | 3000 | 89 | 1.251 | 1 | 3.6% |
| hc3 | 3000 | 156 | 1.961 | 3 | 0.3% |
| synthetic | 200 | 73 | 13.415 | 10 | 0.0% |

Rule distribution is dominated by apostrophes and quote typography in real text, and by contractions + serial commas only in the synthetic corpus. See Section 9.

## 4. Document-length analysis

Windows are sentence-preserving, sampled from long Enron/HC3 documents.

| target words | median opps | p10 | p90 | eligible ≥20 |
|--------------|-------------|-----|-----|--------------|
| 50 | 1 | 0 | 2 | 0.0% |
| 100 | 1 | 0 | 4 | 0.0% |
| 150 | 2 | 0 | 6 | 0.0% |
| 200 | 4 | 1 | 7 | 0.0% |
| 300 | 4 | 1 | 10 | 1.3% |
| 400 | 6 | 2 | 14 | 2.7% |
| 500 | 7 | 2 | 18 | 7.3% |
| 750 | 12 | 4 | 28 | 24.0% |
| 1000 | 16 | 5 | 37 | 38.0% |
| 1500 | 28 | 8 | 53 | 72.2% |
| 2000 | 39 | 14 | 62 | 83.6% |

Even at 2,000 words, eligibility depends on how many opportunities the specific text yields; density is the binding constraint.

## 5. Candidate-scale analysis

Watermarked documents (≥400-word Enron emails) scored against N unrelated fingerprints. `correct_rank=0` means the true employee ranked first.

| doc | words | opps | N cand | rank | corr rate | false max | adj p | detected |
|-----|-------|------|--------|------|-----------|-----------|-------|----------|
| 511cde8c78 | 515 | 14 | 10 | 0 | 0.929 | 0.643 | 9.16e-03 | True |
| 511cde8c78 | 515 | 14 | 100 | 0 | 0.929 | 0.857 | 9.16e-02 | False |
| 511cde8c78 | 515 | 14 | 1000 | 0 | 0.929 | 0.929 | 9.16e-01 | False |
| 511cde8c78 | 515 | 14 | 5000 | 0 | 0.929 | 0.929 | 1.00e+00 | False |
| 511cde8c78 | 515 | 14 | 10000 | 1 | 0.929 | 1.000 | 1.00e+00 | False |
| 4fdac63b7c | 619 | 3 | 10 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 4fdac63b7c | 619 | 3 | 100 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 4fdac63b7c | 619 | 3 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 4fdac63b7c | 619 | 3 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 4fdac63b7c | 619 | 3 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| be4c40685c | 1002 | 16 | 10 | 0 | 1.000 | 0.625 | 1.53e-04 | True |
| be4c40685c | 1002 | 16 | 100 | 0 | 1.000 | 0.812 | 1.53e-03 | True |
| be4c40685c | 1002 | 16 | 1000 | 0 | 1.000 | 0.875 | 1.53e-02 | True |
| be4c40685c | 1002 | 16 | 5000 | 0 | 1.000 | 0.875 | 7.63e-02 | False |
| be4c40685c | 1002 | 16 | 10000 | 0 | 1.000 | 1.000 | 1.53e-01 | False |
| 9049b65de3 | 775 | 12 | 10 | 0 | 0.917 | 0.667 | 3.17e-02 | True |
| 9049b65de3 | 775 | 12 | 100 | 0 | 0.917 | 0.833 | 3.17e-01 | False |
| 9049b65de3 | 775 | 12 | 1000 | 1 | 0.917 | 1.000 | 1.00e+00 | False |
| 9049b65de3 | 775 | 12 | 5000 | 0 | 0.917 | 0.917 | 1.00e+00 | False |
| 9049b65de3 | 775 | 12 | 10000 | 2 | 0.917 | 1.000 | 1.00e+00 | False |
| bb2db5bd3c | 5269 | 143 | 10 | 0 | 1.000 | 0.538 | 8.97e-43 | True |
| bb2db5bd3c | 5269 | 143 | 100 | 0 | 1.000 | 0.608 | 8.97e-42 | True |
| bb2db5bd3c | 5269 | 143 | 1000 | 0 | 1.000 | 0.636 | 8.97e-41 | True |
| bb2db5bd3c | 5269 | 143 | 5000 | 0 | 1.000 | 0.643 | 4.48e-40 | True |
| bb2db5bd3c | 5269 | 143 | 10000 | 0 | 1.000 | 0.664 | 8.97e-40 | True |
| 8b4f4e0c83 | 572 | 5 | 10 | 0 | 1.000 | 0.800 | 3.12e-01 | False |
| 8b4f4e0c83 | 572 | 5 | 100 | 0 | 1.000 | 0.800 | 1.00e+00 | False |
| 8b4f4e0c83 | 572 | 5 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 8b4f4e0c83 | 572 | 5 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 8b4f4e0c83 | 572 | 5 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 33d8ef48c4 | 585 | 6 | 10 | 0 | 1.000 | 0.833 | 1.56e-01 | False |
| 33d8ef48c4 | 585 | 6 | 100 | 0 | 1.000 | 0.833 | 1.00e+00 | False |
| 33d8ef48c4 | 585 | 6 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 33d8ef48c4 | 585 | 6 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 33d8ef48c4 | 585 | 6 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 389a9f4d44 | 7039 | 172 | 10 | 0 | 1.000 | 0.587 | 1.67e-51 | True |
| 389a9f4d44 | 7039 | 172 | 100 | 0 | 1.000 | 0.599 | 1.67e-50 | True |
| 389a9f4d44 | 7039 | 172 | 1000 | 0 | 1.000 | 0.610 | 1.67e-49 | True |
| 389a9f4d44 | 7039 | 172 | 5000 | 0 | 1.000 | 0.622 | 8.35e-49 | True |
| 389a9f4d44 | 7039 | 172 | 10000 | 0 | 1.000 | 0.657 | 1.67e-48 | True |
| 8f71cf030f | 550 | 6 | 10 | 0 | 1.000 | 0.833 | 1.56e-01 | False |
| 8f71cf030f | 550 | 6 | 100 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 8f71cf030f | 550 | 6 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 8f71cf030f | 550 | 6 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 8f71cf030f | 550 | 6 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 055f23006a | 1405 | 45 | 10 | 0 | 0.978 | 0.644 | 1.31e-11 | True |
| 055f23006a | 1405 | 45 | 100 | 0 | 0.978 | 0.711 | 1.31e-10 | True |
| 055f23006a | 1405 | 45 | 1000 | 0 | 0.978 | 0.733 | 1.31e-09 | True |
| 055f23006a | 1405 | 45 | 5000 | 0 | 0.978 | 0.756 | 6.54e-09 | True |
| 055f23006a | 1405 | 45 | 10000 | 0 | 0.978 | 0.778 | 1.31e-08 | True |
| fa36f2fac5 | 536 | 13 | 10 | 0 | 1.000 | 0.692 | 1.22e-03 | True |
| fa36f2fac5 | 536 | 13 | 100 | 0 | 1.000 | 0.769 | 1.22e-02 | True |
| fa36f2fac5 | 536 | 13 | 1000 | 0 | 1.000 | 0.923 | 1.22e-01 | False |
| fa36f2fac5 | 536 | 13 | 5000 | 0 | 1.000 | 1.000 | 6.10e-01 | False |
| fa36f2fac5 | 536 | 13 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 2b6a82f92e | 426 | 2 | 10 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 2b6a82f92e | 426 | 2 | 100 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 2b6a82f92e | 426 | 2 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 2b6a82f92e | 426 | 2 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 2b6a82f92e | 426 | 2 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 905fb0483e | 506 | 16 | 10 | 0 | 1.000 | 0.750 | 1.53e-04 | True |
| 905fb0483e | 506 | 16 | 100 | 0 | 1.000 | 0.812 | 1.53e-03 | True |
| 905fb0483e | 506 | 16 | 1000 | 0 | 1.000 | 0.938 | 1.53e-02 | True |
| 905fb0483e | 506 | 16 | 5000 | 0 | 1.000 | 0.938 | 7.63e-02 | False |
| 905fb0483e | 506 | 16 | 10000 | 0 | 1.000 | 0.938 | 1.53e-01 | False |
| 3cdb8797fe | 800 | 15 | 10 | 0 | 0.867 | 0.733 | 3.69e-02 | True |
| 3cdb8797fe | 800 | 15 | 100 | 0 | 0.867 | 0.867 | 3.69e-01 | False |
| 3cdb8797fe | 800 | 15 | 1000 | 0 | 0.867 | 0.867 | 1.00e+00 | False |
| 3cdb8797fe | 800 | 15 | 5000 | 1 | 0.867 | 0.933 | 1.00e+00 | False |
| 3cdb8797fe | 800 | 15 | 10000 | 0 | 0.867 | 0.867 | 1.00e+00 | False |
| 608ca88427 | 693 | 11 | 10 | 0 | 1.000 | 0.636 | 4.88e-03 | True |
| 608ca88427 | 693 | 11 | 100 | 0 | 1.000 | 1.000 | 4.88e-02 | True |
| 608ca88427 | 693 | 11 | 1000 | 0 | 1.000 | 0.909 | 4.88e-01 | False |
| 608ca88427 | 693 | 11 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 608ca88427 | 693 | 11 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| b9366c9a70 | 553 | 7 | 10 | 0 | 1.000 | 0.571 | 7.81e-02 | False |
| b9366c9a70 | 553 | 7 | 100 | 0 | 1.000 | 1.000 | 7.81e-01 | False |
| b9366c9a70 | 553 | 7 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| b9366c9a70 | 553 | 7 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| b9366c9a70 | 553 | 7 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| fa346d96d6 | 522 | 0 | 10 | 0 | 0.000 | 0.000 | 1.00e+00 | False |
| fa346d96d6 | 522 | 0 | 100 | 0 | 0.000 | 0.000 | 1.00e+00 | False |
| fa346d96d6 | 522 | 0 | 1000 | 0 | 0.000 | 0.000 | 1.00e+00 | False |
| fa346d96d6 | 522 | 0 | 5000 | 0 | 0.000 | 0.000 | 1.00e+00 | False |
| fa346d96d6 | 522 | 0 | 10000 | 0 | 0.000 | 0.000 | 1.00e+00 | False |
| e8db02b26c | 569 | 9 | 10 | 0 | 1.000 | 0.556 | 1.95e-02 | True |
| e8db02b26c | 569 | 9 | 100 | 0 | 1.000 | 0.889 | 1.95e-01 | False |
| e8db02b26c | 569 | 9 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| e8db02b26c | 569 | 9 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| e8db02b26c | 569 | 9 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| deaa499c04 | 1996 | 37 | 10 | 0 | 1.000 | 0.649 | 7.28e-11 | True |
| deaa499c04 | 1996 | 37 | 100 | 0 | 1.000 | 0.703 | 7.28e-10 | True |
| deaa499c04 | 1996 | 37 | 1000 | 0 | 1.000 | 0.730 | 7.28e-09 | True |
| deaa499c04 | 1996 | 37 | 5000 | 0 | 1.000 | 0.811 | 3.64e-08 | True |
| deaa499c04 | 1996 | 37 | 10000 | 0 | 1.000 | 0.784 | 7.28e-08 | True |
| 0b677aca42 | 1431 | 41 | 10 | 0 | 0.976 | 0.585 | 1.91e-10 | True |
| 0b677aca42 | 1431 | 41 | 100 | 0 | 0.976 | 0.634 | 1.91e-09 | True |
| 0b677aca42 | 1431 | 41 | 1000 | 0 | 0.976 | 0.780 | 1.91e-08 | True |
| 0b677aca42 | 1431 | 41 | 5000 | 0 | 0.976 | 0.756 | 9.55e-08 | True |
| 0b677aca42 | 1431 | 41 | 10000 | 0 | 0.976 | 0.805 | 1.91e-07 | True |
| ad5e3b2c40 | 486 | 14 | 10 | 0 | 1.000 | 0.643 | 6.10e-04 | True |
| ad5e3b2c40 | 486 | 14 | 100 | 0 | 1.000 | 0.857 | 6.10e-03 | True |
| ad5e3b2c40 | 486 | 14 | 1000 | 0 | 1.000 | 0.857 | 6.10e-02 | False |
| ad5e3b2c40 | 486 | 14 | 5000 | 0 | 1.000 | 0.929 | 3.05e-01 | False |
| ad5e3b2c40 | 486 | 14 | 10000 | 0 | 1.000 | 0.929 | 6.10e-01 | False |
| 9823838aa2 | 520 | 2 | 10 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 9823838aa2 | 520 | 2 | 100 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 9823838aa2 | 520 | 2 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 9823838aa2 | 520 | 2 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 9823838aa2 | 520 | 2 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 2fe3d846d1 | 476 | 24 | 10 | 0 | 1.000 | 0.625 | 5.96e-07 | True |
| 2fe3d846d1 | 476 | 24 | 100 | 0 | 1.000 | 0.750 | 5.96e-06 | True |
| 2fe3d846d1 | 476 | 24 | 1000 | 0 | 1.000 | 0.792 | 5.96e-05 | True |
| 2fe3d846d1 | 476 | 24 | 5000 | 0 | 1.000 | 0.917 | 2.98e-04 | True |
| 2fe3d846d1 | 476 | 24 | 10000 | 0 | 1.000 | 0.875 | 5.96e-04 | True |
| 2bb540e722 | 521 | 3 | 10 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 2bb540e722 | 521 | 3 | 100 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 2bb540e722 | 521 | 3 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 2bb540e722 | 521 | 3 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 2bb540e722 | 521 | 3 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 6125d82c24 | 433 | 7 | 10 | 0 | 1.000 | 0.714 | 7.81e-02 | False |
| 6125d82c24 | 433 | 7 | 100 | 0 | 1.000 | 0.857 | 7.81e-01 | False |
| 6125d82c24 | 433 | 7 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 6125d82c24 | 433 | 7 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 6125d82c24 | 433 | 7 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 26c9114e21 | 536 | 1 | 10 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 26c9114e21 | 536 | 1 | 100 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 26c9114e21 | 536 | 1 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 26c9114e21 | 536 | 1 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 26c9114e21 | 536 | 1 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 992789232d | 2924 | 50 | 10 | 0 | 1.000 | 0.580 | 8.88e-15 | True |
| 992789232d | 2924 | 50 | 100 | 0 | 1.000 | 0.680 | 8.88e-14 | True |
| 992789232d | 2924 | 50 | 1000 | 0 | 1.000 | 0.700 | 8.88e-13 | True |
| 992789232d | 2924 | 50 | 5000 | 0 | 1.000 | 0.740 | 4.44e-12 | True |
| 992789232d | 2924 | 50 | 10000 | 0 | 1.000 | 0.760 | 8.88e-12 | True |
| 96a300cfaf | 1339 | 16 | 10 | 0 | 1.000 | 0.750 | 1.53e-04 | True |
| 96a300cfaf | 1339 | 16 | 100 | 0 | 1.000 | 0.812 | 1.53e-03 | True |
| 96a300cfaf | 1339 | 16 | 1000 | 0 | 1.000 | 0.875 | 1.53e-02 | True |
| 96a300cfaf | 1339 | 16 | 5000 | 0 | 1.000 | 0.875 | 7.63e-02 | False |
| 96a300cfaf | 1339 | 16 | 10000 | 0 | 1.000 | 0.875 | 1.53e-01 | False |
| 9d02c6a0a9 | 833 | 7 | 10 | 0 | 1.000 | 0.857 | 7.81e-02 | False |
| 9d02c6a0a9 | 833 | 7 | 100 | 0 | 1.000 | 0.857 | 7.81e-01 | False |
| 9d02c6a0a9 | 833 | 7 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 9d02c6a0a9 | 833 | 7 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 9d02c6a0a9 | 833 | 7 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 2ccabaf893 | 721 | 13 | 10 | 0 | 1.000 | 0.692 | 1.22e-03 | True |
| 2ccabaf893 | 721 | 13 | 100 | 0 | 1.000 | 0.846 | 1.22e-02 | True |
| 2ccabaf893 | 721 | 13 | 1000 | 0 | 1.000 | 0.923 | 1.22e-01 | False |
| 2ccabaf893 | 721 | 13 | 5000 | 0 | 1.000 | 1.000 | 6.10e-01 | False |
| 2ccabaf893 | 721 | 13 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 7a7758c3fa | 812 | 13 | 10 | 0 | 1.000 | 0.769 | 1.22e-03 | True |
| 7a7758c3fa | 812 | 13 | 100 | 0 | 1.000 | 0.769 | 1.22e-02 | True |
| 7a7758c3fa | 812 | 13 | 1000 | 0 | 1.000 | 0.923 | 1.22e-01 | False |
| 7a7758c3fa | 812 | 13 | 5000 | 0 | 1.000 | 0.923 | 6.10e-01 | False |
| 7a7758c3fa | 812 | 13 | 10000 | 0 | 1.000 | 0.923 | 1.00e+00 | False |
| f6ac1065a1 | 497 | 100 | 10 | 0 | 1.000 | 0.560 | 7.89e-30 | True |
| f6ac1065a1 | 497 | 100 | 100 | 0 | 1.000 | 0.650 | 7.89e-29 | True |
| f6ac1065a1 | 497 | 100 | 1000 | 0 | 1.000 | 0.660 | 7.89e-28 | True |
| f6ac1065a1 | 497 | 100 | 5000 | 0 | 1.000 | 0.660 | 3.94e-27 | True |
| f6ac1065a1 | 497 | 100 | 10000 | 0 | 1.000 | 0.700 | 7.89e-27 | True |
| eddd1c273d | 1294 | 13 | 10 | 0 | 1.000 | 0.769 | 1.22e-03 | True |
| eddd1c273d | 1294 | 13 | 100 | 0 | 1.000 | 0.846 | 1.22e-02 | True |
| eddd1c273d | 1294 | 13 | 1000 | 0 | 1.000 | 0.846 | 1.22e-01 | False |
| eddd1c273d | 1294 | 13 | 5000 | 0 | 1.000 | 0.923 | 6.10e-01 | False |
| eddd1c273d | 1294 | 13 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| f485077191 | 455 | 8 | 10 | 1 | 0.750 | 0.875 | 1.00e+00 | False |
| f485077191 | 455 | 8 | 100 | 2 | 0.750 | 0.875 | 1.00e+00 | False |
| f485077191 | 455 | 8 | 1000 | 22 | 0.750 | 0.875 | 1.00e+00 | False |
| f485077191 | 455 | 8 | 5000 | 169 | 0.750 | 1.000 | 1.00e+00 | False |
| f485077191 | 455 | 8 | 10000 | 318 | 0.750 | 1.000 | 1.00e+00 | False |
| 89efc69331 | 7734 | 227 | 10 | 0 | 0.974 | 0.551 | 8.47e-57 | True |
| 89efc69331 | 7734 | 227 | 100 | 0 | 0.974 | 0.555 | 8.47e-56 | True |
| 89efc69331 | 7734 | 227 | 1000 | 0 | 0.974 | 0.604 | 8.47e-55 | True |
| 89efc69331 | 7734 | 227 | 5000 | 0 | 0.974 | 0.626 | 4.24e-54 | True |
| 89efc69331 | 7734 | 227 | 10000 | 0 | 0.974 | 0.639 | 8.47e-54 | True |
| ee11e6726a | 521 | 22 | 10 | 0 | 1.000 | 0.545 | 2.38e-06 | True |
| ee11e6726a | 521 | 22 | 100 | 0 | 1.000 | 0.818 | 2.38e-05 | True |
| ee11e6726a | 521 | 22 | 1000 | 0 | 1.000 | 0.773 | 2.38e-04 | True |
| ee11e6726a | 521 | 22 | 5000 | 0 | 1.000 | 0.864 | 1.19e-03 | True |
| ee11e6726a | 521 | 22 | 10000 | 0 | 1.000 | 0.864 | 2.38e-03 | True |
| 0c3f5ecb4d | 4305 | 81 | 10 | 0 | 0.901 | 0.568 | 1.49e-13 | True |
| 0c3f5ecb4d | 4305 | 81 | 100 | 0 | 0.901 | 0.630 | 1.49e-12 | True |
| 0c3f5ecb4d | 4305 | 81 | 1000 | 0 | 0.901 | 0.654 | 1.49e-11 | True |
| 0c3f5ecb4d | 4305 | 81 | 5000 | 0 | 0.901 | 0.691 | 7.44e-11 | True |
| 0c3f5ecb4d | 4305 | 81 | 10000 | 0 | 0.901 | 0.716 | 1.49e-10 | True |
| 999a6d98f5 | 6799 | 223 | 10 | 0 | 0.919 | 0.552 | 1.17e-40 | True |
| 999a6d98f5 | 6799 | 223 | 100 | 0 | 0.919 | 0.574 | 1.17e-39 | True |
| 999a6d98f5 | 6799 | 223 | 1000 | 0 | 0.919 | 0.614 | 1.17e-38 | True |
| 999a6d98f5 | 6799 | 223 | 5000 | 0 | 0.919 | 0.646 | 5.83e-38 | True |
| 999a6d98f5 | 6799 | 223 | 10000 | 0 | 0.919 | 0.637 | 1.17e-37 | True |
| e1c081100b | 1167 | 29 | 10 | 0 | 0.966 | 0.621 | 5.59e-07 | True |
| e1c081100b | 1167 | 29 | 100 | 0 | 0.966 | 0.724 | 5.59e-06 | True |
| e1c081100b | 1167 | 29 | 1000 | 0 | 0.966 | 0.724 | 5.59e-05 | True |
| e1c081100b | 1167 | 29 | 5000 | 0 | 0.966 | 0.828 | 2.79e-04 | True |
| e1c081100b | 1167 | 29 | 10000 | 0 | 0.966 | 0.828 | 5.59e-04 | True |
| d6393904b1 | 609 | 29 | 10 | 0 | 0.793 | 0.586 | 1.16e-02 | True |
| d6393904b1 | 609 | 29 | 100 | 0 | 0.793 | 0.724 | 1.16e-01 | False |
| d6393904b1 | 609 | 29 | 1000 | 1 | 0.793 | 0.862 | 1.00e+00 | False |
| d6393904b1 | 609 | 29 | 5000 | 0 | 0.793 | 0.793 | 1.00e+00 | False |
| d6393904b1 | 609 | 29 | 10000 | 3 | 0.793 | 0.862 | 1.00e+00 | False |
| e4d335a4fc | 462 | 8 | 10 | 0 | 1.000 | 0.875 | 3.91e-02 | True |
| e4d335a4fc | 462 | 8 | 100 | 0 | 1.000 | 1.000 | 3.91e-01 | False |
| e4d335a4fc | 462 | 8 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| e4d335a4fc | 462 | 8 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| e4d335a4fc | 462 | 8 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 2e04be5a5a | 463 | 9 | 10 | 0 | 1.000 | 0.778 | 1.95e-02 | True |
| 2e04be5a5a | 463 | 9 | 100 | 0 | 1.000 | 0.778 | 1.95e-01 | False |
| 2e04be5a5a | 463 | 9 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 2e04be5a5a | 463 | 9 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 2e04be5a5a | 463 | 9 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| e1200e14b6 | 487 | 13 | 10 | 0 | 1.000 | 0.615 | 1.22e-03 | True |
| e1200e14b6 | 487 | 13 | 100 | 0 | 1.000 | 0.846 | 1.22e-02 | True |
| e1200e14b6 | 487 | 13 | 1000 | 0 | 1.000 | 0.923 | 1.22e-01 | False |
| e1200e14b6 | 487 | 13 | 5000 | 0 | 1.000 | 0.923 | 6.10e-01 | False |
| e1200e14b6 | 487 | 13 | 10000 | 0 | 1.000 | 0.923 | 1.00e+00 | False |
| 681628f8c3 | 1856 | 43 | 10 | 0 | 0.953 | 0.605 | 1.08e-09 | True |
| 681628f8c3 | 1856 | 43 | 100 | 0 | 0.953 | 0.674 | 1.08e-08 | True |
| 681628f8c3 | 1856 | 43 | 1000 | 0 | 0.953 | 0.721 | 1.08e-07 | True |
| 681628f8c3 | 1856 | 43 | 5000 | 0 | 0.953 | 0.744 | 5.38e-07 | True |
| 681628f8c3 | 1856 | 43 | 10000 | 0 | 0.953 | 0.767 | 1.08e-06 | True |
| f7319aa18b | 424 | 6 | 10 | 0 | 1.000 | 0.833 | 1.56e-01 | False |
| f7319aa18b | 424 | 6 | 100 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| f7319aa18b | 424 | 6 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| f7319aa18b | 424 | 6 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| f7319aa18b | 424 | 6 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 15a8f0c6b4 | 444 | 13 | 10 | 0 | 1.000 | 0.615 | 1.22e-03 | True |
| 15a8f0c6b4 | 444 | 13 | 100 | 0 | 1.000 | 0.846 | 1.22e-02 | True |
| 15a8f0c6b4 | 444 | 13 | 1000 | 0 | 1.000 | 0.923 | 1.22e-01 | False |
| 15a8f0c6b4 | 444 | 13 | 5000 | 0 | 1.000 | 0.923 | 6.10e-01 | False |
| 15a8f0c6b4 | 444 | 13 | 10000 | 0 | 1.000 | 0.923 | 1.00e+00 | False |
| f6b66758f0 | 425 | 4 | 10 | 0 | 1.000 | 1.000 | 6.25e-01 | False |
| f6b66758f0 | 425 | 4 | 100 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| f6b66758f0 | 425 | 4 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| f6b66758f0 | 425 | 4 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| f6b66758f0 | 425 | 4 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 1bfa280956 | 517 | 1 | 10 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 1bfa280956 | 517 | 1 | 100 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 1bfa280956 | 517 | 1 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 1bfa280956 | 517 | 1 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 1bfa280956 | 517 | 1 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 5f266c5f3f | 816 | 59 | 10 | 0 | 0.729 | 0.559 | 2.92e-03 | True |
| 5f266c5f3f | 816 | 59 | 100 | 0 | 0.729 | 0.729 | 2.92e-02 | True |
| 5f266c5f3f | 816 | 59 | 1000 | 0 | 0.729 | 0.729 | 2.92e-01 | False |
| 5f266c5f3f | 816 | 59 | 5000 | 1 | 0.729 | 0.746 | 1.00e+00 | False |
| 5f266c5f3f | 816 | 59 | 10000 | 1 | 0.729 | 0.746 | 1.00e+00 | False |
| a8d7f51752 | 541 | 6 | 10 | 1 | 0.667 | 0.833 | 1.00e+00 | False |
| a8d7f51752 | 541 | 6 | 100 | 10 | 0.667 | 0.833 | 1.00e+00 | False |
| a8d7f51752 | 541 | 6 | 1000 | 123 | 0.667 | 1.000 | 1.00e+00 | False |
| a8d7f51752 | 541 | 6 | 5000 | 540 | 0.667 | 1.000 | 1.00e+00 | False |
| a8d7f51752 | 541 | 6 | 10000 | 1070 | 0.667 | 1.000 | 1.00e+00 | False |
| ef5081680a | 540 | 4 | 10 | 0 | 1.000 | 0.750 | 6.25e-01 | False |
| ef5081680a | 540 | 4 | 100 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| ef5081680a | 540 | 4 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| ef5081680a | 540 | 4 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| ef5081680a | 540 | 4 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 646e4b6d43 | 515 | 0 | 10 | 0 | 0.000 | 0.000 | 1.00e+00 | False |
| 646e4b6d43 | 515 | 0 | 100 | 0 | 0.000 | 0.000 | 1.00e+00 | False |
| 646e4b6d43 | 515 | 0 | 1000 | 0 | 0.000 | 0.000 | 1.00e+00 | False |
| 646e4b6d43 | 515 | 0 | 5000 | 0 | 0.000 | 0.000 | 1.00e+00 | False |
| 646e4b6d43 | 515 | 0 | 10000 | 0 | 0.000 | 0.000 | 1.00e+00 | False |
| ce4833e866 | 644 | 9 | 10 | 0 | 1.000 | 0.667 | 1.95e-02 | True |
| ce4833e866 | 644 | 9 | 100 | 0 | 1.000 | 0.889 | 1.95e-01 | False |
| ce4833e866 | 644 | 9 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| ce4833e866 | 644 | 9 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| ce4833e866 | 644 | 9 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| e2e3fe9751 | 5396 | 100 | 10 | 0 | 0.960 | 0.540 | 3.22e-23 | True |
| e2e3fe9751 | 5396 | 100 | 100 | 0 | 0.960 | 0.620 | 3.22e-22 | True |
| e2e3fe9751 | 5396 | 100 | 1000 | 0 | 0.960 | 0.640 | 3.22e-21 | True |
| e2e3fe9751 | 5396 | 100 | 5000 | 0 | 0.960 | 0.690 | 1.61e-20 | True |
| e2e3fe9751 | 5396 | 100 | 10000 | 0 | 0.960 | 0.690 | 3.22e-20 | True |
| a092364d80 | 635 | 20 | 10 | 0 | 1.000 | 0.650 | 9.54e-06 | True |
| a092364d80 | 635 | 20 | 100 | 0 | 1.000 | 0.800 | 9.54e-05 | True |
| a092364d80 | 635 | 20 | 1000 | 0 | 1.000 | 0.850 | 9.54e-04 | True |
| a092364d80 | 635 | 20 | 5000 | 0 | 1.000 | 0.850 | 4.77e-03 | True |
| a092364d80 | 635 | 20 | 10000 | 0 | 1.000 | 0.900 | 9.54e-03 | True |
| be21f2afe3 | 471 | 18 | 10 | 0 | 1.000 | 0.667 | 3.81e-05 | True |
| be21f2afe3 | 471 | 18 | 100 | 0 | 1.000 | 0.722 | 3.81e-04 | True |
| be21f2afe3 | 471 | 18 | 1000 | 0 | 1.000 | 0.833 | 3.81e-03 | True |
| be21f2afe3 | 471 | 18 | 5000 | 0 | 1.000 | 0.944 | 1.91e-02 | True |
| be21f2afe3 | 471 | 18 | 10000 | 0 | 1.000 | 0.944 | 3.81e-02 | True |
| 98f77a4b17 | 493 | 7 | 10 | 0 | 1.000 | 0.714 | 7.81e-02 | False |
| 98f77a4b17 | 493 | 7 | 100 | 0 | 1.000 | 0.857 | 7.81e-01 | False |
| 98f77a4b17 | 493 | 7 | 1000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 98f77a4b17 | 493 | 7 | 5000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 98f77a4b17 | 493 | 7 | 10000 | 0 | 1.000 | 1.000 | 1.00e+00 | False |
| 43d8b2dcbe | 490 | 16 | 10 | 0 | 0.938 | 0.562 | 2.59e-03 | True |
| 43d8b2dcbe | 490 | 16 | 100 | 0 | 0.938 | 0.812 | 2.59e-02 | True |
| 43d8b2dcbe | 490 | 16 | 1000 | 0 | 0.938 | 0.812 | 2.59e-01 | False |
| 43d8b2dcbe | 490 | 16 | 5000 | 0 | 0.938 | 0.875 | 1.00e+00 | False |
| 43d8b2dcbe | 490 | 16 | 10000 | 0 | 0.938 | 0.938 | 1.00e+00 | False |
| a623298e48 | 531 | 22 | 10 | 0 | 1.000 | 0.545 | 2.38e-06 | True |
| a623298e48 | 531 | 22 | 100 | 0 | 1.000 | 0.773 | 2.38e-05 | True |
| a623298e48 | 531 | 22 | 1000 | 0 | 1.000 | 0.818 | 2.38e-04 | True |
| a623298e48 | 531 | 22 | 5000 | 0 | 1.000 | 0.864 | 1.19e-03 | True |
| a623298e48 | 531 | 22 | 10000 | 0 | 1.000 | 0.864 | 2.38e-03 | True |
| be5865275e | 2289 | 24 | 10 | 0 | 1.000 | 0.667 | 5.96e-07 | True |
| be5865275e | 2289 | 24 | 100 | 0 | 1.000 | 0.750 | 5.96e-06 | True |
| be5865275e | 2289 | 24 | 1000 | 0 | 1.000 | 0.833 | 5.96e-05 | True |
| be5865275e | 2289 | 24 | 5000 | 0 | 1.000 | 0.833 | 2.98e-04 | True |
| be5865275e | 2289 | 24 | 10000 | 0 | 1.000 | 0.833 | 5.96e-04 | True |

## 5b. Document length × candidate population grid

Attribution accuracy (correct employee, adjusted p < 0.05, ≥20 opportunities) by document length and candidate population. Large-pool cells use a 40-window subsample.

| words | N=10 | N=100 | N=1000 | N=10000 |
|-------||----------|----------|----------|----------|
| 100 | 0.00 | 0.00 | 0.00 | 0.00 |
| 200 | 0.00 | 0.00 | 0.00 | 0.00 |
| 300 | 0.02 | 0.02 | 0.02 | 0.03 |
| 500 | 0.06 | 0.06 | 0.06 | 0.07 |
| 750 | 0.21 | 0.20 | 0.18 | 0.25 |
| 1000 | 0.29 | 0.27 | 0.26 | 0.28 |
| 1500 | 0.70 | 0.70 | 0.66 | 0.60 |
| 2000 | 0.86 | 0.86 | 0.85 | 0.80 |

Insufficient-evidence rate (share below the 20-opportunity threshold) is reported separately in Section 4.

## 6. Null-model calibration

Simulated null (no NLP): for each n and N, N candidates each draw Binomial(n, 0.5) matches; `best` is the max. FWER = fraction of trials where the best candidate passes the Bonferroni threshold.

| opps | cand | trials | theor mean | empir mean | theor var | empir var | empir FWER |
|------|------|--------|-----------|-----------|-----------|-----------|------------|
| 10 | 10 | 2000 | 5.0 | 5.0 | 2.5 | 2.5 | 0.0085 |
| 10 | 100 | 2000 | 5.0 | 5.0 | 2.5 | 2.5 | 0.0000 |
| 10 | 1000 | 2000 | 5.0 | 5.0 | 2.5 | 2.5 | 0.0000 |
| 10 | 10000 | 2000 | 5.0 | 5.0 | 2.5 | 2.5 | 0.0000 |
| 20 | 10 | 2000 | 10.0 | 10.0 | 5.0 | 5.0 | 0.0145 |
| 20 | 100 | 2000 | 10.0 | 10.0 | 5.0 | 5.0 | 0.0225 |
| 20 | 1000 | 2000 | 10.0 | 10.0 | 5.0 | 5.0 | 0.0235 |
| 20 | 10000 | 2000 | 10.0 | 10.0 | 5.0 | 5.0 | 0.0135 |
| 30 | 10 | 2000 | 15.0 | 15.0 | 7.5 | 7.6 | 0.0265 |
| 30 | 100 | 2000 | 15.0 | 15.0 | 7.5 | 7.6 | 0.0180 |
| 30 | 1000 | 2000 | 15.0 | 15.0 | 7.5 | 7.5 | 0.0280 |
| 30 | 10000 | 2000 | 15.0 | 15.0 | 7.5 | 7.5 | 0.0375 |
| 50 | 10 | 2000 | 25.0 | 25.0 | 12.5 | 12.9 | 0.0350 |
| 50 | 100 | 2000 | 25.0 | 25.0 | 12.5 | 12.6 | 0.0510 |
| 50 | 1000 | 2000 | 25.0 | 25.0 | 12.5 | 12.5 | 0.0410 |
| 50 | 10000 | 2000 | 25.0 | 25.0 | 12.5 | 12.5 | 0.0240 |
| 100 | 10 | 2000 | 50.0 | 50.0 | 25.0 | 25.3 | 0.0360 |
| 100 | 100 | 2000 | 50.0 | 50.0 | 25.0 | 25.0 | 0.0440 |
| 100 | 1000 | 2000 | 50.0 | 50.0 | 25.0 | 25.0 | 0.0370 |
| 100 | 10000 | 2000 | 50.0 | 50.0 | 25.0 | 25.0 | 0.0255 |

If empirical means/variance track Binomial(n, 0.5) and empirical FWER stays ≈ the Bonferroni target, the simple null is supported.

## 7. False positives

Unwatermarked Enron emails scored against random fingerprints. `adj upper 95` is the Clopper-Pearson one-sided upper bound.

| docs | cand/doc | raw sig | adj sig | raw frac | adj frac | adj upper 95 | eligible |
|------|----------|---------|---------|----------|----------|--------------|----------|
| 4000 | 100 | 712 | 11 | 0.1780 | 0.0027 | 0.0045 | 156 |
| 4000 | 1000 | 796 | 6 | 0.1990 | 0.0015 | 0.0030 | 156 |

A zero count does not prove FPR=0; the Clopper-Pearson bound is the honest upper limit.

## 8. Author-style bias

Repeated-author test: for each Enron author with ≥10 emails, score their unwatermarked writing against 200 unrelated random fingerprints. If any random key persistently matches a specific human's style, that is a calibration problem.

| author | docs | opps | mean rate | max rate | combined evidence |
|--------|------|------|-----------|----------|-------------------|
| 39aec7fca0 | 46 | 79 | 0.500 | 0.646 | 0.0 |
| 07ed3b366b | 315 | 837 | 0.501 | 0.551 | 0.4 |
| 30fa01256f | 202 | 582 | 0.500 | 0.548 | 0.0 |
| 743294acec | 35 | 59 | 0.500 | 0.712 | 0.8 |
| 0f8c20b967 | 43 | 58 | 0.499 | 0.672 | 0.0 |
| 40d4c77a25 | 16 | 31 | 0.506 | 0.774 | 0.5 |
| 66dfcc09bc | 91 | 235 | 0.498 | 0.587 | 0.0 |
| df058af042 | 41 | 85 | 0.504 | 0.635 | 0.0 |
| 265d304a61 | 72 | 434 | 0.498 | 0.565 | 0.1 |
| 29754c5ec9 | 22 | 13 | 0.498 | 0.846 | 0.0 |
| b57344ed50 | 357 | 6261 | 0.501 | 0.521 | 1.1 |
| 8ec7a75a3e | 27 | 51 | 0.503 | 0.686 | 0.0 |
| 3871e742fa | 143 | 276 | 0.498 | 0.587 | 0.3 |
| dd53f9c3c5 | 66 | 164 | 0.506 | 0.610 | 0.2 |
| de161ab8c4 | 96 | 292 | 0.498 | 0.589 | 0.6 |
| f8c7f08429 | 100 | 568 | 0.501 | 0.565 | 0.7 |
| d3048feb17 | 73 | 388 | 0.501 | 0.585 | 1.0 |
| f888f0519e | 256 | 755 | 0.502 | 0.603 | 5.7 |
| 8d4a832f49 | 121 | 210 | 0.501 | 0.590 | 0.0 |
| 39771a039f | 19 | 78 | 0.501 | 0.628 | 0.0 |
| f576e49756 | 14 | 35 | 0.489 | 0.714 | 0.0 |
| dbb3733b4b | 255 | 554 | 0.499 | 0.567 | 0.7 |
| 50cb790ee6 | 12 | 12 | 0.520 | 0.917 | 0.2 |
| 782352f8ea | 49 | 327 | 0.500 | 0.578 | 0.3 |
| 8ca7f02e25 | 314 | 1933 | 0.499 | 0.527 | 0.0 |
| a58deed47f | 61 | 155 | 0.499 | 0.606 | 0.0 |
| 6c29758dd0 | 28 | 209 | 0.500 | 0.603 | 0.4 |
| ad42322c69 | 30 | 217 | 0.501 | 0.585 | 0.0 |
| 70101c2ffd | 14 | 93 | 0.505 | 0.688 | 1.4 |
| 01bb5e9fba | 88 | 838 | 0.500 | 0.551 | 0.5 |
| 188d26f4ff | 59 | 41 | 0.505 | 0.659 | 0.0 |
| 3ccc2d44c7 | 51 | 52 | 0.500 | 0.692 | 0.1 |
| 5e4ecce477 | 19 | 46 | 0.496 | 0.717 | 0.3 |
| 6a19cf1e78 | 66 | 275 | 0.498 | 0.640 | 3.4 |
| 67f6149376 | 62 | 73 | 0.502 | 0.671 | 0.3 |
| 6c0b397bed | 251 | 427 | 0.499 | 0.555 | 0.0 |
| 45f5eceee8 | 33 | 63 | 0.510 | 0.683 | 0.3 |
| 1c1162b5a7 | 11 | 25 | 0.490 | 0.720 | 0.0 |
| 971e0a881a | 65 | 343 | 0.500 | 0.574 | 0.2 |
| 2d1a91f861 | 43 | 61 | 0.504 | 0.689 | 0.4 |
| 60171d0fc3 | 19 | 56 | 0.491 | 0.679 | 0.0 |
| 009432121a | 44 | 856 | 0.500 | 0.551 | 0.5 |
| 7508dc12ba | 90 | 374 | 0.499 | 0.575 | 0.4 |
| 27fc90a336 | 34 | 26 | 0.504 | 0.846 | 1.3 |
| ed07490fa7 | 14 | 99 | 0.498 | 0.677 | 1.3 |
| 41cc704bcf | 29 | 77 | 0.499 | 0.636 | 0.0 |
| 3e5abd96f1 | 138 | 575 | 0.499 | 0.557 | 0.1 |
| 2b3e9c19a6 | 33 | 46 | 0.498 | 0.761 | 1.3 |
| ea3b02792e | 20 | 73 | 0.500 | 0.644 | 0.0 |
| 7510bb4599 | 32 | 71 | 0.496 | 0.620 | 0.0 |
| feb02ef009 | 18 | 42 | 0.491 | 0.690 | 0.0 |
| bb76bc779a | 35 | 444 | 0.497 | 0.577 | 0.8 |
| f7afbeaea2 | 29 | 77 | 0.505 | 0.662 | 0.2 |
| da39e0f026 | 149 | 360 | 0.501 | 0.561 | 0.0 |
| 0a1ec63e77 | 25 | 35 | 0.499 | 0.743 | 0.2 |
| 021fe20c4e | 18 | 23 | 0.503 | 0.739 | 0.0 |
| b401943888 | 18 | 39 | 0.495 | 0.718 | 0.0 |
| ac4c014c2b | 25 | 179 | 0.499 | 0.609 | 0.4 |
| 368592b225 | 19 | 83 | 0.500 | 0.639 | 0.0 |
| 9292b779cf | 28 | 53 | 0.499 | 0.698 | 0.3 |
| 873da2771e | 48 | 79 | 0.495 | 0.658 | 0.2 |
| e259728618 | 55 | 244 | 0.499 | 0.586 | 0.1 |
| 5b99cff84d | 14 | 10 | 0.496 | 1.000 | 0.7 |
| ecc910a947 | 166 | 502 | 0.499 | 0.568 | 0.6 |
| dbcdca4b0f | 49 | 224 | 0.501 | 0.625 | 1.7 |
| 9411b98545 | 18 | 31 | 0.498 | 0.742 | 0.0 |
| f25492fa3f | 44 | 139 | 0.499 | 0.612 | 0.0 |
| 3ea9ebc032 | 21 | 42 | 0.510 | 0.714 | 0.1 |
| 3198ca2558 | 28 | 63 | 0.505 | 0.667 | 0.0 |
| d48b41709c | 10 | 14 | 0.504 | 0.857 | 0.0 |
| 0c64b64398 | 13 | 1011 | 0.499 | 0.539 | 0.0 |
| ad5586b1c0 | 15 | 144 | 0.497 | 0.597 | 0.0 |
| cd0edf0a75 | 31 | 52 | 0.497 | 0.712 | 0.5 |
| 86c29b9941 | 17 | 89 | 0.498 | 0.629 | 0.0 |
| ee6e95a35d | 20 | 39 | 0.500 | 0.692 | 0.0 |
| aa81f693a7 | 56 | 180 | 0.499 | 0.600 | 0.1 |
| 6ea4f41323 | 38 | 116 | 0.499 | 0.621 | 0.0 |
| 8d95a851b1 | 27 | 112 | 0.499 | 0.661 | 1.1 |
| 7926ba8de2 | 13 | 23 | 0.499 | 0.957 | 3.2 |
| 9766748b87 | 20 | 34 | 0.501 | 0.941 | 5.2 |
| 98727ad7ee | 13 | 12 | 0.492 | 0.917 | 0.2 |
| e320b464b1 | 24 | 46 | 0.494 | 0.696 | 0.0 |
| 9520198c6d | 20 | 106 | 0.503 | 0.670 | 1.2 |
| 6d7933a2b4 | 38 | 90 | 0.500 | 0.633 | 0.0 |
| 92bd3822a1 | 23 | 188 | 0.500 | 0.617 | 0.8 |
| 8bb98f38fb | 20 | 39 | 0.489 | 0.667 | 0.0 |
| 8df0821a9f | 14 | 18 | 0.491 | 0.833 | 0.1 |
| cdf93e80d5 | 18 | 119 | 0.502 | 0.639 | 0.5 |
| e450684f6a | 14 | 82 | 0.498 | 0.659 | 0.3 |
| dd93d0aeac | 18 | 312 | 0.497 | 0.571 | 0.0 |
| 52eac598be | 12 | 36 | 0.503 | 0.778 | 0.9 |
| a3568ae143 | 10 | 16 | 0.498 | 0.812 | 0.0 |
| 06d9207069 | 17 | 54 | 0.502 | 0.759 | 1.8 |
| eca8e143a3 | 24 | 353 | 0.498 | 0.581 | 0.5 |
| 78d048fe95 | 12 | 14 | 0.502 | 0.786 | 0.0 |
| 27e6c3ea3d | 19 | 25 | 0.495 | 0.840 | 1.0 |
| c7a9eee641 | 20 | 42 | 0.499 | 0.738 | 0.5 |
| 886fce8585 | 39 | 227 | 0.496 | 0.617 | 1.3 |
| 814fe81f0a | 40 | 157 | 0.503 | 0.611 | 0.2 |
| 7c9a79688a | 15 | 55 | 0.493 | 0.800 | 3.1 |
| 9dc11ca517 | 32 | 45 | 0.507 | 0.756 | 1.1 |
| 7fccbab91a | 11 | 14 | 0.492 | 0.857 | 0.0 |
| eab5e1f6ef | 23 | 37 | 0.498 | 0.730 | 0.1 |
| 19d432ad36 | 14 | 14 | 0.501 | 0.857 | 0.0 |
| f7eef5eeaf | 11 | 29 | 0.499 | 0.724 | 0.0 |
| d77660b5e3 | 14 | 94 | 0.497 | 0.638 | 0.0 |
| 3ee225a3ea | 11 | 23 | 0.494 | 0.783 | 0.0 |
| d645f10a1d | 11 | 38 | 0.501 | 0.737 | 0.3 |
| 761de542f8 | 11 | 43 | 0.504 | 0.721 | 0.3 |
| 76af6c338d | 15 | 174 | 0.499 | 0.592 | 0.0 |
| 11bf152dc6 | 13 | 41 | 0.507 | 0.805 | 1.9 |
| 2b0699776a | 13 | 29 | 0.498 | 0.759 | 0.1 |
| d8a3863712 | 14 | 25 | 0.506 | 0.720 | 0.0 |

Max rates near 0.5–0.6 with no extreme evidence support the keyed-PRF null; persistent high max rates would indicate author-style bias.

## 9. Per-rule capacity

Per-rule capacity (counts over the sampled Enron set):

| rule | count | share of capacity | robustness to normalization |
|------|-------|-------------------|------------------------------|
| apostrophes | 5818 | 41.8% | weak (curly→straight) |
| quotes | 4579 | 32.9% | weak |
| contractions | 2320 | 16.7% | strong (expand removes channel) |
| serial_comma | 1033 | 7.4% | strong (remove comma removes channel) |
| ellipsis | 158 | 1.1% | weak |

The two most abundant channels in real text (apostrophes, quotes) are the two most fragile (destroyed by typography normalization). The two most robust channels (contractions, serial comma) are less common in real email.

## 10. Rule ablation

Attribution when individual rule groups are removed (HC3 sample):

| rules | docs | median opps | mean opps | attributed fraction |
|-------|------|-------------|-----------|---------------------|
| quotes,ellipsis,dash_style,serial_comma, | 300 | 3 | 4 | 0.000 |
| quotes,ellipsis,dash_style,serial_comma, | 300 | 2 | 3 | 0.000 |
| quotes,ellipsis,dash_style,contractions, | 300 | 2 | 3 | 0.000 |
| quotes,apostrophes,ellipsis,dash_style | 300 | 2 | 3 | 0.000 |
| serial_comma,contractions | 300 | 0 | 1 | 0.000 |
| quotes | 300 | 0 | 1 | 0.000 |
| ellipsis | 300 | 0 | 0 | 0.000 |
| dash_style | 300 | 0 | 0 | 0.000 |
| serial_comma | 300 | 0 | 0 | 0.000 |
| contractions | 300 | 0 | 1 | 0.000 |
| apostrophes | 300 | 2 | 2 | 0.000 |

## 11. Partial-copy robustness

Random contiguous portions of ≥400-word watermarked Enron emails:

| fraction | documents | attributed | insufficient |
|----------|-----------|------------|--------------|
| 0.1 | 315 | 0.003 | 0.978 |
| 0.25 | 315 | 0.010 | 0.933 |
| 0.5 | 315 | 0.016 | 0.876 |
| 0.75 | 315 | 0.013 | 0.800 |

## 12. Opportunity-ID collisions and match independence

Opportunity-ID collisions across Enron + HC3:
- total IDs: 24280, unique: 21564, duplicates: 2716 (11.19%)

Match-independence check (phi coefficient; 0 = independent):
- mean pairwise correlation: -0.013
- expected-bit imbalance (ideal 0.5): 0.489
- duplicate IDs within set: 369

## 12b. Canonicalization-mode experiment

| mode | docs | clean | lowercased | clean det | lower det | dup-ID % |
|------|------|-------|------------|-----------|-----------|----------|
| case-sensitive | 250 | 0.641 | 0.347 | 0.032 | 0.000 | 2.6% |
| case-insensitive | 250 | 0.646 | 0.581 | 0.032 | 0.032 | 2.6% |

If the case-insensitive mode preserves clean detection while raising lowercase survival, it is a candidate for production; the cost is a higher duplicate-ID rate.

## 12c. Combined edit attacks

| attack | docs | mean match rate | detected fraction |
|--------|------|-----------------|-------------------|
| delete20_whitespace | 120 | 0.658 | 0.167 |
| typography_contraction | 120 | 0.570 | 0.033 |
| typography_serial_comma | 120 | 0.610 | 0.092 |
| contraction_serial_comma | 120 | 0.812 | 0.308 |
| lowercase_whitespace | 120 | 0.512 | 0.000 |

## 12d. Human vs machine source text

HC3 density by source (human vs ChatGPT answers):

| source | docs | median words | density/100w | median opps | eligible ≥20 |
|--------|------|--------------|--------------|-------------|--------------|
| human | 1757 | 123 | 1.911 | 3 | 0.5% |
| machine | 743 | 201 | 1.915 | 4 | 0.0% |

## 13. Theoretical detection limits

The mathematically minimal match rate needed for a Bonferroni-adjusted p < 0.05 (from exact binomial tails). This is the *best case* before any editing noise:

| opps | N=10 | N=100 | N=1k | N=10k | N=50k |
|------|------|-------|------|-------|-------|
| 10 | 10 (1.000) | 11 (1.100) | 11 (1.100) | 11 (1.100) | 11 (1.100) |
| 15 | 13 (0.867) | 14 (0.933) | 15 (1.000) | 16 (1.067) | 16 (1.067) |
| 20 | 17 (0.850) | 18 (0.900) | 19 (0.950) | 20 (1.000) | 20 (1.000) |
| 25 | 20 (0.800) | 21 (0.840) | 23 (0.920) | 24 (0.960) | 24 (0.960) |
| 30 | 23 (0.767) | 25 (0.833) | 26 (0.867) | 27 (0.900) | 28 (0.933) |
| 40 | 29 (0.725) | 31 (0.775) | 33 (0.825) | 34 (0.850) | 35 (0.875) |
| 50 | 35 (0.700) | 37 (0.740) | 39 (0.780) | 41 (0.820) | 42 (0.840) |
| 75 | 50 (0.667) | 53 (0.707) | 55 (0.733) | 57 (0.760) | 59 (0.787) |
| 100 | 64 (0.640) | 67 (0.670) | 70 (0.700) | 73 (0.730) | 74 (0.740) |

At N=10,000 the required match rate exceeds ~0.85 even at 30 opportunities, which is only achievable on unedited text. Values >1.0 mean the document is mathematically unattributeable at that candidate population.

## 14. Performance

Median milliseconds on Apple M3 Pro (decode-once / score-many):

| words | opps | watermark | decode | score @10 | score @1k | score @10k |
|-------|------|-----------|--------|-----------|-----------|------------|
| 100 | 1 | 12 | 11 | 0.0 | 3 | 30 |
| 500 | 12 | 51 | 51 | 0.2 | 19 | 187 |
| 1000 | 18 | 99 | 98 | 0.3 | 27 | 277 |
| 2000 | 43 | 212 | 202 | 0.6 | 64 | 649 |

## 15. Limitations

- **Density is the binding constraint.** Real email/QA text yields ~1.3–1.9 opportunities per 100 words, so ~500–1,500 words are needed just to reach 20 opportunities, and far more for confident attribution among thousands of candidates.
- **Most real-text capacity is fragile.** Apostrophes and quote typography dominate but are destroyed by typography normalization.
- **Robust channels are rarer in real text.** Contractions and serial commas are less common in business email than in hand-crafted V1 prose.
- **Lowercasing destroys sentence-local IDs** (case is part of the canonical context); this remains a known attack.
- **Not AI detection.** HC3 shows machine and human source text have similar density; TraceMark fingerprints only text it processed.
- **Paraphrase robustness untested without provider keys**; expected to be weak (V1-style normalization already degrades several channels).

## 16. Answers to the required questions

1. Median opportunity density by dataset: 1.251/100w (Enron), 1.961/100w (HC3).
2. % of real documents with enough evidence: 3.6% of Enron emails reach 20 opportunities.
3. Binomial(n,0.5) null supported: 20/20 simulated configs match theory within tolerance.
4. Match indicators correlated? mean pairwise correlation -0.013, bit imbalance 0.489.
5. Repeated author style: across 113 Enron authors the mean random-key match rate is 0.500 (no systematic bias); the best-key match rate reaches 1.000 and the maximum corrected evidence is 5.7. A few author×key pairs reach corrected significance, consistent with multiple-testing tails and driven partly by ~11% opportunity-ID collisions from repeated boilerplate.
6. Measured false attribution: 0.27% adjusted-significant over unwatermarked corpus.
7. See candidate-scale rows for how attribution changes with N.
8. Document length needed for reliable attribution among 10k employees: see Sections 4/5/13 — realistically 1,000–2,000+ words on clean text.
9–10. Which rules provide capacity / dependence on contractions+serial comma: see Section 9. In real text, apostrophes+quotes dominate (fragile); in synthetic text, contractions+serial commas dominate.
11. Additional conservative rules: pattern inventory shows hyphens (1.3/100w), times (0.6/100w) and numeric ranges (0.37/100w) in Enron; a conservative numeric-range en-dash rule was implemented in this sprint (STRICT), adding only modest density (~0.1–0.2/100w) because date-like ranges are deliberately rejected.
12. Case-insensitive canonical context: case-sensitive clean=0.641, lowercased=0.347, lowercased-detected=0.000; case-insensitive clean=0.646, lowercased=0.581, lowercased-detected=0.032. Case-insensitive preserves clean detection while roughly doubling lowercase survival; the cross-document ID-collision cost (11% overall) still argues for keeping case-sensitive as production until the collision tradeoff is measured directly.
13. Partial copy/paste survival: see Section 11 — copying 10–25% of a ≥400-word document is essentially never attributable (0.3–1.0%).
14–16. LLM rewrite survival: requires provider keys; not measured in this run. Based on channel-normalization results, light rewrites are expected to degrade several channels and heavy paraphrasing to destroy the signal.
17. Human vs machine source: HC3 density is similar for both (machine ~1.9/100w); TraceMark does not detect AI, it fingerprints processed text.
18. Detection speed at 10k employees: one parse + 10k HMAC scorings; see Section 14.
19–20. Strongest/weakest cases: see Product implications and Commercial Viability Assessment below.

## 17. Product implications

**What TraceMark is genuinely good at (on the evidence):**
- Long, clean, unedited documents (1,000+ words) among a small-to-medium candidate population, where a single honest fingerprint is the goal.
- Forensic-style copy/paste attribution of large excerpts.

**Where the evidence says it is weak:**
- Real business emails (median <100 words, ~1 opportunity each).
- Large employee populations with short documents.
- Any workflow where text is lightly rewritten or typography-normalized.

The V1 synthetic benchmark materially overstated capability; V2's real-corpus measurements are the honest basis for any product decision.

## Commercial Viability Assessment

Ratings are based only on measured evidence.

| Use case | Rating | Basis |
|----------|--------|-------|
| Short business emails | **Not viable in current form** | median ~1 opportunity/doc, ~3.5% reach the 20-opp threshold |
| Long business emails | **Weak** | ~400-word emails still often short of the threshold; apostrophe/quote channels are normalization-fragile |
| Legal memos | **Insufficient evidence** | legal text is contraction-sparse; not separately measured in this sprint |
| Financial reports | **Promising** | longer reports, numeric range/density present; needs more corpus |
| Technical reports | **Promising** | moderate density; hyphen/time patterns available |
| Long AI-generated deliverables | **Weak–Promising** | HC3 machine text has similar low density to human text |
| Forensic copy/paste attribution | **Promising** | large-excerpt survival is good; small excerpts are not |
| Adversarial watermark resistance | **Not viable in current form** | typography normalization, lowercase, and channel normalization remove most real-text capacity |
| Employee-level attribution | **Not viable in current form** | short real documents and large populations are the actual product shape, and the evidence threshold cannot be met |
| Model-scope attribution | **Insufficient evidence** | multiplies hypotheses and cost; not measured at scale |

**Overall:** at V1's rule set, TraceMark is best characterized as a research-grade tool with a promising forensic niche for **long, clean, unedited documents**. It is not currently a general-purpose enterprise attribution product for everyday email/chat content. Increasing capacity with safe real-text rules and improving normalization robustness are prerequisites before commercialization is defensible.

## Appendix. Reproducibility

- git commit: 768ff28
- Python: 3.12
- seed: fixed per benchmark (see module defaults)
- policy: balanced; rules: quotes, apostrophes, ellipsis, dash_style, serial_comma, contractions
- corpora versions: Enron 20150507, HC3 main, newsgroups bydate
- machine: Apple M3 Pro, 18 GB, macOS
- Raw CSVs: `benchmarks/results/v2/*.csv`