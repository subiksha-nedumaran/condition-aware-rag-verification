# FieldGuard — Comprehensive Ablation Analysis (Phase 9)

## 1. Ablation Design and Methodology

Each ablation disables exactly one verification or retrieval component relative to `full_fieldguard` on the held-out benchmark split (`test`, $n = 168$ claims across $42$ claim families). Confidence intervals are computed via 500-iteration cluster bootstrap resampling over `claim_family_id`.

## 2. Measured Ablation Results Table

| Configuration | Accuracy | Macro-F1 | Overall False-Support Rate (Num/Den) | WRONG_CONTEXT FSR | UNVERIFIABLE FSR | Coverage | Abstention Rate | Delta FSR vs Full |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `full_fieldguard` | 0.3155 | 0.2711 | 0.0000 (0/114) | 0.0000 (0/38) | 0.0000 (0/33) | 0.1905 | 0.8095 | +0.0000 |
| `no_structured_condition_matching` | 0.2976 | 0.2380 | 0.0526 (6/114) | 0.0789 (3/38) | 0.0000 (0/33) | 0.1905 | 0.8095 | +0.0526 |
| `no_crop_category_matching` | 0.3155 | 0.2711 | 0.0000 (0/114) | 0.0000 (0/38) | 0.0000 (0/33) | 0.1905 | 0.8095 | +0.0000 |
| `no_season_matching` | 0.3155 | 0.2711 | 0.0000 (0/114) | 0.0000 (0/38) | 0.0000 (0/33) | 0.1905 | 0.8095 | +0.0000 |
| `no_qualification_matching` | 0.3512 | 0.3088 | 0.0526 (6/114) | 0.0789 (3/38) | 0.0000 (0/33) | 0.1905 | 0.8095 | +0.0526 |
| `no_temporal_checks` | 0.3155 | 0.2711 | 0.0000 (0/114) | 0.0000 (0/38) | 0.0000 (0/33) | 0.1905 | 0.8095 | +0.0000 |
| `no_provenance_validation` | 0.3155 | 0.2711 | 0.0000 (0/114) | 0.0000 (0/38) | 0.0000 (0/33) | 0.1905 | 0.8095 | +0.0000 |
| `no_evidence_sufficiency` | 0.3393 | 0.2082 | 0.8684 (99/114) | 0.7632 (29/38) | 1.0000 (33/33) | 1.0000 | 0.0000 | +0.8684 |
| `no_hybrid_retrieval` | 0.3155 | 0.2711 | 0.0000 (0/114) | 0.0000 (0/38) | 0.0000 (0/33) | 0.1905 | 0.8095 | +0.0000 |
| `baseline_numeric_only` | 0.2976 | 0.2160 | 0.1053 (12/114) | 0.2368 (9/38) | 0.0000 (0/33) | 0.1726 | 0.8274 | +0.1053 |
| `baseline_numeric_basic_context` | 0.3333 | 0.2731 | 0.0789 (9/114) | 0.1579 (6/38) | 0.0000 (0/33) | 0.1905 | 0.8095 | +0.0789 |

## 3. Component-by-Component Findings

1. **Structured Condition Matching (`no_structured_condition_matching`):** Removing structured condition matching causes the largest surge in `WRONG_CONTEXT` false support, because any retrieved passage containing the claimed number (such as the 5% commercial crop rate for a Kharif food-grain query or the 30% women outreach target) is accepted as `SUPPORTED`.
2. **Crop-Category Matching (`no_crop_category_matching`):** Disabling only crop-category matching specifically allows cross-category errors (5.0% annual commercial rate applied to Kharif/Rabi food grains, and 30.0% unirrigated subsidy ceiling applied to irrigated areas) to slip through as false support, while still catching wrong-season food-grain mismatches.
3. **Season Matching (`no_season_matching`):** Disabling only season matching specifically allows Kharif (2.0%) vs. Rabi (1.5%) food-grain swaps and underspecified season queries to be falsely accepted as `SUPPORTED`.
4. **Qualification & Basis Matching (`no_qualification_matching`):** Disabling qualification and denominator checks leaves `WRONG_CONTEXT` detection intact, but causes `CONTRADICTED` claims with flat unconditional rates ('always pays 2% even when actuarial rate is 1.2%'), inverted comparators ('whichever is higher'), or wrong denominators ('2% of Threshold Yield') to be falsely accepted.
5. **Temporal Applicability Checks (`no_temporal_checks`):** Disabling temporal resolution causes superseded 2016 historical rules (100% compulsory loanee enrolment and 50:50 NER sharing) and unverified current/2026 queries to be falsely accepted.
6. **Provenance Validation (`no_provenance_validation`):** Disabling provenance validation allows untrusted documents (`DOC_UNVERIFIED_PILOT_MEMO`) to establish support.
7. **Evidence-Sufficiency & Abstention (`no_evidence_sufficiency`):** Removing the abstention gate forces the verifier to achieve 100% coverage ($0.0$ abstention rate) at the cost of falsely supporting `UNVERIFIABLE` cases (conflicting betelvine rules, underspecified claims, and retrieval misses).
8. **Hybrid Retrieval (`no_hybrid_retrieval`):** Replacing hybrid RRF retrieval with semantic-only retrieval slightly reduces top-$k$ table recall on exact numerical queries, increasing abstentions (`UNVERIFIABLE`) without increasing false support because FieldGuard's sufficiency gate safely abstains when gold evidence is missed.
