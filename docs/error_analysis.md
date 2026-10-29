# FieldGuard — Evidence-Grounded Error Analysis (Phase 14)

## 1. Overview of Error Taxonomy

- **Evaluated Split Size:** 168 benchmark claims.
- **Wrong-Context False Supports in Baseline B (`numeric_only`) Caught by FieldGuard:** 6 cases.
- **Qualification & Denominator False Supports in Baseline C (`numeric_basic_context`) Caught by FieldGuard:** 0 cases.
- **Temporal / Policy-Version False Supports in Baseline C Caught by FieldGuard:** 3 cases.
- **Correct Abstentions (`UNVERIFIABLE`) by FieldGuard:** 33 cases.
- **Residual Verdict Errors in Full FieldGuard:** 115 cases.

## 2. Representative Wrong-Context Failures in Baselines (Corrected by FieldGuard)

### Case `CLM_0127` (`cat07_inappropriate_historical_version`)
- **Question:** [FAM_032] Under the 2023 PMFBY operational guidelines, is the Central Government's share of normal premium subsidy in North Eastern States 50.0% (50:50)?
- **Candidate Claim:** Under the 2023 PMFBY operational guidelines, the Central Government's share of normal premium subsidy in North Eastern States is 50.0% (50:50).
- **Numeric-Only Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `WRONG_CONTEXT`
- **Detected Context Mismatch:** `['geography_mismatch(claimed=north_eastern_states, rule=general_states)', 'policy_version_mismatch(superseded_2016_historical_rule)']`
- **FieldGuard Rationale:** Claimed value (50.0 percent) belongs to a different context in rule RULE_OG2023_SUBSIDY_SHARE_GENERAL_STATES (EV_DOC_PMFBY_OG_2023_P5_TBL_OG2023_SUBSIDY_CAPS_R3): ['geography_mismatch(claimed=north_eastern_states, rule=general_states)', 'policy_version_mismatch(superseded_2016_historical_rule)'].

### Case `CLM_0136` (`cat09_misleading_paragraph_distractor`)
- **Question:** [FAM_034] Based on the Section XIX outreach paragraph mentioning 2.0 hectares, is the Rabi food-grain farmer premium 2.0% under PMFBY?
- **Candidate Claim:** Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Rabi food-grain crops is 2.0% of Sum Insured.
- **Numeric-Only Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `WRONG_CONTEXT`
- **Detected Context Mismatch:** `['unrelated_paragraph_distractor_number']`
- **FieldGuard Rationale:** Claimed number (2.0 hectares) appears in unrelated administrative/outreach paragraph EV_DOC_PMFBY_OG_2023_P7_CHUNK_2 rather than an applicable policy rule for farmer_premium_rate.

### Case `CLM_0175` (`cat07_inappropriate_historical_version`)
- **Question:** [FAM_044] Under the 2023 PMFBY operational guidelines, is the Central Government's share of normal premium subsidy in North Eastern States 50.0% (50:50)?
- **Candidate Claim:** Under the 2023 PMFBY operational guidelines, the Central Government's share of normal premium subsidy in North Eastern States is 50.0% (50:50).
- **Numeric-Only Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `WRONG_CONTEXT`
- **Detected Context Mismatch:** `['geography_mismatch(claimed=north_eastern_states, rule=general_states)', 'policy_version_mismatch(superseded_2016_historical_rule)']`
- **FieldGuard Rationale:** Claimed value (50.0 percent) belongs to a different context in rule RULE_OG2023_SUBSIDY_SHARE_GENERAL_STATES (EV_DOC_PMFBY_OG_2023_P5_TBL_OG2023_SUBSIDY_CAPS_R3): ['geography_mismatch(claimed=north_eastern_states, rule=general_states)', 'policy_version_mismatch(superseded_2016_historical_rule)'].

### Case `CLM_0184` (`cat09_misleading_paragraph_distractor`)
- **Question:** [FAM_046] Based on the Section XIX outreach paragraph mentioning 2.0 hectares, is the Rabi food-grain farmer premium 2.0% under PMFBY?
- **Candidate Claim:** Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Rabi food-grain crops is 2.0% of Sum Insured.
- **Numeric-Only Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `WRONG_CONTEXT`
- **Detected Context Mismatch:** `['unrelated_paragraph_distractor_number']`
- **FieldGuard Rationale:** Claimed number (2.0 hectares) appears in unrelated administrative/outreach paragraph EV_DOC_PMFBY_OG_2023_P7_CHUNK_2 rather than an applicable policy rule for farmer_premium_rate.

