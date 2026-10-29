# FieldGuard — Data Dictionary

This document specifies the schema of every JSONL, JSON, and CSV artifact produced and consumed across the FieldGuard pipeline.

---

## 1. Source Manifest (`data/manifests/source_manifest.json` & `.csv`)

| Field | Type | Description |
| :--- | :--- | :--- |
| `doc_id` | `str` | Deterministic canonical document identifier (e.g., `DOC_PMFBY_OG_2023`). |
| `title` | `str` | Official document title as verified from the header or page title. |
| `publisher` | `str` | Issuing ministry or government agency (e.g., `Ministry of Agriculture & Farmers Welfare, Government of India`). |
| `source_url` | `str` | Initial official URL targeted during corpus acquisition. |
| `final_url` | `str` | Final resolved URL after HTTP redirects (or fallback path if offline/blocked). |
| `retrieval_timestamp_utc` | `str` | ISO-8601 UTC timestamp of acquisition. |
| `sha256` | `str` | SHA-256 cryptographic digest of the raw file in `data/raw/documents/`. |
| `file_size_bytes` | `int` | Exact byte length of the saved file. |
| `mime_type` | `str` | Verified MIME type (`application/pdf`, `text/html`, or `text/plain`). |
| `local_path` | `str` | Relative path under `data/raw/documents/`. |
| `publication_date` | `str \| null` | Confirmed publication date (`YYYY-MM-DD`) or `null` if unconfirmed. |
| `publication_date_status` | `str` | `CONFIRMED` or `UNKNOWN`. |
| `effective_from` | `str \| null` | Confirmed policy effective start date (`YYYY-MM-DD`) or `null` (never inferred merely from `publication_date`). |
| `effective_from_status` | `str` | `CONFIRMED` or `UNKNOWN`. |
| `effective_to` | `str \| null` | Confirmed policy effective end date or `null`. |
| `policy_version` | `str` | Policy regime identifier (`OG_2023_REVAMPED`, `OG_2016_HISTORICAL`, `PIB_2025_12_ANNOUNCEMENT`, `FAQ_PORTAL_UNDATED`). |
| `applicable_period` | `str` | Human-readable seasonal/temporal scope (e.g., `Kharif 2020 onwards (2023 Revamped Operational Guidelines)`). |
| `authority_tier` | `str` | Document authority tier: `TIER_1_OPERATIONAL_GUIDELINES`, `TIER_2_OFFICIAL_PORTAL_FAQ`, `TIER_3_PRESS_RELEASE_LEAD`, or `SYNTHETIC_ADVERSARIAL`. |
| `acquisition_mode` | `str` | `LIVE_HTTP_DOWNLOAD` or `VERIFIED_OFFICIAL_CURATED_EXCERPT_FALLBACK`. |
| `license_notes` | `str` | Copyright, attribution, and reuse restrictions verified for the document. |

---

## 2. Extracted Text Chunks (`data/processed/chunks.jsonl`)

| Field | Type | Description |
| :--- | :--- | :--- |
| `chunk_id` | `str` | Unique chunk identifier (`{doc_id}_P{page:02d}_C{idx:03d}`). |
| `doc_id` | `str` | Parent document ID from `source_manifest.json`. |
| `doc_title` | `str` | Parent document title. |
| `page_number` | `int` | 1-indexed source page number. |
| `section_heading` | `str` | Nearest preceding section heading preserved during structure-aware chunking. |
| `clause_id` | `str \| null` | Paragraph or clause number (e.g., `Para 10.1`, `Para 14.2`). |
| `text` | `str` | Extracted and normalized text content of the chunk. |
| `char_count` | `int` | Character length of `text`. |
| `policy_version` | `str` | Inherited policy version from document metadata. |
| `authority_tier` | `str` | Inherited authority tier from document metadata. |
| `effective_from` | `str \| null` | Confirmed effective start date or `null`. |
| `contains_numbers` | `bool` | Whether the chunk contains numeric percentages, counts, or deadlines. |

---

## 3. Extracted Table Rows (`data/processed/table_rows.jsonl`)

| Field | Type | Description |
| :--- | :--- | :--- |
| `row_id` | `str` | Unique table row identifier (`{doc_id}_T{table_idx:02d}_R{row_idx:02d}`). |
| `doc_id` | `str` | Parent document ID. |
| `page_number` | `int` | 1-indexed page number where the table appears. |
| `table_title` | `str` | Table caption or nearest section heading. |
| `headers` | `list[str]` | Ordered list of column header strings. |
| `cells` | `dict[str, str]` | Mapping from column header to cell string value for this row. |
| `serialized_text` | `str` | Condition-preserving natural-language serialization of the row used by lexical, semantic, and table-aware retrievers. |
| `policy_version` | `str` | Inherited policy version. |
| `authority_tier` | `str` | Inherited authority tier. |

---

## 4. Structured Evidence Store (`data/benchmark/evidence.jsonl`)

