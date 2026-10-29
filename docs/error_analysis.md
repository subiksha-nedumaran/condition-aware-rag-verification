# FieldGuard — Evidence-Grounded Error Analysis (Phase 14)

## 1. Overview of Error Taxonomy

- **Evaluated Split Size:** 168 benchmark claims.
- **Wrong-Context False Supports in Baseline B (`numeric_only`) Caught by FieldGuard:** 38 cases.
- **Qualification & Denominator False Supports in Baseline C (`numeric_basic_context`) Caught by FieldGuard:** 18 cases.
- **Temporal / Policy-Version False Supports in Baseline C Caught by FieldGuard:** 18 cases.
- **Correct Abstentions (`UNVERIFIABLE`) by FieldGuard:** 30 cases.
- **Residual Verdict Errors in Full FieldGuard:** 10 cases.

## 2. Representative Wrong-Context Failures in Baselines (Corrected by FieldGuard)

### Case `CLM_0026` (`cat03_wrong_crop_category`)
- **Question:** For Kharif food grains under the 2023 PMFBY operational guidelines, is the maximum farmer premium 5.0%?
- **Candidate Claim:** For Kharif food grains under the 2023 PMFBY operational guidelines, the maximum farmer premium is 5.0% of Sum Insured or actuarial rate, whichever is less.
- **Numeric-Only Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `WRONG_CONTEXT`
- **Detected Context Mismatch:** `['crop_category_mismatch(claimed=food_grain_and_oilseed, rule=commercial_and_horticultural)']`
- **FieldGuard Rationale:** Claimed value (5.0 percent) belongs to a different context in rule RULE_OG2023_PREM_ANNUAL_COMM_HORT (EV_DOC_PMFBY_OG_2023_P4_TBL_OG2023_PREMIUM_RATES_R3): ['crop_category_mismatch(claimed=food_grain_and_oilseed, rule=commercial_and_horticultural)'].

### Case `CLM_0027` (`cat04_wrong_season`)
- **Question:** Under the 2023 PMFBY guidelines, is the maximum farmer premium for Kharif food grains capped at 1.5% of Sum Insured?
- **Candidate Claim:** Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 1.5% of Sum Insured or actuarial rate, whichever is less.
- **Numeric-Only Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `WRONG_CONTEXT`
- **Detected Context Mismatch:** `['season_mismatch(claimed=kharif, rule=rabi)', 'policy_version_mismatch(superseded_2016_historical_rule)']`
- **FieldGuard Rationale:** Claimed value (1.5 percent) belongs to a different context in rule RULE_OG2023_PREM_RABI_FOOD_OILSEED (EV_DOC_PMFBY_OG_2023_P4_TBL_OG2023_PREMIUM_RATES_R2): ['season_mismatch(claimed=kharif, rule=rabi)', 'policy_version_mismatch(superseded_2016_historical_rule)'].

### Case `CLM_0030` (`cat03_wrong_crop_category`)
- **Question:** For Kharif millets (such as bajra and sorghum) under the 2023 PMFBY operational guidelines, is the maximum farmer premium 5.0%?
- **Candidate Claim:** For Kharif millets (such as bajra and sorghum) under the 2023 PMFBY operational guidelines, the maximum farmer premium is 5.0% of Sum Insured or actuarial rate, whichever is less.
- **Numeric-Only Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `WRONG_CONTEXT`
- **Detected Context Mismatch:** `['crop_category_mismatch(claimed=food_grain_and_oilseed, rule=commercial_and_horticultural)']`
- **FieldGuard Rationale:** Claimed value (5.0 percent) belongs to a different context in rule RULE_OG2023_PREM_ANNUAL_COMM_HORT (EV_DOC_PMFBY_OG_2023_P4_TBL_OG2023_PREMIUM_RATES_R3): ['crop_category_mismatch(claimed=food_grain_and_oilseed, rule=commercial_and_horticultural)'].