### Case `CLM_0223` (`cat07_inappropriate_historical_version`)
- **Question:** [FAM_056] Under the 2023 PMFBY operational guidelines, is the Central Government's share of normal premium subsidy in North Eastern States 50.0% (50:50)?
- **Candidate Claim:** Under the 2023 PMFBY operational guidelines, the Central Government's share of normal premium subsidy in North Eastern States is 50.0% (50:50).
- **Numeric-Only Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `WRONG_CONTEXT`
- **Detected Context Mismatch:** `['geography_mismatch(claimed=north_eastern_states, rule=general_states)', 'policy_version_mismatch(superseded_2016_historical_rule)']`
- **FieldGuard Rationale:** Claimed value (50.0 percent) belongs to a different context in rule RULE_OG2023_SUBSIDY_SHARE_GENERAL_STATES (EV_DOC_PMFBY_OG_2023_P5_TBL_OG2023_SUBSIDY_CAPS_R3): ['geography_mismatch(claimed=north_eastern_states, rule=general_states)', 'policy_version_mismatch(superseded_2016_historical_rule)'].

## 3. Representative Qualification & Denominator Failures in Basic-Context Baseline

## 4. Representative Temporal & Policy-Version Failures in Basic-Context Baseline

### Case `CLM_0127` (`cat07_inappropriate_historical_version`)
- **Question:** [FAM_032] Under the 2023 PMFBY operational guidelines, is the Central Government's share of normal premium subsidy in North Eastern States 50.0% (50:50)?
- **Candidate Claim:** Under the 2023 PMFBY operational guidelines, the Central Government's share of normal premium subsidy in North Eastern States is 50.0% (50:50).
- **Basic-Context Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `WRONG_CONTEXT` (`temporal_status=matched_2023_guidelines`)
- **FieldGuard Rationale:** Claimed value (50.0 percent) belongs to a different context in rule RULE_OG2023_SUBSIDY_SHARE_GENERAL_STATES (EV_DOC_PMFBY_OG_2023_P5_TBL_OG2023_SUBSIDY_CAPS_R3): ['geography_mismatch(claimed=north_eastern_states, rule=general_states)', 'policy_version_mismatch(superseded_2016_historical_rule)'].

### Case `CLM_0175` (`cat07_inappropriate_historical_version`)
- **Question:** [FAM_044] Under the 2023 PMFBY operational guidelines, is the Central Government's share of normal premium subsidy in North Eastern States 50.0% (50:50)?
- **Candidate Claim:** Under the 2023 PMFBY operational guidelines, the Central Government's share of normal premium subsidy in North Eastern States is 50.0% (50:50).
- **Basic-Context Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `WRONG_CONTEXT` (`temporal_status=matched_2023_guidelines`)
- **FieldGuard Rationale:** Claimed value (50.0 percent) belongs to a different context in rule RULE_OG2023_SUBSIDY_SHARE_GENERAL_STATES (EV_DOC_PMFBY_OG_2023_P5_TBL_OG2023_SUBSIDY_CAPS_R3): ['geography_mismatch(claimed=north_eastern_states, rule=general_states)', 'policy_version_mismatch(superseded_2016_historical_rule)'].

### Case `CLM_0223` (`cat07_inappropriate_historical_version`)
- **Question:** [FAM_056] Under the 2023 PMFBY operational guidelines, is the Central Government's share of normal premium subsidy in North Eastern States 50.0% (50:50)?
- **Candidate Claim:** Under the 2023 PMFBY operational guidelines, the Central Government's share of normal premium subsidy in North Eastern States is 50.0% (50:50).
- **Basic-Context Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `WRONG_CONTEXT` (`temporal_status=matched_2023_guidelines`)
- **FieldGuard Rationale:** Claimed value (50.0 percent) belongs to a different context in rule RULE_OG2023_SUBSIDY_SHARE_GENERAL_STATES (EV_DOC_PMFBY_OG_2023_P5_TBL_OG2023_SUBSIDY_CAPS_R3): ['geography_mismatch(claimed=north_eastern_states, rule=general_states)', 'policy_version_mismatch(superseded_2016_historical_rule)'].

## 5. Representative Correct Abstentions (`UNVERIFIABLE`: Missing Evidence, Conflicts, Retrieval Misses)

