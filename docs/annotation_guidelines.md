# FieldGuard — Benchmark Annotation Guidelines & Adjudication Protocol

## 1. Purpose and Scope

This document defines the manual annotation protocol for the **FieldGuard** benchmark (`data/benchmark/claims.jsonl` and `data/benchmark/evidence.jsonl`), which evaluates condition-aware verification of numerical claims in Government-Scheme Question Answering (PMFBY).

## 2. Four Mandatory Gold Verdicts

Every benchmark case is assigned exactly one gold verdict:

1. **`SUPPORTED`**: Applicable, trusted official evidence establishes the numerical claim, including:
   - Exact or canonically equivalent numerical value and unit (e.g., `2%` = `2.0%`, `2 weeks` = `14 days`),
   - Matching scheme (`PMFBY`), rule parameter, crop category, season, and geography,
   - Matching denominator/basis (e.g., `% of Sum Insured` vs. `% of Threshold Yield`),
   - Compatible comparison operator (`<=` maximum ceiling vs. `>=` minimum floor) and mandatory qualification (`or actuarial rate, whichever is less`), and
   - Verified temporal applicability for the requested policy version or effective date.

2. **`CONTRADICTED`**: Applicable, trusted official evidence for the requested context establishes an incompatible numerical value, unit, basis/denominator, comparison operator, or violates a mandatory qualification (for example, asserting that a farmer *always* pays a flat 2.0% even when the actuarial rate is 1.2%, or asserting `0.02%` instead of `2.0%`).

3. **`WRONG_CONTEXT`**: Retrieved trusted official evidence contains the claimed numerical value, but demonstrates that the number belongs to a **different semantic or temporal context**—such as:
   - A different crop category (e.g., applying the 5.0% commercial/horticultural crop rate to Kharif food grains, or the 30.0% unirrigated subsidy cap to irrigated areas),
   - A different season (e.g., applying the 2.0% Kharif food-grain rate to Rabi wheat),
   - A different geography (e.g., applying the 90:10 North Eastern subsidy sharing ratio to General States),
   - A superseded historical policy version (e.g., applying the 2016 100% compulsory loanee enrolment rule to the 2023 Revamped Operational Guidelines), or
   - An unrelated administrative/outreach paragraph (e.g., mistaking the 30% women cultivator IEC outreach target for a farmer premium rate).

4. **`UNVERIFIABLE`**: Available evidence is insufficient to establish support or contradiction because:
   - Applicable evidence is absent from the corpus (e.g., non-covered aquaculture/livestock or another scheme like RWBCIS),
   - Relevant evidence is omitted from top-$k$ retrieved results (retrieval miss),
   - Official sources conflict without a superseding corrigendum (e.g., 5.0% vs. 3.0% in the betelvine pilot addendum),
   - The only matching source is unverified (`DOC_UNVERIFIED_PILOT_MEMO`),
   - The claim omits required conditions (e.g., asking if the PMFBY premium is 2.0% without specifying season or crop category), or
   - Temporal applicability is unresolved (e.g., asking for the latest current 2026 revised policy when only the 2023 guidelines and a December 2025 loss-assessment press release exist, or inferring an effective date from a publication date).

## 3. Core Annotation Rules

- **Absence is Never Contradiction:** Do not label a claim `CONTRADICTED` merely because supporting evidence is absent from the corpus or missed by retrieval; label it `UNVERIFIABLE`.
- **Null for Unspecified Conditions:** When a claim omits a condition (such as `season` or `crop_category`), record `null` in the structured claim record. Never fill missing fields by assumption.
- **No Self-Labelling:** Gold labels and rationales are authored directly from the official source tables and clauses (`DOC_PMFBY_OG_2023`, `DOC_PMFBY_OG_2016_HIST`, `DOC_PIB_2025_PRID2197713`, `DOC_PMFBY_FAQ_OFFICIAL`, `DOC_PMFBY_STATE_ADDENDUM_CONFLICT`), never produced by the verifier being evaluated.
- **Claim-Family Split Grouping:** All paraphrases and controlled context perturbations derived from the same base rule family share a `claim_family_id` and are assigned strictly to the same split (`dev` or `test`) to prevent data leakage.
