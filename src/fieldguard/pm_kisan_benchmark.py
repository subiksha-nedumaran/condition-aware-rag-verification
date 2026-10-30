"""PM-KISAN gold-annotated benchmark construction and leakage-free cluster splitting."""

from __future__ import annotations

import csv
import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from fieldguard.benchmark_builder import BenchmarkClaimRecord
from fieldguard.verdicts import Verdict


def generate_pm_kisan_benchmark_claims() -> list[BenchmarkClaimRecord]:
    """
    Construct 80 manually curated, gold-annotated numerical claim cases for PM-KISAN
    across 20 claim families (4 variants per family) covering all 4 verdict classes:
    SUPPORTED, CONTRADICTED, WRONG_CONTEXT, and UNVERIFIABLE.
    Cluster-stratified by claim family into 40 Dev claims (Families 1-10) and
    40 Frozen Test claims (Families 11-20).
    """
    records: list[BenchmarkClaimRecord] = []

    def add(
        cid: str,
        fam_id: str,
        split: str,
        question: str,
        claim: str,
        val: float | None,
        unit: str | None,
        op: str | None,
        rule_param: str,
        entity: str | None,
        freq: str | None,
        qual: str | None,
        ver_req: str | None,
        verdict: str,
        ev_ids: list[str],
        rationale: str,
        claim_type: str = "numerical_factual",
    ) -> None:
        rec = BenchmarkClaimRecord(
            claim_id=cid,
            question=question,
            candidate_claim=claim,
            claimed_value=val,
            claimed_unit=unit,
            numeric_operator=op,
            scheme="PM_KISAN",
            crop_category=entity,
            season=freq,
            geography="all_india",
            qualification=qual,
            requested_policy_version=ver_req,
            requested_effective_date=None,
            claim_type=claim_type,
            gold_verdict=verdict,
            gold_evidence_ids=ev_ids,
            gold_rationale=rationale,
            case_origin="official_pm_kisan_guidelines_2020",
            annotation_status="gold_verified",
            annotator_notes="Manually curated for PM-KISAN Stage 2 benchmark",
            claim_family_id=fam_id,
            split=split,
            rule_parameter=rule_param,
        )
        records.append(rec)

    # -------------------------------------------------------------
    # DEVELOPMENT SPLIT: FAMILIES 1 to 10 (40 cases)
    # -------------------------------------------------------------

    # FAM_PMK_01: Annual Income Support (Rs 6000 / year)
    add(
        "PMK_DEV_001", "FAM_PMK_01", "dev",
        "Under PM-KISAN, what is the annual financial assistance provided to eligible farmer families?",
        "Under PM-KISAN, eligible landholding farmer families receive an annual financial benefit of Rs 6000.",
        6000.0, "rupees", "eq", "annual_income_support", "all_landholding_farmers", "annual",
        None, "pmkisan_current", Verdict.SUPPORTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R4"],
        "Supported by Table 1 Row 4 of PM-KISAN Guidelines: Rs 6000 annual total."
    )
    add(
        "PMK_DEV_002", "FAM_PMK_01", "dev",
        "Under PM-KISAN, what is the annual financial assistance provided to eligible farmer families?",
        "Under PM-KISAN, eligible farmer families receive Rs 10000 per year.",
        10000.0, "rupees", "eq", "annual_income_support", "all_landholding_farmers", "annual",
        None, "pmkisan_current", Verdict.CONTRADICTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R4"],
        "Contradicted: Annual benefit is Rs 6000, not Rs 10000."
    )
    add(
        "PMK_DEV_003", "FAM_PMK_01", "dev",
        "Under PM-KISAN, what is the financial assistance provided per four-monthly instalment?",
        "Under PM-KISAN, eligible farmers receive Rs 6000 per instalment.",
        6000.0, "rupees", "eq", "instalment_amount", "all_landholding_farmers", "per_instalment",
        None, "pmkisan_current", Verdict.WRONG_CONTEXT.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R4", "EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R1"],
        "Wrong context: Rs 6000 is the annual total, not the per-instalment amount (which is Rs 2000)."
    )
    add(
        "PMK_DEV_004", "FAM_PMK_01", "dev",
        "Under PM-KISAN, what is the annual financial support provided to non-agricultural urban traders?",
        "Urban commercial traders receive an annual financial benefit of Rs 6000 under PM-KISAN.",
        6000.0, "rupees", "eq", "annual_income_support", "non_agricultural_traders", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Urban traders are outside the scheme scope; no applicable rule in official guidelines."
    )

    # FAM_PMK_02: Instalment Amount (Rs 2000 / instalment)
    add(
        "PMK_DEV_005", "FAM_PMK_02", "dev",
        "What is the amount disbursed per instalment under PM-KISAN?",
        "Under PM-KISAN, each four-monthly instalment is Rs 2000 per eligible farmer family.",
        2000.0, "rupees", "eq", "instalment_amount", "all_landholding_farmers", "per_instalment",
        None, "pmkisan_current", Verdict.SUPPORTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R1"],
        "Supported by Table 1 Row 1: Rs 2000 per instalment."
    )
    add(
        "PMK_DEV_006", "FAM_PMK_02", "dev",
        "What is the amount disbursed per instalment under PM-KISAN?",
        "Under PM-KISAN, each instalment amount is Rs 3000.",
        3000.0, "rupees", "eq", "instalment_amount", "all_landholding_farmers", "per_instalment",
        None, "pmkisan_current", Verdict.CONTRADICTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R1"],
        "Contradicted: Instalment is Rs 2000, not Rs 3000."
    )
    add(
        "PMK_DEV_007", "FAM_PMK_02", "dev",
        "What is the total annual income support under PM-KISAN?",
        "Under PM-KISAN, the total annual benefit is Rs 2000 per farmer family.",
        2000.0, "rupees", "eq", "annual_income_support", "all_landholding_farmers", "annual",
        None, "pmkisan_current", Verdict.WRONG_CONTEXT.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R1", "EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R4"],
        "Wrong context: Rs 2000 is the instalment amount, not the annual total (Rs 6000)."
    )
    add(
        "PMK_DEV_008", "FAM_PMK_02", "dev",
        "What is the monthly bonus stipend for rural agricultural trainees under PM-KISAN?",
        "Agricultural trainees receive a monthly stipend of Rs 2000 under PM-KISAN.",
        2000.0, "rupees", "eq", "trainee_stipend", "agricultural_trainees", "monthly",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: PM-KISAN does not provide trainee stipends."
    )

    # FAM_PMK_03: Instalments per Year (3 instalments)
    add(
        "PMK_DEV_009", "FAM_PMK_03", "dev",
        "How many instalments are paid in a financial year under PM-KISAN?",
        "Under PM-KISAN, the financial benefit is payable in 3 equal instalments per year.",
        3.0, "instalments", "eq", "instalments_per_year", "all_landholding_farmers", "annual",
        None, "pmkisan_current", Verdict.SUPPORTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_CHUNK_1"],
        "Supported by Clause 2.1: Payable in three equal instalments."
    )
    add(
        "PMK_DEV_010", "FAM_PMK_03", "dev",
        "How many instalments are paid in a financial year under PM-KISAN?",
        "Under PM-KISAN, the financial benefit is disbursed in 4 quarterly instalments per year.",
        4.0, "instalments", "eq", "instalments_per_year", "all_landholding_farmers", "annual",
        None, "pmkisan_current", Verdict.CONTRADICTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_CHUNK_1"],
        "Contradicted: Paid in 3 instalments, not 4."
    )
    add(
        "PMK_DEV_011", "FAM_PMK_03", "dev",
        "How many hectares of land can an eligible farmer own under current PM-KISAN guidelines?",
        "Under PM-KISAN, eligible farmers can own a maximum of 3 hectares of land.",
        3.0, "hectares", "le", "landholding_eligibility_cap_ha", "all_landholding_farmers", "annual",
        None, "pmkisan_current", Verdict.WRONG_CONTEXT.value,
        ["EV_DOC_PMKISAN_OG_2020_P3_CHUNK_1"],
        "Wrong context: 3 is the number of instalments, not a land ceiling (which was removed in 2019)."
    )
    add(
        "PMK_DEV_012", "FAM_PMK_03", "dev",
        "How many solar water pumps are subsidized per village under PM-KISAN?",
        "Under PM-KISAN, each village receives 3 subsidized solar water pumps.",
        3.0, "dimensionless", "eq", "solar_pumps", "village_community", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Solar pumps are under PM-KUSUM, not PM-KISAN."
    )

    # FAM_PMK_04: Instalment Window (4 months)
    add(
        "PMK_DEV_013", "FAM_PMK_04", "dev",
        "What is the duration of each instalment period under PM-KISAN?",
        "Under PM-KISAN, each instalment covers a period of 4 months.",
        4.0, "months", "eq", "instalment_period_months", "all_landholding_farmers", "per_instalment",
        None, "pmkisan_current", Verdict.SUPPORTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_CHUNK_1"],
        "Supported by Clause 2.1: Four-monthly instalment periods."
    )
    add(
        "PMK_DEV_014", "FAM_PMK_04", "dev",
        "What is the duration of each instalment period under PM-KISAN?",
        "Under PM-KISAN, instalments are released every 6 months bi-annually.",
        6.0, "months", "eq", "instalment_period_months", "all_landholding_farmers", "per_instalment",
        None, "pmkisan_current", Verdict.CONTRADICTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_CHUNK_1"],
        "Contradicted: Each instalment period is 4 months, not 6 months."
    )
    add(
        "PMK_DEV_015", "FAM_PMK_04", "dev",
        "How many instalments are paid each year under PM-KISAN?",
        "Under PM-KISAN, farmers receive 4 instalments every year.",
        4.0, "instalments", "eq", "instalments_per_year", "all_landholding_farmers", "annual",
        None, "pmkisan_current", Verdict.WRONG_CONTEXT.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_CHUNK_1"],
        "Wrong context: 4 is the number of months per instalment period, not the number of instalments per year."
    )
    add(
        "PMK_DEV_016", "FAM_PMK_04", "dev",
        "What is the mandatory warehouse drying time for PM-KISAN grain storage?",
        "Under PM-KISAN, harvested grain must be dried for 4 months in warehouses.",
        4.0, "months", "eq", "grain_drying", "harvested_grain", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Warehouse storage is unrelated to PM-KISAN direct cash transfer."
    )

    # FAM_PMK_05: Historical 2 ha Land Ceiling (Feb 2019 Launch Era)
    add(
        "PMK_DEV_017", "FAM_PMK_05", "dev",
        "Under the original February 2019 launch guidelines of PM-KISAN, what was the landholding ceiling for eligibility?",
        "Under the original February 2019 launch guidelines of PM-KISAN, eligibility was capped at 2.0 hectares.",
        2.0, "hectares", "le", "landholding_eligibility_cap_ha", "small_and_marginal_farmers", "annual",
        None, "2019_original_pmkisan", Verdict.SUPPORTED.value,
        ["EV_DOC_PMKISAN_OG_2019_HIST_P1_TBL_PMKISAN_2019_ELIGIBILITY_R1"],
        "Supported by 2019 launch guidelines Table 1: Landholding ceiling of up to 2.0 ha for SMFs."
    )
    add(
        "PMK_DEV_018", "FAM_PMK_05", "dev",
        "Under the original February 2019 launch guidelines of PM-KISAN, what was the landholding ceiling for eligibility?",
        "Under the original February 2019 guidelines of PM-KISAN, eligibility was capped at 5.0 hectares.",
        5.0, "hectares", "le", "landholding_eligibility_cap_ha", "small_and_marginal_farmers", "annual",
        None, "2019_original_pmkisan", Verdict.CONTRADICTED.value,
        ["EV_DOC_PMKISAN_OG_2019_HIST_P1_TBL_PMKISAN_2019_ELIGIBILITY_R1"],
        "Contradicted: Original ceiling was 2.0 hectares (5 acres), not 5.0 hectares."
    )
    add(
        "PMK_DEV_019", "FAM_PMK_05", "dev",
        "Under current active PM-KISAN guidelines, what is the maximum landholding allowed to receive benefits?",
        "Under current PM-KISAN guidelines, eligibility is restricted to farmers holding up to 2.0 hectares.",
        2.0, "hectares", "le", "landholding_eligibility_cap_ha", "all_landholding_farmers", "annual",
        None, "pmkisan_current", Verdict.WRONG_CONTEXT.value,
        ["EV_DOC_PMKISAN_OG_2019_HIST_P1_TBL_PMKISAN_2019_ELIGIBILITY_R1", "EV_DOC_PMKISAN_OG_2020_P3_CHUNK_1"],
        "Wrong context / temporal mismatch: The 2.0 ha ceiling applied only in the Feb 2019 launch era; the June 2019 cabinet decision expanded coverage to all landholders."
    )
    add(
        "PMK_DEV_020", "FAM_PMK_05", "dev",
        "Under the unverified 2028 future draft of PM-KISAN, what is the proposed land ceiling?",
        "Under the 2028 future draft guidelines, PM-KISAN will restrict eligibility to 2.0 hectares.",
        2.0, "hectares", "le", "landholding_eligibility_cap_ha", "all_landholding_farmers", "annual",
        None, "2028_unverified_draft", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Speculative future policy draft cannot be verified from active corpus."
    )

    # FAM_PMK_06: Universal Landholder Coverage (June 2019 Onwards)
    add(
        "PMK_DEV_021", "FAM_PMK_06", "dev",
        "Do medium and large landholding farmers qualify for PM-KISAN benefits under revised guidelines?",
        "Under revised PM-KISAN guidelines, all landholding farmer families are eligible regardless of land size.",
        6000.0, "rupees", "eq", "annual_income_support", "all_landholding_farmers", "annual",
        None, "pmkisan_current", Verdict.SUPPORTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P3_CHUNK_1", "EV_DOC_PMKISAN_PIB_JUN2019_P1_CHUNK_1"],
        "Supported by Clause 3.1 and Cabinet Decision: Universal coverage for all landholder farmer families."
    )
    add(
        "PMK_DEV_022", "FAM_PMK_06", "dev",
        "Do medium and large landholding farmers qualify for PM-KISAN benefits under revised guidelines?",
        "Medium and large farmers with over 2 hectares receive Rs 0 under revised PM-KISAN guidelines.",
        0.0, "rupees", "eq", "annual_income_support", "medium_and_large_farmers", "annual",
        None, "pmkisan_current", Verdict.CONTRADICTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P3_CHUNK_1"],
        "Contradicted: Medium and large farmers are eligible for the full Rs 6000 annual benefit post-June 2019."
    )
    add(
        "PMK_DEV_023", "FAM_PMK_06", "dev",
        "Under PM-KISAN, what is the annual financial support provided to tenant farmers?",
        "Under PM-KISAN, tenant farmers receive an annual income support of Rs 6000.",
        6000.0, "rupees", "eq", "annual_income_support", "tenant_farmer", "annual",
        None, "pmkisan_current", Verdict.WRONG_CONTEXT.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R4", "EV_DOC_PMKISAN_OG_2020_P3_CHUNK_2"],
        "Wrong context: Rs 6000 applies only to landholding owners; tenant farmers are explicitly ineligible."
    )
    add(
        "PMK_DEV_024", "FAM_PMK_06", "dev",
        "What is the annual financial support for agricultural universities under PM-KISAN?",
        "Agricultural universities receive an annual research grant of Rs 6000 under PM-KISAN.",
        6000.0, "rupees", "eq", "university_grant", "agricultural_universities", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Universities are not beneficiary farmer families."
    )

    # FAM_PMK_07: Tenant Farmers Ineligibility
    add(
        "PMK_DEV_025", "FAM_PMK_07", "dev",
        "Are tenant farmers without land ownership title eligible for financial benefits under PM-KISAN?",
        "Tenant farmers without cultivable land ownership are ineligible (Rs 0 benefit) under PM-KISAN.",
        0.0, "rupees", "eq", "annual_income_support", "tenant_farmer", "annual",
        None, "pmkisan_current", Verdict.SUPPORTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P3_CHUNK_2", "EV_DOC_PMKISAN_FAQ_OFFICIAL_P1_CHUNK_1"],
        "Supported by Clause 3.2 and FAQ Q1: Tenant farmers are not eligible."
    )
    add(
        "PMK_DEV_026", "FAM_PMK_07", "dev",
        "Are tenant farmers without land ownership title eligible for financial benefits under PM-KISAN?",
        "Tenant farmers are eligible and receive Rs 2000 per instalment under PM-KISAN.",
        2000.0, "rupees", "eq", "instalment_amount", "tenant_farmer", "per_instalment",
        None, "pmkisan_current", Verdict.CONTRADICTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P3_CHUNK_2"],
        "Contradicted: Tenant farmers do not receive instalments under PM-KISAN."
    )
    add(
        "PMK_DEV_027", "FAM_PMK_07", "dev",
        "Under PM-KISAN, what is the annual financial benefit for tenant farmers?",
        "Tenant farmers receive Rs 6000 per year under the PM-KISAN scheme.",
        6000.0, "rupees", "eq", "annual_income_support", "tenant_farmer", "annual",
        None, "pmkisan_current", Verdict.WRONG_CONTEXT.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R4", "EV_DOC_PMKISAN_OG_2020_P3_CHUNK_2"],
        "Wrong context: Rs 6000 belongs to landholding owners, not tenant farmers."
    )
    add(
        "PMK_DEV_028", "FAM_PMK_07", "dev",
        "What is the maximum crop loan interest waiver for tenant farmers under PM-KISAN?",
        "Tenant farmers receive a crop loan interest waiver of 4 percent under PM-KISAN.",
        4.0, "percent", "le", "interest_waiver", "tenant_farmer", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Interest subvention is handled under ISS, not PM-KISAN."
    )

    # FAM_PMK_08: Landless Agricultural Labourers
    add(
        "PMK_DEV_029", "FAM_PMK_08", "dev",
        "Are landless agricultural labourers eligible to receive PM-KISAN income support?",
        "Landless agricultural labourers are ineligible (Rs 0 benefit) under PM-KISAN guidelines.",
        0.0, "rupees", "eq", "annual_income_support", "agricultural_laborer", "annual",
        None, "pmkisan_current", Verdict.SUPPORTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P3_CHUNK_2"],
        "Supported by Clause 3.2: Landless agricultural labourers are not eligible."
    )
    add(
        "PMK_DEV_030", "FAM_PMK_08", "dev",
        "Are landless agricultural labourers eligible to receive PM-KISAN income support?",
        "Landless agricultural labourers receive Rs 6000 per annum under PM-KISAN.",
        6000.0, "rupees", "eq", "annual_income_support", "agricultural_laborer", "annual",
        None, "pmkisan_current", Verdict.CONTRADICTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P3_CHUNK_2"],
        "Contradicted: Clause 3.2 explicitly excludes landless labourers."
    )
    add(
        "PMK_DEV_031", "FAM_PMK_08", "dev",
        "What is the instalment amount for landless agricultural labourers under PM-KISAN?",
        "Landless agricultural labourers receive Rs 2000 per instalment under PM-KISAN.",
        2000.0, "rupees", "eq", "instalment_amount", "agricultural_laborer", "per_instalment",
        None, "pmkisan_current", Verdict.WRONG_CONTEXT.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R1", "EV_DOC_PMKISAN_OG_2020_P3_CHUNK_2"],
        "Wrong context: The Rs 2000 instalment applies to landholders, not landless labourers."
    )
    add(
        "PMK_DEV_032", "FAM_PMK_08", "dev",
        "What is the daily minimum wage supplement for landless labourers under PM-KISAN?",
        "Under PM-KISAN, landless labourers receive a daily wage supplement of Rs 100.",
        100.0, "rupees", "eq", "wage_supplement", "agricultural_laborer", "daily",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Wage supplements fall under MGNREGS, not PM-KISAN."
    )

    # FAM_PMK_09: Institutional Landholders Exclusion
    add(
        "PMK_DEV_033", "FAM_PMK_09", "dev",
        "Are institutional landholders eligible to receive benefits under PM-KISAN?",
        "All institutional landholders are statutorily excluded (Rs 0 benefit) from PM-KISAN.",
        0.0, "rupees", "eq", "statutory_exclusion", "institutional_landholder", "annual",
        None, "pmkisan_current", Verdict.SUPPORTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R1"],
        "Supported by Table 2 Row 1: Institutional landholders are excluded."
    )
    add(
        "PMK_DEV_034", "FAM_PMK_09", "dev",
        "Are institutional landholders eligible to receive benefits under PM-KISAN?",
        "Institutional landholders are fully eligible and receive Rs 6000 annually under PM-KISAN.",
        6000.0, "rupees", "eq", "annual_income_support", "institutional_landholder", "annual",
        None, "pmkisan_current", Verdict.CONTRADICTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R1"],
        "Contradicted: Institutional landholders are disqualified under Clause 4.1."
    )
    add(
        "PMK_DEV_035", "FAM_PMK_09", "dev",
        "Under PM-KISAN, what is the annual financial benefit for corporate agricultural institutions?",
        "Corporate agricultural institutions receive Rs 6000 per year under PM-KISAN.",
        6000.0, "rupees", "eq", "annual_income_support", "institutional_landholder", "annual",
        None, "pmkisan_current", Verdict.WRONG_CONTEXT.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R4", "EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R1"],
        "Wrong context: Rs 6000 applies to family farmers; corporate institutions are statutorily excluded."
    )
    add(
        "PMK_DEV_036", "FAM_PMK_09", "dev",
        "What is the corporate tax deduction rate for institutional farms under PM-KISAN?",
        "Institutional farms receive a corporate tax deduction of 15 percent under PM-KISAN.",
        15.0, "percent", "eq", "tax_deduction", "institutional_landholder", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Tax deductions are not part of PM-KISAN."
    )

    # FAM_PMK_10: Constitutional Post Holders Exclusion
    add(
        "PMK_DEV_037", "FAM_PMK_10", "dev",
        "Are former or present holders of constitutional posts eligible for PM-KISAN?",
        "Former and present holders of constitutional posts are statutorily excluded from PM-KISAN.",
        0.0, "rupees", "eq", "statutory_exclusion", "constitutional_post_holder", "annual",
        None, "pmkisan_current", Verdict.SUPPORTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R2"],
        "Supported by Table 2 Row 2: Constitutional post holders are excluded."
    )
    add(
        "PMK_DEV_038", "FAM_PMK_10", "dev",
        "Are former or present holders of constitutional posts eligible for PM-KISAN?",
        "Holders of constitutional posts are eligible and receive Rs 6000 per annum under PM-KISAN.",
        6000.0, "rupees", "eq", "annual_income_support", "constitutional_post_holder", "annual",
        None, "pmkisan_current", Verdict.CONTRADICTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R2"],
        "Contradicted: Constitutional post holders are disqualified under Clause 4.1."
    )
    add(
        "PMK_DEV_039", "FAM_PMK_10", "dev",
        "What is the annual benefit for ministers and members of parliament who own farmland under PM-KISAN?",
        "Ministers and Members of Parliament who own agricultural land receive Rs 6000 per year under PM-KISAN.",
        6000.0, "rupees", "eq", "annual_income_support", "constitutional_post_holder", "annual",
        None, "pmkisan_current", Verdict.WRONG_CONTEXT.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R4", "EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R3"],
        "Wrong context: Rs 6000 is for eligible non-excluded farmers; ministers and MPs are excluded."
    )
    add(
        "PMK_DEV_040", "FAM_PMK_10", "dev",
        "What is the official protocol vehicle allowance for constitutional post holders under PM-KISAN?",
        "Constitutional post holders receive a protocol vehicle allowance of Rs 10000 under PM-KISAN.",
        10000.0, "rupees", "eq", "vehicle_allowance", "constitutional_post_holder", "monthly",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Protocol vehicle allowances are unrelated to PM-KISAN."
    )

    # -------------------------------------------------------------
    # FROZEN TEST SPLIT: FAMILIES 11 to 20 (40 cases)
    # -------------------------------------------------------------

    # FAM_PMK_11: Government Employees & Class IV Exemption
    add(
        "PMK_TEST_041", "FAM_PMK_11", "test",
        "Are serving or retired government officers and employees eligible for PM-KISAN?",
        "Serving or retired government employees (excluding Class IV / Group D) are excluded from PM-KISAN.",
        0.0, "rupees", "eq", "statutory_exclusion", "government_employee", "annual",
        None, "pmkisan_current", Verdict.SUPPORTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R4"],
        "Supported by Table 2 Row 4: Govt employees excluded, with Class IV / Group D exemption."
    )
    add(
        "PMK_TEST_042", "FAM_PMK_11", "test",
        "Are serving or retired government officers and employees eligible for PM-KISAN?",
        "All government officers are eligible and receive Rs 6000 per annum under PM-KISAN.",
        6000.0, "rupees", "eq", "annual_income_support", "government_employee", "annual",
        None, "pmkisan_current", Verdict.CONTRADICTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R4"],
        "Contradicted: Govt employees are disqualified under Clause 4.1."
    )
    add(
        "PMK_TEST_043", "FAM_PMK_11", "test",
        "What is the annual benefit for central government gazetted officers who own agricultural land?",
        "Central government gazetted officers who own land receive Rs 6000 per year under PM-KISAN.",
        6000.0, "rupees", "eq", "annual_income_support", "government_employee", "annual",
        None, "pmkisan_current", Verdict.WRONG_CONTEXT.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R4", "EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R4"],
        "Wrong context: Rs 6000 belongs to non-excluded landholding families; gazetted officers are excluded."
    )
    add(
        "PMK_TEST_044", "FAM_PMK_11", "test",
        "What is the housing loan subsidy percentage for government employees under PM-KISAN?",
        "Government employees receive an 8 percent housing loan subsidy under PM-KISAN.",
        8.0, "percent", "eq", "housing_subsidy", "government_employee", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Housing loans are outside PM-KISAN."
    )

    # FAM_PMK_12: Superannuated Pensioners Threshold (Rs 10,000 / month)
    add(
        "PMK_TEST_045", "FAM_PMK_12", "test",
        "What is the monthly pension threshold that disqualifies retired pensioners from PM-KISAN?",
        "Retired pensioners with monthly pension of Rs 10000 or more are statutorily excluded from PM-KISAN.",
        10000.0, "rupees", "ge", "statutory_exclusion_pension_threshold", "pensioners", "monthly",
        None, "pmkisan_current", Verdict.SUPPORTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R5"],
        "Supported by Table 2 Row 5: Pension >= Rs 10000 is an exclusion criterion."
    )
    add(
        "PMK_TEST_046", "FAM_PMK_12", "test",
        "What is the monthly pension threshold that disqualifies retired pensioners from PM-KISAN?",
        "Retired pensioners with monthly pension of Rs 5000 or more are disqualified from PM-KISAN.",
        5000.0, "rupees", "ge", "statutory_exclusion_pension_threshold", "pensioners", "monthly",
        None, "pmkisan_current", Verdict.CONTRADICTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R5"],
        "Contradicted: Threshold is Rs 10000, not Rs 5000."
    )
    add(
        "PMK_TEST_047", "FAM_PMK_12", "test",
        "What is the financial assistance provided per instalment under PM-KISAN?",
        "Under PM-KISAN, each instalment amount is Rs 10000.",
        10000.0, "rupees", "eq", "instalment_amount", "all_landholding_farmers", "per_instalment",
        None, "pmkisan_current", Verdict.WRONG_CONTEXT.value,
        ["EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R5", "EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R1"],
        "Wrong context: Rs 10000 is the monthly pension exclusion threshold, not the instalment benefit (which is Rs 2000)."
    )
    add(
        "PMK_TEST_048", "FAM_PMK_12", "test",
        "What is the medical insurance allowance for pensioners under PM-KISAN?",
        "Pensioners receive an annual medical allowance of Rs 10000 under PM-KISAN.",
        10000.0, "rupees", "eq", "medical_allowance", "pensioners", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Medical allowances are not part of PM-KISAN."
    )

    # FAM_PMK_13: Income Tax Payees Exclusion
    add(
        "PMK_TEST_049", "FAM_PMK_13", "test",
        "Are individuals who paid income tax in the last assessment year eligible for PM-KISAN?",
        "Individuals who paid income tax in the last assessment year are statutorily excluded from PM-KISAN.",
        0.0, "rupees", "eq", "statutory_exclusion", "income_tax_payee", "annual",
        None, "pmkisan_current", Verdict.SUPPORTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R6"],
        "Supported by Table 2 Row 6: Income tax payees of last assessment year excluded."
    )
    add(
        "PMK_TEST_050", "FAM_PMK_13", "test",
        "Are individuals who paid income tax in the last assessment year eligible for PM-KISAN?",
        "Income tax payees are eligible and receive an annual benefit of Rs 6000 under PM-KISAN.",
        6000.0, "rupees", "eq", "annual_income_support", "income_tax_payee", "annual",
        None, "pmkisan_current", Verdict.CONTRADICTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R6"],
        "Contradicted: Income tax payees are disqualified under Clause 4.1."
    )
    add(
        "PMK_TEST_051", "FAM_PMK_13", "test",
        "Under PM-KISAN, what is the annual financial support for taxpayers owning agricultural land?",
        "Taxpayers who paid income tax receive Rs 6000 per year under PM-KISAN.",
        6000.0, "rupees", "eq", "annual_income_support", "income_tax_payee", "annual",
        None, "pmkisan_current", Verdict.WRONG_CONTEXT.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R4", "EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R6"],
        "Wrong context: Rs 6000 is for non-taxpayers; income tax payees are excluded."
    )
    add(
        "PMK_TEST_052", "FAM_PMK_13", "test",
        "What is the income tax rebate percentage on agricultural income under PM-KISAN?",
        "Farmers receive a 20 percent income tax rebate under PM-KISAN.",
        20.0, "percent", "eq", "tax_rebate", "income_tax_payee", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: PM-KISAN does not administer income tax rebates."
    )

    # FAM_PMK_14: Registered Professionals Exclusion
    add(
        "PMK_TEST_053", "FAM_PMK_14", "test",
        "Are practicing doctors, engineers, lawyers, and chartered accountants eligible for PM-KISAN?",
        "Registered professionals (doctors, engineers, lawyers, CAs, architects) are statutorily excluded from PM-KISAN.",
        0.0, "rupees", "eq", "statutory_exclusion", "registered_professional", "annual",
        None, "pmkisan_current", Verdict.SUPPORTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R7"],
        "Supported by Table 2 Row 7: Registered professionals are excluded."
    )
    add(
        "PMK_TEST_054", "FAM_PMK_14", "test",
        "Are practicing doctors, engineers, lawyers, and chartered accountants eligible for PM-KISAN?",
        "Practicing lawyers and doctors are eligible and receive Rs 6000 per year under PM-KISAN.",
        6000.0, "rupees", "eq", "annual_income_support", "registered_professional", "annual",
        None, "pmkisan_current", Verdict.CONTRADICTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R7"],
        "Contradicted: Registered professionals are disqualified under Clause 4.1."
    )
    add(
        "PMK_TEST_055", "FAM_PMK_14", "test",
        "Under PM-KISAN, what is the annual financial support for practicing chartered accountants who own farmland?",
        "Practicing chartered accountants who own farmland receive Rs 6000 per year under PM-KISAN.",
        6000.0, "rupees", "eq", "annual_income_support", "registered_professional", "annual",
        None, "pmkisan_current", Verdict.WRONG_CONTEXT.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R4", "EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R7"],
        "Wrong context: Rs 6000 belongs to eligible non-professional families; CAs are excluded."
    )
    add(
        "PMK_TEST_056", "FAM_PMK_14", "test",
        "What is the continuing professional education stipend for doctors under PM-KISAN?",
        "Doctors receive an annual continuing education stipend of Rs 6000 under PM-KISAN.",
        6000.0, "rupees", "eq", "education_stipend", "registered_professional", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Professional education stipends are not part of PM-KISAN."
    )

    # FAM_PMK_15: Mandatory eKYC (100% compliance)
    add(
        "PMK_TEST_057", "FAM_PMK_15", "test",
        "What is the eKYC compliance requirement for registered farmers under PM-KISAN?",
        "Under PM-KISAN, eKYC completion is 100 percent mandatory for all registered farmers.",
        100.0, "percent", "eq", "mandatory_ekyc_requirement", "all_landholding_farmers", "annual",
        None, "pmkisan_current", Verdict.SUPPORTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P5_CHUNK_1", "EV_DOC_PMKISAN_FAQ_OFFICIAL_P1_CHUNK_2"],
        "Supported by Clause 5.1 and FAQ Q2: eKYC is 100% mandatory."
    )
    add(
        "PMK_TEST_058", "FAM_PMK_15", "test",
        "What is the eKYC compliance requirement for registered farmers under PM-KISAN?",
        "Under PM-KISAN, eKYC completion is optional and only required for 50 percent of beneficiaries.",
        50.0, "percent", "eq", "mandatory_ekyc_requirement", "all_landholding_farmers", "annual",
        None, "pmkisan_current", Verdict.CONTRADICTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P5_CHUNK_1"],
        "Contradicted: eKYC is 100% mandatory, not optional 50%."
    )
    add(
        "PMK_TEST_059", "FAM_PMK_15", "test",
        "What is the central subsidy share for state administrative expenses under PM-KISAN?",
        "The central government pays 100 percent of state administrative expenses under PM-KISAN.",
        100.0, "percent", "eq", "admin_expense_share", "state_governments", "annual",
        None, "pmkisan_current", Verdict.WRONG_CONTEXT.value,
        ["EV_DOC_PMKISAN_OG_2020_P5_CHUNK_1"],
        "Wrong context: 100% is the eKYC and APBS mandate, not an administrative subsidy rate."
    )
    add(
        "PMK_TEST_060", "FAM_PMK_15", "test",
        "What is the fingerprint biometric scanner subsidy rate for CSC village centers under PM-KISAN?",
        "CSC centers receive a 100 percent subsidy for fingerprint biometric scanners under PM-KISAN.",
        100.0, "percent", "eq", "scanner_subsidy", "csc_centers", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: CSC hardware subsidies are not governed by PM-KISAN guidelines."
    )

    # FAM_PMK_16: Aadhaar DBT APBS Delivery (100% electronic)
    add(
        "PMK_TEST_061", "FAM_PMK_16", "test",
        "How are financial benefits delivered to beneficiary bank accounts under PM-KISAN?",
        "Benefits under PM-KISAN are transferred 100 percent electronically via Aadhaar Payment Bridge System (APBS).",
        100.0, "percent", "eq", "aadhaar_seeding_requirement", "all_landholding_farmers", "annual",
        None, "pmkisan_current", Verdict.SUPPORTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P5_CHUNK_1"],
        "Supported by Clause 5.1: 100% electronic transfer via APBS into Aadhaar-seeded accounts."
    )
    add(
        "PMK_TEST_062", "FAM_PMK_16", "test",
        "How are financial benefits delivered to beneficiary bank accounts under PM-KISAN?",
        "Benefits are paid in cash for up to 50 percent of beneficiaries under PM-KISAN.",
        50.0, "percent", "eq", "aadhaar_seeding_requirement", "all_landholding_farmers", "annual",
        None, "pmkisan_current", Verdict.CONTRADICTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P5_CHUNK_1"],
        "Contradicted: 100% electronic DBT is required; cash payment is not permitted."
    )
    add(
        "PMK_TEST_063", "FAM_PMK_16", "test",
        "What percentage of PM-KISAN funds are allocated to urban food processing units?",
        "100 percent of PM-KISAN funds are allocated to urban food processing units.",
        100.0, "percent", "eq", "fund_allocation", "food_processing_units", "annual",
        None, "pmkisan_current", Verdict.WRONG_CONTEXT.value,
        ["EV_DOC_PMKISAN_OG_2020_P5_CHUNK_1"],
        "Wrong context: 100% is the electronic APBS mandate, not fund allocation to food processing."
    )
    add(
        "PMK_TEST_064", "FAM_PMK_16", "test",
        "What is the bank account opening fee reimbursement for rural post offices under PM-KISAN?",
        "Rural post offices receive a 100 percent account opening fee reimbursement under PM-KISAN.",
        100.0, "percent", "eq", "account_fee_reimbursement", "post_offices", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Post office fee reimbursements are outside PM-KISAN scope."
    )

    # FAM_PMK_17: Tractor Purchase Subsidy Distractor (Unverifiable)
    add(
        "PMK_TEST_065", "FAM_PMK_17", "test",
        "Under PM-KISAN, what is the tractor purchase subsidy rate provided to farmers?",
        "Under PM-KISAN, farmers receive a tractor purchase subsidy of 50 percent.",
        50.0, "percent", "eq", "tractor_subsidy", "all_landholding_farmers", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: PM-KISAN does not offer tractor purchase subsidies; absent from guidelines."
    )
    add(
        "PMK_TEST_066", "FAM_PMK_17", "test",
        "Under PM-KISAN, what is the tractor purchase subsidy rate provided to small farmers?",
        "Small farmers receive a tractor purchase subsidy of 40 percent under PM-KISAN.",
        40.0, "percent", "eq", "tractor_subsidy", "small_and_marginal_farmers", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Tractor subsidies are governed by Sub-Mission on Agricultural Mechanization (SMAM)."
    )
    add(
        "PMK_TEST_067", "FAM_PMK_17", "test",
        "Under PM-KISAN, what is the power tiller subsidy rate for hill states?",
        "Farmers in hill states receive a power tiller subsidy of 60 percent under PM-KISAN.",
        60.0, "percent", "eq", "power_tiller_subsidy", "hill_farmers", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Power tiller subsidies are not part of PM-KISAN."
    )
    add(
        "PMK_TEST_068", "FAM_PMK_17", "test",
        "Under PM-KISAN, what is the solar tractor rebate provided to cooperatives?",
        "Cooperatives receive a solar tractor rebate of 35 percent under PM-KISAN.",
        35.0, "percent", "eq", "solar_tractor_rebate", "farmer_cooperatives", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Solar tractor rebates do not exist under PM-KISAN."
    )

    # FAM_PMK_18: Dairy Cattle & Livestock Distractor (Unverifiable)
    add(
        "PMK_TEST_069", "FAM_PMK_18", "test",
        "Under PM-KISAN, what is the financial grant provided for purchasing milch dairy cows?",
        "Under PM-KISAN, farmers receive a grant of Rs 40000 for purchasing milch cows.",
        40000.0, "rupees", "eq", "dairy_cow_grant", "dairy_farmers", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Dairy livestock grants belong to National Livestock Mission, not PM-KISAN."
    )
    add(
        "PMK_TEST_070", "FAM_PMK_18", "test",
        "Under PM-KISAN, what is the capital subsidy for establishing a commercial poultry shed?",
        "Farmers receive a 25 percent capital subsidy for poultry sheds under PM-KISAN.",
        25.0, "percent", "eq", "poultry_shed_subsidy", "poultry_farmers", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Poultry subsidies are not governed by PM-KISAN."
    )
    add(
        "PMK_TEST_071", "FAM_PMK_18", "test",
        "Under PM-KISAN, what is the artificial insemination fee subsidy for indigenous cattle?",
        "Farmers receive a 50 percent artificial insemination subsidy under PM-KISAN.",
        50.0, "percent", "eq", "insemination_subsidy", "dairy_farmers", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Cattle breeding subsidies fall under Rashtriya Gokul Mission."
    )
    add(
        "PMK_TEST_072", "FAM_PMK_18", "test",
        "Under PM-KISAN, what is the fish pond excavation grant for aquaculture cultivators?",
        "Aquaculture cultivators receive an excavation grant of Rs 50000 under PM-KISAN.",
        50000.0, "rupees", "eq", "fish_pond_grant", "fish_farmers", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Aquaculture grants fall under PMMSY, not PM-KISAN."
    )

    # FAM_PMK_19: Fertilizer & Crop Inputs Distractor (Unverifiable)
    add(
        "PMK_TEST_073", "FAM_PMK_19", "test",
        "What is the direct cash rebate on neem-coated urea bags provided under PM-KISAN?",
        "Under PM-KISAN, farmers receive a cash rebate of Rs 2500 per ton on neem-coated urea.",
        2500.0, "rupees", "eq", "fertilizer_rebate", "all_landholding_farmers", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Fertilizer subsidies are managed by Department of Fertilizers, not PM-KISAN."
    )
    add(
        "PMK_TEST_074", "FAM_PMK_19", "test",
        "What is the certified seed distribution subsidy rate under PM-KISAN?",
        "Farmers receive a 50 percent subsidy on certified seeds under PM-KISAN.",
        50.0, "percent", "eq", "seed_subsidy", "all_landholding_farmers", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Seed subsidies fall under Sub-Mission on Seeds and Planting Material."
    )
    add(
        "PMK_TEST_075", "FAM_PMK_19", "test",
        "What is the micro-irrigation drip equipment subsidy percentage under PM-KISAN?",
        "Under PM-KISAN, drip irrigation equipment is subsidized at 55 percent.",
        55.0, "percent", "eq", "drip_irrigation_subsidy", "all_landholding_farmers", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Micro-irrigation is subsidized under PMKSY-Per Drop More Crop."
    )
    add(
        "PMK_TEST_076", "FAM_PMK_19", "test",
        "What is the bio-pesticide demonstration grant per hectare under PM-KISAN?",
        "Farmers receive a bio-pesticide grant of Rs 1500 per hectare under PM-KISAN.",
        1500.0, "rupees", "eq", "biopesticide_grant", "all_landholding_farmers", "annual",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Bio-pesticides fall under Paramparagat Krishi Vikas Yojana."
    )

    # FAM_PMK_20: Period 1 Instalment Window (April to July)
    add(
        "PMK_TEST_077", "FAM_PMK_20", "test",
        "What is the first instalment period window and amount under PM-KISAN?",
        "Under PM-KISAN, the first instalment of Rs 2000 is disbursed between April and July.",
        2000.0, "rupees", "eq", "instalment_amount", "all_landholding_farmers", "per_instalment",
        "first_instalment_period_april_to_july", "pmkisan_current", Verdict.SUPPORTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R1"],
        "Supported by Table 1 Row 1: First instalment of Rs 2000 during April to July."
    )
    add(
        "PMK_TEST_078", "FAM_PMK_20", "test",
        "What is the first instalment amount under PM-KISAN for the period April to July?",
        "Under PM-KISAN, the first instalment for April to July is Rs 4000.",
        4000.0, "rupees", "eq", "instalment_amount", "all_landholding_farmers", "per_instalment",
        "first_instalment_period_april_to_july", "pmkisan_current", Verdict.CONTRADICTED.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R1"],
        "Contradicted: Period 1 instalment is Rs 2000, not Rs 4000."
    )
    add(
        "PMK_TEST_079", "FAM_PMK_20", "test",
        "What is the financial amount disbursed during the first instalment window (April to July) under PM-KISAN?",
        "Under PM-KISAN, farmers receive Rs 6000 during the first instalment window (April to July).",
        6000.0, "rupees", "eq", "instalment_amount", "all_landholding_farmers", "per_instalment",
        "first_instalment_period_april_to_july", "pmkisan_current", Verdict.WRONG_CONTEXT.value,
        ["EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R4", "EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R1"],
        "Wrong context: Rs 6000 is the full-year annual total, not the first instalment (which is Rs 2000)."
    )
    add(
        "PMK_TEST_080", "FAM_PMK_20", "test",
        "What is the emergency advance grant available to drought-affected farmers during April to July under PM-KISAN?",
        "Farmers in drought areas receive an emergency advance grant of Rs 2000 under PM-KISAN.",
        2000.0, "rupees", "eq", "drought_advance_grant", "drought_affected_farmers", "per_instalment",
        None, "pmkisan_current", Verdict.UNVERIFIABLE.value,
        [],
        "Unverifiable: Emergency drought advance grants are not a provision of PM-KISAN."
    )

    return records