### Case `CLM_0130` (`cat08_unresolved_effective_date_or_current`)
- **Question:** [FAM_033] Under the latest current 2026 revised PMFBY operational guidelines (following the December 2025 revision), is the maximum farmer premium for Kharif food grains still 2.0%?
- **Candidate Claim:** Under the latest current 2026 revised PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 2.0% of Sum Insured.
- **Abstention Reason:** `malformed_or_non_numerical_claim`
- **FieldGuard Rationale:** Claim parsing failed or numeric value/unit is corrupted/missing; malformed claims cannot bypass verification.

### Case `CLM_0131` (`cat08_unresolved_effective_date_or_current`)
- **Question:** [FAM_033] Did the 100.0% State-funded wild animal attack add-on cover in PIB release PRID=2197713 take legal effect on 2025-12-12?
- **Candidate Claim:** Under PMFBY, the 100.0% State-funded wild animal attack add-on cover announced in PIB release PRID=2197713 has a verified effective start date of 2025-12-12.
- **Abstention Reason:** `malformed_or_non_numerical_claim`
- **FieldGuard Rationale:** Claim parsing failed or numeric value/unit is corrupted/missing; malformed claims cannot bypass verification.

### Case `CLM_0132` (`cat08_unresolved_effective_date_or_current`)
- **Question:** [FAM_033] Based strictly on the undated official FAQ page, can we verify that the 2.0% Kharif food-grain premium ceiling was effective on 2023-07-01 under the 2023 guidelines?
- **Candidate Claim:** Under the 2023 PMFBY operational guidelines effective on 2023-07-01, the maximum farmer premium for Kharif food grains is 2.0% of Sum Insured.
- **Abstention Reason:** `malformed_or_non_numerical_claim`
- **FieldGuard Rationale:** Claim parsing failed or numeric value/unit is corrupted/missing; malformed claims cannot bypass verification.

### Case `CLM_0137` (`cat10_conflicting_official_sources`)
- **Question:** [FAM_035] Under the 2023 PMFBY pilot addendum for Kharif perennial betelvine, is the maximum farmer premium 5.0% of Sum Insured?
- **Candidate Claim:** Under the 2023 PMFBY guidelines, the maximum farmer premium for Kharif perennial betelvine is 5.0% of Sum Insured or actuarial rate, whichever is less.
- **Abstention Reason:** `malformed_or_non_numerical_claim`
- **FieldGuard Rationale:** Claim parsing failed or numeric value/unit is corrupted/missing; malformed claims cannot bypass verification.

### Case `CLM_0138` (`cat10_conflicting_official_sources`)
- **Question:** [FAM_035] Under the 2023 PMFBY pilot addendum for Kharif perennial betelvine, is the maximum farmer premium 3.0% of Sum Insured?
- **Candidate Claim:** Under the 2023 PMFBY guidelines, the maximum farmer premium for Kharif perennial betelvine is 3.0% of Sum Insured or actuarial rate, whichever is less.
- **Abstention Reason:** `malformed_or_non_numerical_claim`
- **FieldGuard Rationale:** Claim parsing failed or numeric value/unit is corrupted/missing; malformed claims cannot bypass verification.

## 6. Residual Failure Modes and Boundary Analysis

### Residual Error `CLM_0025` (`cat01_supported_exact`)
- **Gold Verdict:** `SUPPORTED` | **Predicted:** `UNVERIFIABLE`
- **Rationale:** Claim parsing failed or numeric value/unit is corrupted/missing; malformed claims cannot bypass verification.

### Residual Error `CLM_0026` (`cat03_wrong_crop_category`)
- **Gold Verdict:** `WRONG_CONTEXT` | **Predicted:** `UNVERIFIABLE`
- **Rationale:** Claim parsing failed or numeric value/unit is corrupted/missing; malformed claims cannot bypass verification.

### Residual Error `CLM_0027` (`cat04_wrong_season`)
- **Gold Verdict:** `WRONG_CONTEXT` | **Predicted:** `UNVERIFIABLE`
- **Rationale:** Claim parsing failed or numeric value/unit is corrupted/missing; malformed claims cannot bypass verification.

### Residual Error `CLM_0028` (`cat02_contradicted_value`)
- **Gold Verdict:** `CONTRADICTED` | **Predicted:** `UNVERIFIABLE`
- **Rationale:** Claim parsing failed or numeric value/unit is corrupted/missing; malformed claims cannot bypass verification.

### Residual Error `CLM_0029` (`cat01_supported_exact`)
- **Gold Verdict:** `SUPPORTED` | **Predicted:** `UNVERIFIABLE`
- **Rationale:** Claim parsing failed or numeric value/unit is corrupted/missing; malformed claims cannot bypass verification.

