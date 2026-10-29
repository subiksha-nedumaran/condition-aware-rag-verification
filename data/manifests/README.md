# FieldGuard — Source Manifests & Acquisition Provenance

This directory contains the reproducible provenance manifests and acquisition logs for the official PMFBY corpus:

- `source_manifest.json`: Complete JSON manifest with SHA-256 checksums, document versions, publication dates, effective dates, and verification statuses.
- `source_manifest.csv`: Tabular CSV representation of the source manifest.
- `download_log.jsonl`: Append-only structured acquisition log recording HTTP download attempts, status codes, redirect URLs, PDF signature checks, and sandbox fallback events.

## Temporal Metadata Policy

1. **Confirmed vs. Unknown Dates:** `publication_date` and `effective_from` are recorded only when explicitly stated in the official source. Unknown dates remain `null` with status `"unknown"`.
2. **No Inferred Effective Dates:** An effective date (`effective_from`) is **never** inferred merely from a document's publication date. For example, PIB Press Release `PRID=2197713` has a confirmed `publication_date` of `2025-12-12`, while `effective_from` is explicitly `null` (`"unknown"`).
3. **Policy Versioning:** Historical guidelines (`DOC_PMFBY_OG_2016_HIST`, effective `2016-04-01` to `2020-03-31`), revamped operational guidelines (`DOC_PMFBY_OG_2023`, effective from `2020-04-01` / 2023 update), undated official FAQs (`DOC_PMFBY_FAQ_OFFICIAL`), and the December 2025 announcement (`DOC_PIB_2025_PRID2197713`) are kept strictly separate.

## Manual Acquisition Instructions (When Running in an Offline / Sandboxed Network)

If automated live HTTP acquisition encounters network isolation (`getaddrinfo failed`), the pipeline logs the network error in `download_log.jsonl` and provisions the verified reference corpus in `data/raw/documents/`. To manually replace or refresh raw PDFs on an internet-connected machine:

1. Download the 2023 Operational Guidelines PDF from `https://pmfby.amnex.co.in/pmfby/pdf/operational_guidelines_pmfby.pdf` into `data/raw/documents/operational_guidelines_pmfby_2023.pdf`.
2. Download the official FAQ from `https://pmfby.gov.in/faq` and PIB Release `PRID=2197713` from `https://www.pib.gov.in/PressReleasePage.aspx?PRID=2197713&lang=2&reg=48`.
3. Re-run `python -m fieldguard.data_acquisition` to validate `%PDF-` signatures and update SHA-256 hashes.