### Case `CLM_0031` (`cat04_wrong_season`)
- **Question:** Under the 2023 PMFBY guidelines, is the maximum farmer premium for Kharif millets (such as bajra and sorghum) capped at 1.5% of Sum Insured?
- **Candidate Claim:** Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Kharif millets (such as bajra and sorghum) is 1.5% of Sum Insured or actuarial rate, whichever is less.
- **Numeric-Only Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `WRONG_CONTEXT`
- **Detected Context Mismatch:** `['season_mismatch(claimed=kharif, rule=rabi)']`
- **FieldGuard Rationale:** Claimed value (1.5 percent) belongs to a different context in rule RULE_OG2023_PREM_RABI_FOOD_OILSEED (EV_DOC_PMFBY_OG_2023_P4_TBL_OG2023_PREMIUM_RATES_R2): ['season_mismatch(claimed=kharif, rule=rabi)'].

### Case `CLM_0034` (`cat03_wrong_crop_category`)
- **Question:** For Kharif pulses and cereals (such as maize) under the 2023 PMFBY operational guidelines, is the maximum farmer premium 5.0%?
- **Candidate Claim:** For Kharif pulses and cereals (such as maize) under the 2023 PMFBY operational guidelines, the maximum farmer premium is 5.0% of Sum Insured or actuarial rate, whichever is less.
- **Numeric-Only Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `WRONG_CONTEXT`
- **Detected Context Mismatch:** `['crop_category_mismatch(claimed=food_grain_and_oilseed, rule=commercial_and_horticultural)', 'crop_category_mismatch(claimed=food_grain_and_oilseed, rule=perennial_betelvine_pilot)']`
- **FieldGuard Rationale:** Claimed value (5.0 percent) belongs to a different context in rule RULE_OG2023_PREM_ANNUAL_COMM_HORT (EV_DOC_PMFBY_OG_2023_P4_TBL_OG2023_PREMIUM_RATES_R3): ['crop_category_mismatch(claimed=food_grain_and_oilseed, rule=commercial_and_horticultural)', 'crop_category_mismatch(claimed=food_grain_and_oilseed, rule=perennial_betelvine_pilot)'].

## 3. Representative Qualification & Denominator Failures in Basic-Context Baseline

### Case `CLM_0102` (`cat05_qualification_violation`)
- **Question:** [FAM_026] Under the 2023 PMFBY operational guidelines, does a Kharif food-grain farmer always pay a flat 2.0% premium even if the actuarial rate is 1.2%?
- **Candidate Claim:** Under the 2023 PMFBY operational guidelines, a Kharif food-grain farmer always pays a fixed 2.0% of Sum Insured even when the actuarial rate is lower at 1.2%.
- **Basic-Context Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `CONTRADICTED`
- **FieldGuard Rationale:** Claim is CONTRADICTED in the requested context by rule RULE_OG2023_PROSE_PREM_KHARIF in EV_DOC_PMFBY_OG_2023_P4_CHUNK_2: ['qualification_violation(claim_asserts_unconditional_or_flat_rate, rule_requires=or_actuarial_rate_whichever_is_less)', 'qualification_violation(claimed=contradictory_unconditional_flat_rate, rule=or_actuarial_rate_whichever_is_less)'].

### Case `CLM_0103` (`cat05_qualification_violation`)
- **Question:** [FAM_026] For Rabi food-grain crops under the 2023 PMFBY guidelines, is the farmer premium 1.5% of Sum Insured or the actuarial rate, whichever is higher?
- **Candidate Claim:** Under the 2023 PMFBY guidelines, the farmer premium for Rabi food-grain crops is 1.5% of Sum Insured or the actuarial rate, whichever is higher.
- **Basic-Context Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `CONTRADICTED`
- **FieldGuard Rationale:** Claim is CONTRADICTED in the requested context by rule RULE_OG2023_PREM_RABI_FOOD_OILSEED in EV_DOC_PMFBY_OG_2023_P4_TBL_OG2023_PREMIUM_RATES_R2: ['operator_mismatch(claimed=ge, rule=le)', 'qualification_violation(claim_asserts_unconditional_or_flat_rate, rule_requires=or_actuarial_rate_whichever_is_less)', 'qualification_violation(claimed=contradictory_whichever_is_higher, rule=or_actuarial_rate_whichever_is_less)'].