| Field | Type | Description |
| :--- | :--- | :--- |
| `rule_id` | `str` | Unique rule identifier (e.g., `RULE_OG2023_T01_R01`). |
| `doc_id` | `str` | Provenance document ID (`DOC_PMFBY_OG_2023`, `DOC_SYNTH_ADVERSARIAL`, etc.). |
| `source_id` | `str` | Provenance chunk ID (`chunk_id`) or table row ID (`row_id`). |
| `source_type` | `str` | `table_row`, `prose_chunk`, or `synthetic_adversarial`. |
| `is_synthetic` | `bool` | `false` for real official documents; `true` for synthetic stress-test distractors. |
| `scheme` | `str` | Scheme code (`PMFBY` or `RWBCIS`). |
| `parameter_type` | `str` | Normalized parameter category (`farmer_premium_cap`, `intimation_window`, `subsidy_sharing_ratio`, `ne_subsidy_sharing_ratio`, `enrollment_modality`, `late_cut_yield_penalty_threshold`, `cce_minimum_sample`, `prevented_sowing_payout_cap`, `admin_expense_cap`). |
| `numeric_value` | `float` | Canonical floating-point value (e.g., `2.0` for `2%`, `72.0` for `72 hours`). |
| `unit` | `str` | Canonical unit (`percent`, `hours`, `days`, `cce_count`, `boolean_percent`). |
| `basis` | `str` | Denominator or calculation basis (`sum_insured_or_actuarial_whichever_less`, `central_state_premium_subsidy`, `threshold_yield`, `indemnity_limit`, `not_applicable`). |
| `comparison_operator` | `str` | `max_cap`, `exact`, `min_threshold`, or `within_window`. |
| `qualification` | `str` | Qualifying clause (`whichever_is_less_with_actuarial`, `voluntary_for_all_farmers`, `mandatory_for_loanee_farmers`, `intimate_within_72_hours_Up_to_14_days_after_harvest`, `none`). |
| `season` | `str` | Applicable season (`kharif`, `rabi`, `annual`, `all_seasons`). |
| `crop_category` | `str` | Applicable crop category (`food_grains_and_oilseeds`, `commercial_and_horticultural`, `all_notified_crops`, `perennial_horticultural`). |
| `farmer_category` | `str` | Applicable farmer segment (`all_farmers`, `loanee_farmers`, `non_loanee_farmers`). |
| `geography` | `str` | Applicable geographic region (`general_states`, `north_eastern_and_himalayan_states`, `all_india`). |
| `peril_scope` | `str` | Covered risk stage (`all_covered_risks`, `post_harvest_cyclonic_unseasonal_rain`, `localised_calamities_hailstorm_landslide_inundation`, `prevented_sowing_germination_failure`, `mid_season_adversity`, `wild_animal_attack_add_on`). |
| `policy_version` | `str` | Policy regime (`OG_2023_REVAMPED`, `OG_2016_HISTORICAL`, `PIB_2025_12_ANNOUNCEMENT`, `FAQ_PORTAL_UNDATED`). |
| `authority_tier` | `str` | Authority tier of the source document. |
| `effective_from` | `str \| null` | Confirmed effective start date or `null`. |
| `raw_evidence_text` | `str` | Verbatim text span or serialized table row backing the rule. |

---

## 5. Benchmark Claims (`data/benchmark/claims.jsonl`)

| Field | Type | Description |
| :--- | :--- | :--- |
| `claim_id` | `str` | Unique claim identifier (`FG_CLM_0001` through `FG_CLM_0240`). |
| `claim_family_id` | `str` | Base claim family ID (`FAM_001` through `FAM_060`) used for zero-leakage grouped splitting. |
| `split` | `str` | Dataset partition (`dev` or `test`). All claims sharing a `claim_family_id` reside in the same split. |
| `question_text` | `str` | Natural-language question or claim statement submitted to the verification pipeline. |
| `gold_verdict` | `str` | Ground-truth 4-way label (`SUPPORTED`, `CONTRADICTED`, `WRONG_CONTEXT`, `UNVERIFIABLE`). |
| `perturbation_type` | `str` | Controlled perturbation applied (`canonical_supported`, `wrong_season`, `wrong_crop_category`, `wrong_geography`, `wrong_peril_scope`, `wrong_value`, `decimal_scale_confusion`, `missing_actuarial_qualification`, `wrong_basis`, `historical_2016_vs_current`, `undated_faq_current_assertion`, `unverified_2025_pib_rule_detail`, `out_of_scope_scheme_or_livestock`, `conflicting_unresolved_evidence`). |
| `evidence_regime` | `str` | Retrieval/evidence evaluation regime (`clean_single_rule`, `multi_rule_distractor_table`, `temporal_version_shift`, `missing_or_unverified_source`, `synthetic_conflict_stress`). |
| `source_origin` | `str` | `real_official_corpus` or `synthetic_stress_test`. |
| `gold_evidence_ids` | `list[str]` | List of authoritative `rule_id`s (and corresponding `source_id`s) required to resolve the claim. |
| `gold_structured_claim` | `dict` | Ground-truth parsed slots (`scheme`, `parameter_type`, `claimed_value`, `claimed_unit`, `basis`, `comparison_operator`, `qualification`, `season`, `crop_category`, `farmer_category`, `geography`, `peril_scope`, `temporal_scope`, `requested_policy_version`, `requested_effective_date`). |
| `annotator_rationale` | `str` | Explicit human-auditable explanation of why `gold_verdict` holds under the annotation guidelines. |