def build_and_save_pm_kisan_benchmark(project_root: Path | None = None) -> dict[str, Any]:
    """
    Generate and save the PM-KISAN benchmark dataset with cluster-stratified splits.
    Saves:
      - data/benchmark/pm_kisan/all_claims.jsonl
      - data/benchmark/pm_kisan/dev.jsonl
      - data/benchmark/pm_kisan/test.jsonl
      - data/benchmark/pm_kisan/benchmark_manifest.json (with cryptographic SHA-256 hashes)
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parents[2]

    bench_dir = project_root / "data" / "benchmark" / "pm_kisan"
    bench_dir.mkdir(parents=True, exist_ok=True)

    records = generate_pm_kisan_benchmark_claims()

    all_path = bench_dir / "all_claims.jsonl"
    dev_path = bench_dir / "dev.jsonl"
    test_path = bench_dir / "test.jsonl"

    all_claims: list[dict[str, Any]] = []
    dev_claims: list[dict[str, Any]] = []
    test_claims: list[dict[str, Any]] = []

    dev_fams: set[str] = set()
    test_fams: set[str] = set()

    for r in records:
        d = r.to_dict()
        all_claims.append(d)
        if r.split == "dev":
            dev_claims.append(d)
            dev_fams.add(r.claim_family_id)
        elif r.split == "test":
            test_claims.append(d)
            test_fams.add(r.claim_family_id)

    # Verify zero leakage between Dev and Test claim families
    family_leakage = dev_fams.intersection(test_fams)
    if family_leakage:
        raise ValueError(f"Cluster leakage detected between dev and test families: {family_leakage}")

    # Write JSONL files
    with all_path.open("w", encoding="utf-8") as f:
        for c in all_claims:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    with dev_path.open("w", encoding="utf-8") as f:
        for c in dev_claims:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    with test_path.open("w", encoding="utf-8") as f:
        for c in test_claims:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # Compute SHA-256 hashes
    def get_sha256(p: Path) -> str:
        h = hashlib.sha256()
        with p.open("rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    all_sha = get_sha256(all_path)
    dev_sha = get_sha256(dev_path)
    test_sha = get_sha256(test_path)

    # Verdict distribution counts
    def get_counts(claims: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for c in claims:
            v = c["gold_verdict"]
            counts[v] = counts.get(v, 0) + 1
        return counts

    manifest = {
        "benchmark_id": "PM_KISAN_BENCHMARK_V1",
        "created_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scheme": "PM_KISAN",
        "total_claims": len(all_claims),
        "total_claim_families": len(dev_fams) + len(test_fams),
        "split_protocol": "cluster_stratified_by_claim_family",
        "leakage_verification": "zero_claim_family_overlap_confirmed",
        "splits": {
            "dev": {
                "count": len(dev_claims),
                "claim_families_count": len(dev_fams),
                "claim_families": sorted(list(dev_fams)),
                "verdict_distribution": get_counts(dev_claims),
                "sha256": dev_sha,
                "file": "dev.jsonl",
            },
            "test": {
                "count": len(test_claims),
                "claim_families_count": len(test_fams),
                "claim_families": sorted(list(test_fams)),
                "verdict_distribution": get_counts(test_claims),
                "sha256": test_sha,
                "file": "test.jsonl",
                "freeze_status": "LOCKED_HELD_OUT_TEST_SET",
            },
        },
        "all_claims_sha256": all_sha,
    }

    manifest_path = bench_dir / "benchmark_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return manifest


def load_pm_kisan_benchmark_claims(
    project_root: Path | None = None,
    split: str = "test",
) -> list[BenchmarkClaimRecord]:
    """Load PM-KISAN benchmark claims for a given split ('dev', 'test', or 'all')."""
    if project_root is None:
        project_root = Path(__file__).resolve().parents[2]

    bench_dir = project_root / "data" / "benchmark" / "pm_kisan"
    filename = "all_claims.jsonl" if split == "all" else f"{split}.jsonl"
    path = bench_dir / filename

    if not path.exists():
        build_and_save_pm_kisan_benchmark(project_root)

    records: list[BenchmarkClaimRecord] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                d = json.loads(line)
                records.append(BenchmarkClaimRecord(**d))
    return records