### Case `CLM_0106` (`cat12_wrong_unit_denominator_operator`)
- **Question:** [FAM_027] Under the 2023 PMFBY guidelines, is the maximum farmer premium for Kharif food grains 2.0% of the Threshold Yield?
- **Candidate Claim:** Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 2.0% of the Threshold Yield.
- **Basic-Context Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `CONTRADICTED`
- **FieldGuard Rationale:** Claim is CONTRADICTED in the requested context by rule RULE_OG2023_PREM_KHARIF_FOOD_OILSEED in EV_DOC_PMFBY_OG_2023_P4_TBL_OG2023_PREMIUM_RATES_R1: ['basis_mismatch(claimed=threshold_yield, rule=sum_insured)'].

### Case `CLM_0107` (`cat12_wrong_unit_denominator_operator`)
- **Question:** [FAM_027] Under the 2023 PMFBY operational guidelines, is the farmer premium for Rabi food grains capped at 1.5% of the Gross Premium?
- **Candidate Claim:** Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Rabi food grains is 1.5% of the Gross Premium.
- **Basic-Context Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `CONTRADICTED`
- **FieldGuard Rationale:** Claim is CONTRADICTED in the requested context by rule RULE_OG2023_PREM_RABI_FOOD_OILSEED in EV_DOC_PMFBY_OG_2023_P4_TBL_OG2023_PREMIUM_RATES_R2: ['basis_mismatch(claimed=gross_premium, rule=sum_insured)'].

## 4. Representative Temporal & Policy-Version Failures in Basic-Context Baseline

### Case `CLM_0126` (`cat07_inappropriate_historical_version`)
- **Question:** [FAM_032] Under the 2023 revamped PMFBY operational guidelines, is scheme enrolment 100% compulsory for loanee farmers?
- **Candidate Claim:** Under the 2023 revamped PMFBY operational guidelines, scheme enrolment is 100.0% compulsory for loanee farmers.
- **Basic-Context Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `WRONG_CONTEXT` (`temporal_status=superseded_2016_historical_rule`)
- **FieldGuard Rationale:** Claimed value (100.0 percent) belongs to a different context in rule RULE_OG2016_HIST_PROSE_LOANEE_MANDATORY (EV_DOC_PMFBY_OG_2016_HIST_P1_CHUNK_1): ['policy_version_mismatch(superseded_2016_historical_rule)'].

### Case `CLM_0127` (`cat07_inappropriate_historical_version`)
- **Question:** [FAM_032] Under the 2023 PMFBY operational guidelines, is the Central Government's share of normal premium subsidy in North Eastern States 50.0% (50:50)?
- **Candidate Claim:** Under the 2023 PMFBY operational guidelines, the Central Government's share of normal premium subsidy in North Eastern States is 50.0% (50:50).
- **Basic-Context Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `WRONG_CONTEXT` (`temporal_status=matched_2023_guidelines`)
- **FieldGuard Rationale:** Claimed value (50.0 percent) belongs to a different context in rule RULE_OG2023_SUBSIDY_SHARE_GENERAL_STATES (EV_DOC_PMFBY_OG_2023_P5_TBL_OG2023_SUBSIDY_CAPS_R3): ['geography_mismatch(claimed=north_eastern_states, rule=general_states)', 'policy_version_mismatch(superseded_2016_historical_rule)'].

### Case `CLM_0128` (`cat07_inappropriate_historical_version`)
- **Question:** [FAM_032] Under the original 2016 PMFBY operational guidelines (in Kharif 2017), did the Central Government pay 90.0% of the premium subsidy in North Eastern States?
- **Candidate Claim:** Under the 2016 PMFBY operational guidelines in Kharif 2017, the Central Government paid 90.0% (90:10 ratio) of the normal premium subsidy in North Eastern States.
- **Basic-Context Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `WRONG_CONTEXT` (`temporal_status=date_outside_effective_window`)
- **FieldGuard Rationale:** Claimed value (90.0 percent) belongs to a different context in rule RULE_OG2023_SUBSIDY_SHARE_NER_STATES (EV_DOC_PMFBY_OG_2023_P5_TBL_OG2023_SUBSIDY_CAPS_R4): ['policy_version_mismatch(date_outside_effective_window)'].

### Case `CLM_0130` (`cat08_unresolved_effective_date_or_current`)
- **Question:** [FAM_033] Under the latest current 2026 revised PMFBY operational guidelines (following the December 2025 revision), is the maximum farmer premium for Kharif food grains still 2.0%?
- **Candidate Claim:** Under the latest current 2026 revised PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 2.0% of Sum Insured.
- **Basic-Context Baseline Verdict:** `SUPPORTED` (False Support)
- **FieldGuard Verdict:** `UNVERIFIABLE` (`temporal_status=unresolved_latest_policy_version`)
- **FieldGuard Rationale:** Temporal resolution requires abstention (UNVERIFIABLE): Requested latest/post-Dec-2025 full policy version cannot be established from historical 2023 guidelines.

## 5. Representative Correct Abstentions (`UNVERIFIABLE`: Missing Evidence, Conflicts, Retrieval Misses)

### Case `CLM_0130` (`cat08_unresolved_effective_date_or_current`)
- **Question:** [FAM_033] Under the latest current 2026 revised PMFBY operational guidelines (following the December 2025 revision), is the maximum farmer premium for Kharif food grains still 2.0%?
- **Candidate Claim:** Under the latest current 2026 revised PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 2.0% of Sum Insured.
- **Abstention Reason:** `unresolved_latest_policy_version`
- **FieldGuard Rationale:** Temporal resolution requires abstention (UNVERIFIABLE): Requested latest/post-Dec-2025 full policy version cannot be established from historical 2023 guidelines.

### Case `CLM_0131` (`cat08_unresolved_effective_date_or_current`)
- **Question:** [FAM_033] Did the 100.0% State-funded wild animal attack add-on cover in PIB release PRID=2197713 take legal effect on 2025-12-12?
- **Candidate Claim:** Under PMFBY, the 100.0% State-funded wild animal attack add-on cover announced in PIB release PRID=2197713 has a verified effective start date of 2025-12-12.
- **Abstention Reason:** `unresolved_effective_date_not_inferred_from_publication`
- **FieldGuard Rationale:** Temporal resolution requires abstention (UNVERIFIABLE): Document DOC_PIB_2025_PRID2197713 has publication_date=2025-12-12 but effective_from=None. FieldGuard never infers an effective date from a publication date.

### Case `CLM_0132` (`cat08_unresolved_effective_date_or_current`)
- **Question:** [FAM_033] Based strictly on the undated official FAQ page, can we verify that the 2.0% Kharif food-grain premium ceiling was effective on 2023-07-01 under the 2023 guidelines?
- **Candidate Claim:** Under the 2023 PMFBY operational guidelines effective on 2023-07-01, the maximum farmer premium for Kharif food grains is 2.0% of Sum Insured.
- **Abstention Reason:** `missing_effective_date`
- **FieldGuard Rationale:** Temporal resolution requires abstention (UNVERIFIABLE): Rule effective_from date is unknown (null); cannot verify date-specific applicability.

### Case `CLM_0137` (`cat10_conflicting_official_sources`)
- **Question:** [FAM_035] Under the 2023 PMFBY pilot addendum for Kharif perennial betelvine, is the maximum farmer premium 5.0% of Sum Insured?
- **Candidate Claim:** Under the 2023 PMFBY guidelines, the maximum farmer premium for Kharif perennial betelvine is 5.0% of Sum Insured or actuarial rate, whichever is less.
- **Abstention Reason:** `conflicting_official_sources`
- **FieldGuard Rationale:** Conflicting official sources detected in ['EV_DOC_PMFBY_STATE_ADDENDUM_CONFLICT_P1_TBL_ADDENDUM_BETELVINE_CONFLICT_R1', 'EV_DOC_PMFBY_STATE_ADDENDUM_CONFLICT_P1_TBL_ADDENDUM_BETELVINE_CONFLICT_R2'] for context (season=kharif, crop=perennial_betelvine_pilot). FieldGuard preserves both records and abstains (UNVERIFIABLE) rather than silently selecting one.

### Case `CLM_0138` (`cat10_conflicting_official_sources`)
- **Question:** [FAM_035] Under the 2023 PMFBY pilot addendum for Kharif perennial betelvine, is the maximum farmer premium 3.0% of Sum Insured?
- **Candidate Claim:** Under the 2023 PMFBY guidelines, the maximum farmer premium for Kharif perennial betelvine is 3.0% of Sum Insured or actuarial rate, whichever is less.
- **Abstention Reason:** `conflicting_official_sources`
- **FieldGuard Rationale:** Conflicting official sources detected in ['EV_DOC_PMFBY_STATE_ADDENDUM_CONFLICT_P1_TBL_ADDENDUM_BETELVINE_CONFLICT_R1', 'EV_DOC_PMFBY_STATE_ADDENDUM_CONFLICT_P1_TBL_ADDENDUM_BETELVINE_CONFLICT_R2'] for context (season=kharif, crop=perennial_betelvine_pilot). FieldGuard preserves both records and abstains (UNVERIFIABLE) rather than silently selecting one.

## 6. Residual Failure Modes and Boundary Analysis

### Residual Error `CLM_0028` (`cat02_contradicted_value`)
- **Gold Verdict:** `CONTRADICTED` | **Predicted:** `WRONG_CONTEXT`
- **Rationale:** Claimed value (3.0 percent) belongs to a different context in rule RULE_ADDENDUM_BETELVINE_3PCT (EV_DOC_PMFBY_STATE_ADDENDUM_CONFLICT_P1_TBL_ADDENDUM_BETELVINE_CONFLICT_R2): ['crop_category_mismatch(claimed=food_grain_and_oilseed, rule=perennial_betelvine_pilot)'].

### Residual Error `CLM_0122` (`cat01_supported_exact`)
- **Gold Verdict:** `SUPPORTED` | **Predicted:** `CONTRADICTED`
- **Rationale:** Claim is CONTRADICTED in the requested context by rule RULE_OG2023_MID_SEASON_ADVERSITY_RELIEF in EV_DOC_PMFBY_OG_2023_P6_TBL_OG2023_INDEMNITY_CLAIM_RULES_R4: ['basis_mismatch(claimed=threshold_yield, rule=likely_claims)'].

### Residual Error `CLM_0124` (`cat05_qualification_violation`)
- **Gold Verdict:** `CONTRADICTED` | **Predicted:** `SUPPORTED`
- **Rationale:** Claim is SUPPORTED by verified rule RULE_OG2023_PREVENTED_SOWING_PAYOUT in EV_DOC_PMFBY_OG_2023_P6_TBL_OG2023_INDEMNITY_CLAIM_RULES_R3 (document=DOC_PMFBY_OG_2023, temporal_status=matched_2023_guidelines).

### Residual Error `CLM_0144` (`cat15_irrelevant_lexical_similarity`)
- **Gold Verdict:** `UNVERIFIABLE` | **Predicted:** `WRONG_CONTEXT`
- **Rationale:** Claimed number (2.0%) appears in unrelated administrative/outreach paragraph EV_DOC_PMFBY_PORTAL_OVERVIEW_HTML_CHUNK_2 rather than an applicable policy rule for None.

### Residual Error `CLM_0170` (`cat01_supported_exact`)
- **Gold Verdict:** `SUPPORTED` | **Predicted:** `CONTRADICTED`
- **Rationale:** Claim is CONTRADICTED in the requested context by rule RULE_OG2023_MID_SEASON_ADVERSITY_RELIEF in EV_DOC_PMFBY_OG_2023_P6_TBL_OG2023_INDEMNITY_CLAIM_RULES_R4: ['basis_mismatch(claimed=threshold_yield, rule=likely_claims)'].

