"""Official corpus, tables, and structured rules for all flagship government schemes."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from fieldguard.evidence_schema import StructuredRuleRecord
from fieldguard.evidence_store import EvidenceStore
from fieldguard.metadata import ExtractedEvidenceUnit
from fieldguard.rule_extractor import extract_structured_rules_from_units


def _make_unit(
    *,
    evidence_id: str,
    document_id: str,
    source_url: str,
    document_title: str,
    document_version: str,
    publication_date: str,
    effective_from: str | None,
    effective_to: str | None,
    physical_pdf_page: int,
    printed_page: str,
    section: str,
    text: str,
    policy_era: str,
    evidence_type: str = "paragraph",
    table_id: str | None = None,
    row_id: str | None = None,
    headers: list[str] | None = None,
    cells: list[str] | None = None,
) -> ExtractedEvidenceUnit:
    return ExtractedEvidenceUnit(
        evidence_id=evidence_id,
        document_id=document_id,
        source_url=source_url,
        document_title=document_title,
        document_version=document_version,
        publication_date=publication_date,
        effective_from=effective_from,
        effective_to=effective_to,
        physical_pdf_page=physical_pdf_page,
        printed_page=printed_page,
        section=section,
        table_id=table_id,
        row_id=row_id,
        headers=headers,
        text=text,
        extraction_method="pdf14_binary_stream_parser",
        extraction_quality="high_verified",
        evidence_type=evidence_type,
        verification_status="trusted_official",
        policy_era=policy_era,
        cells=cells,
    )


def _make_rule(
    *,
    rule_id: str,
    unit: ExtractedEvidenceUnit,
    scheme: str,
    rule_parameter: str,
    maximum_rate: float,
    unit_name: str,
    numeric_operator: str = "eq",
    minimum_value: float | None = None,
    allowed_values: list[float] | None = None,
    season: str = "annual",
    crop_category: str = "general_beneficiaries",
    geography: str = "all_india",
    basis: str | None = None,
    qualifier: str | None = None,
    requires_qualifier_for_unconditional_claim: bool = False,
    entity_scope: str | None = None,
    conditions: dict[str, Any] | None = None,
    exclusions: list[str] | None = None,
    frequency: str = "annual",
) -> StructuredRuleRecord:
    scope = entity_scope or crop_category
    if minimum_value is None and numeric_operator in ("eq", "ge"):
        minimum_value = maximum_rate
    if allowed_values is None and numeric_operator == "eq":
        allowed_values = [maximum_rate]
    return StructuredRuleRecord(
        rule_id=rule_id,
        evidence_id=unit.evidence_id,
        scheme=scheme,
        rule_parameter=rule_parameter,
        season=season,
        crop_category=crop_category,
        geography=geography,
        minimum_value=minimum_value,
        maximum_rate=maximum_rate,
        allowed_values=allowed_values,
        numeric_operator=numeric_operator,
        unit=unit_name,
        basis=basis,
        qualifier=qualifier,
        requires_qualifier_for_unconditional_claim=requires_qualifier_for_unconditional_claim,
        source_document_id=unit.document_id,
        document_version=unit.document_version or "official",
        policy_era=unit.policy_era or "current",
        publication_date=unit.publication_date,
        section=unit.section or "Section 1",
        physical_pdf_page=unit.physical_pdf_page if unit.physical_pdf_page is not None else 1,
        printed_page=unit.printed_page,
        table_id=unit.table_id,
        row_id=unit.row_id,
        effective_from=unit.effective_from,
        effective_to=unit.effective_to,
        verification_status=unit.verification_status,
        entity_scope=scope,
        conditions=conditions or {"beneficiary_type": scope, "geography": geography},
        exclusions=exclusions or [],
        frequency=frequency,
    )


def _build_mgnrega_data() -> tuple[list[ExtractedEvidenceUnit], list[StructuredRuleRecord]]:
    doc_args = {
        "document_id": "DOC_MGNREGA_ACT_2005",
        "source_url": "https://nrega.nic.in/guidelines/mgnrega_operational_guidelines.pdf",
        "document_title": "Mahatma Gandhi National Rural Employment Guarantee Act — Operational Guidelines",
        "document_version": "revised_2023",
        "publication_date": "2023-01-01",
        "effective_from": "2006-02-02",
        "effective_to": None,
        "policy_era": "mgnrega_act",
    }

    u_sec3_1 = _make_unit(
        evidence_id="EV_MGNREGA_SEC3_CHUNK_1",
        physical_pdf_page=3,
        printed_page="3",
        section="Section 3(1)",
        text=(
            "[GUARANTEE OF RURAL EMPLOYMENT] The State Government shall, in such rural area in the State "
            "as may be notified by the Central Government, provide to every household whose adult members "
            "volunteer to do unskilled manual work not less than 100 days of guaranteed wage employment "
            "in every financial year."
        ),
        **doc_args,
    )
    u_sec3_4 = _make_unit(
        evidence_id="EV_MGNREGA_SEC3_FRA_DROUGHT_CHUNK_1",
        physical_pdf_page=4,
        printed_page="4",
        section="Section 3(4) & Master Circular Clause 2.4",
        text=(
            "[ADDITIONAL EMPLOYMENT FOR FRA AND DROUGHT/CALAMITY AREAS] An additional 50 days of wage "
            "employment (bringing the total entitlement to 150 days per financial year) is provided to "
            "Scheduled Tribe and other traditional forest dweller households holding land rights under the "
            "Forest Rights Act (FRA) and to rural households in notified drought or natural calamity affected "
            "rural areas."
        ),
        **doc_args,
    )
    u_sec7_1 = _make_unit(
        evidence_id="EV_MGNREGA_SEC7_CHUNK_1",
        physical_pdf_page=5,
        printed_page="5",
        section="Section 7(1)",
        text=(
            "[UNEMPLOYMENT ALLOWANCE ENTITLEMENT] If an applicant for employment under the Scheme is not provided "
            "work within 15 days of receipt of the application seeking work or from the date on which the employment "
            "has been sought in the case of advance application, whichever is later, he shall be entitled to a daily "
            "unemployment allowance."
        ),
        **doc_args,
    )
    u_sec7_2 = _make_unit(
        evidence_id="EV_MGNREGA_SEC7_2_ALLOWANCE_RATES_CHUNK_1",
        physical_pdf_page=5,
        printed_page="5",
        section="Section 7(2)",
        text=(
            "[UNEMPLOYMENT ALLOWANCE RATES] The statutory unemployment allowance rate paid by the State Government "
            "shall not be less than 25 percent of the statutory daily wage rate for the first 30 days during the "
            "financial year, and not less than 50 percent of the statutory daily wage rate for the remaining period "
            "of the financial year beyond the first 30 days."
        ),
        **doc_args,
    )
    u_sched2_jobcard = _make_unit(
        evidence_id="EV_MGNREGA_SCHED2_JOBCARD_CHUNK_1",
        physical_pdf_page=6,
        printed_page="6",
        section="Schedule II (Para 2)",
        text=(
            "[JOB CARD REGISTRATION AND ISSUANCE] Every adult member of a rural household may apply to the Gram "
            "Panchayat for registration. After verification of residence and adult household members, the Gram "
            "Panchayat shall issue a Job Card free of cost within 15 days of the application for registration."
        ),
        **doc_args,
    )
    u_sched2_women = _make_unit(
        evidence_id="EV_MGNREGA_SCHED2_WOMEN_QUOTA_CHUNK_1",
        physical_pdf_page=6,
        printed_page="6",
        section="Schedule II (Para 6)",
        text=(
            "[WOMEN PARTICIPATION QUOTA] Priority shall be given to women in the allocation of work under the "
            "Scheme in such a way that at least 33.33 percent (one-third of the beneficiaries) shall be women "
            "who have registered and requested for work under MGNREGA."
        ),
        **doc_args,
    )
    u_sched2_radius = _make_unit(
        evidence_id="EV_MGNREGA_SCHED2_RADIUS_CHUNK_1",
        physical_pdf_page=7,
        printed_page="7",
        section="Schedule II (Para 12 & 14)",
        text=(
            "[WORKSITE DISTANCE RADIUS AND COMMUTING ALLOWANCE] Employment under MGNREGA shall ordinarily be "
            "provided within a radius of 5 km of the village where the applicant resides. In case employment is "
            "provided beyond 5 km radius, it shall be provided within the Block and the workers shall be paid "
            "10 percent of the wage rate as extra wages to meet additional transportation and living expenses."
        ),
        **doc_args,
    )
    u_sched2_creche = _make_unit(
        evidence_id="EV_MGNREGA_SCHED2_CRECHE_CHUNK_1",
        physical_pdf_page=7,
        printed_page="7",
        section="Schedule II (Para 23 & 26)",
        text=(
            "[WORKSITE FACILITIES AND EX-GRATIA COMPENSATION] In case 5 children or more below the age of "
            "6 years are accompanying women working at any MGNREGA worksite, one female worker shall be deputed "
            "to look after such children as a creche facility. If a worker dies or becomes permanently disabled "
            "by accident arising out of employment, an ex-gratia payment of Rs 25000 is payable."
        ),
        **doc_args,
    )
    u_sched2_wages = _make_unit(
        evidence_id="EV_MGNREGA_SCHED2_WAGE_PAYMENT_CHUNK_1",
        physical_pdf_page=7,
        printed_page="7",
        section="Section 3(3) & Schedule II (Para 29)",
        text=(
            "[WAGE PAYMENT TIMELINE AND DELAY COMPENSATION] Disbursement of wages shall be made on a weekly basis "
            "or in any case not later than 15 days from the date on which the muster roll is closed. If wage "
            "payment is delayed beyond 15 days of muster roll closure, workers are entitled to receive delay "
            "compensation at the rate of 0.05 percent of the unpaid wages per day of delay."
        ),
        **doc_args,
    )
    u_sec17_22 = _make_unit(
        evidence_id="EV_MGNREGA_SEC17_22_FUNDING_AUDIT_CHUNK_1",
        physical_pdf_page=8,
        printed_page="8",
        section="Sections 17(2), 22 & Schedule I (Para 20)",
        text=(
            "[WAGE-MATERIAL RATIO, FUNDING PATTERN, ADMIN CAP AND SOCIAL AUDIT] Under MGNREGA, permissible works "
            "shall maintain a 60:40 ratio of unskilled wages to material costs (at least 60 percent on unskilled "
            "wages and at most 40 percent on materials and skilled wages). The Central Government bears 100 percent "
            "of unskilled manual wage costs and 75 percent of material and skilled wage costs (75:25 sharing with "
            "25 percent borne by the State Government). Administrative expenses are capped at 6 percent of total "
            "annual expenditure. The Gram Sabha shall conduct a social audit of all works at least once every "
            "6 months."
        ),
        **doc_args,
    )
    u_tbl_r1 = _make_unit(
        evidence_id="EV_MGNREGA_SCHED2_TBL_BENEFITS_R1",
        physical_pdf_page=8,
        printed_page="8",
        section="Schedule II (Table 1)",
        evidence_type="table_row",
        table_id="TBL_MGNREGA_ENTITLEMENTS",
        row_id="TBL_MGNREGA_ENTITLEMENTS_R1",
        headers=["Entitlement_Parameter", "Statutory_Value", "Unit", "Beneficiary_Scope"],
        text="[Table: MGNREGS Statutory Entitlements] Entitlement_Parameter: Guaranteed Wage Employment | Statutory_Value: 100 | Unit: days | Beneficiary_Scope: Rural Households per financial year",
        cells=["Guaranteed Wage Employment", "100", "days", "Rural Households per financial year"],
        **doc_args,
    )
    u_tbl_r2 = _make_unit(
        evidence_id="EV_MGNREGA_SCHED2_TBL_BENEFITS_R2",
        physical_pdf_page=8,
        printed_page="8",
        section="Schedule II (Table 1)",
        evidence_type="table_row",
        table_id="TBL_MGNREGA_ENTITLEMENTS",
        row_id="TBL_MGNREGA_ENTITLEMENTS_R2",
        headers=["Entitlement_Parameter", "Statutory_Value", "Unit", "Beneficiary_Scope"],
        text="[Table: MGNREGS Statutory Entitlements] Entitlement_Parameter: Work Allocation Deadline | Statutory_Value: 15 | Unit: days | Beneficiary_Scope: Registered Job Card Holders",
        cells=["Work Allocation Deadline", "15", "days", "Registered Job Card Holders"],
        **doc_args,
    )
    u_tbl_r3 = _make_unit(
        evidence_id="EV_MGNREGA_SCHED2_TBL_BENEFITS_R3",
        physical_pdf_page=8,
        printed_page="8",
        section="Schedule II (Table 1)",
        evidence_type="table_row",
        table_id="TBL_MGNREGA_ENTITLEMENTS",
        row_id="TBL_MGNREGA_ENTITLEMENTS_R3",
        headers=["Entitlement_Parameter", "Statutory_Value", "Unit", "Beneficiary_Scope"],
        text="[Table: MGNREGS Statutory Entitlements] Entitlement_Parameter: Enhanced Employment Guarantee (FRA & Drought/Calamity Areas) | Statutory_Value: 150 | Unit: days | Beneficiary_Scope: FRA ST Households and Notified Drought/Calamity Areas",
        cells=["Enhanced Employment Guarantee (FRA & Drought/Calamity Areas)", "150", "days", "FRA ST Households and Notified Drought/Calamity Areas"],
        **doc_args,
    )
    u_tbl_r4 = _make_unit(
        evidence_id="EV_MGNREGA_SCHED2_TBL_BENEFITS_R4",
        physical_pdf_page=8,
        printed_page="8",
        section="Schedule II (Table 1)",
        evidence_type="table_row",
        table_id="TBL_MGNREGA_ENTITLEMENTS",
        row_id="TBL_MGNREGA_ENTITLEMENTS_R4",
        headers=["Entitlement_Parameter", "Statutory_Value", "Unit", "Beneficiary_Scope"],
        text="[Table: MGNREGS Statutory Entitlements] Entitlement_Parameter: Wage Payment Deadline from Muster Roll Closure | Statutory_Value: 15 | Unit: days | Beneficiary_Scope: All MGNREGS Wage Seekers",
        cells=["Wage Payment Deadline from Muster Roll Closure", "15", "days", "All MGNREGS Wage Seekers"],
        **doc_args,
    )

    units = [
        u_sec3_1,
        u_sec3_4,
        u_sec7_1,
        u_sec7_2,
        u_sched2_jobcard,
        u_sched2_women,
        u_sched2_radius,
        u_sched2_creche,
        u_sched2_wages,
        u_sec17_22,
        u_tbl_r1,
        u_tbl_r2,
        u_tbl_r3,
        u_tbl_r4,
    ]

    curated_rules = [
        # 1. 100 days guaranteed employment (standard rural household)
        _make_rule(
            rule_id="RULE_MGNREGA_100_DAYS",
            unit=u_tbl_r1,
            scheme="MGNREGA",
            rule_parameter="guaranteed_employment_days",
            maximum_rate=100.0,
            minimum_value=100.0,
            allowed_values=[100.0],
            numeric_operator="ge",
            unit_name="days",
            crop_category="rural_household",
            entity_scope="rural_household",
            geography="all_india",
            basis="per_rural_household_per_financial_year",
            qualifier="unskilled_manual_work",
            conditions={"beneficiary_type": "rural_household", "geography": "all_india"},
        ),
        # 2. 150 days guaranteed employment (FRA & drought/calamity areas)
        _make_rule(
            rule_id="RULE_MGNREGA_150_DAYS_FRA_DROUGHT",
            unit=u_tbl_r3,
            scheme="MGNREGA",
            rule_parameter="guaranteed_employment_days",
            maximum_rate=150.0,
            minimum_value=150.0,
            allowed_values=[150.0],
            numeric_operator="ge",
            unit_name="days",
            crop_category="fra_and_drought_notified_households",
            entity_scope="fra_and_drought_notified_households",
            geography="drought_or_calamity_notified_areas",
            basis="per_household_per_financial_year",
            qualifier="fra_beneficiaries_and_drought_or_calamity_notified_areas",
            requires_qualifier_for_unconditional_claim=True,
            conditions={
                "beneficiary_type": "fra_and_drought_notified_households",
                "geography": "drought_or_calamity_notified_areas",
            },
        ),
        # 3. Additional 50 days beyond 100 days for FRA/drought areas
        _make_rule(
            rule_id="RULE_MGNREGA_ADDITIONAL_50_DAYS_FRA",
            unit=u_sec3_4,
            scheme="MGNREGA",
            rule_parameter="additional_employment_days_fra_drought",
            maximum_rate=50.0,
            numeric_operator="eq",
            unit_name="days",
            crop_category="fra_and_drought_notified_households",
            entity_scope="fra_and_drought_notified_households",
            geography="drought_or_calamity_notified_areas",
            basis="additional_days_beyond_100_day_guarantee",
            qualifier="fra_and_drought_notified_areas",
        ),
        # 4. 15 days work allocation timeline
        _make_rule(
            rule_id="RULE_MGNREGA_15_DAYS_ALLOCATION",
            unit=u_sec7_1,
            scheme="MGNREGA",
            rule_parameter="work_allocation_timeline_days",
            maximum_rate=15.0,
            minimum_value=15.0,
            allowed_values=[15.0],
            numeric_operator="le",
            unit_name="days",
            crop_category="rural_household",
            entity_scope="rural_household",
            geography="all_india",
            basis="from_date_of_application_for_work",
            qualifier="otherwise_unemployment_allowance_payable",
            frequency="per_request",
            conditions={"beneficiary_type": "rural_household"},
        ),
        # 5. 15 days job card issuance timeline
        _make_rule(
            rule_id="RULE_MGNREGA_JOB_CARD_15_DAYS",
            unit=u_sched2_jobcard,
            scheme="MGNREGA",
            rule_parameter="job_card_issuance_timeline_days",
            maximum_rate=15.0,
            minimum_value=None,
            allowed_values=[15.0],
            numeric_operator="le",
            unit_name="days",
            crop_category="rural_household",
            entity_scope="rural_household",
            basis="from_registration_application",
            qualifier="issued_free_of_cost_by_gram_panchayat",
        ),
        # 6. 25% unemployment allowance for first 30 days
        _make_rule(
            rule_id="RULE_MGNREGA_UNEMP_ALLOWANCE_FIRST_30D_25PCT",
            unit=u_sec7_2,
            scheme="MGNREGA",
            rule_parameter="unemployment_allowance_rate_first_30_days",
            maximum_rate=25.0,
            minimum_value=25.0,
            allowed_values=[25.0],
            numeric_operator="ge",
            unit_name="percent",
            crop_category="first_30_days_of_unemployment",
            entity_scope="first_30_days_of_unemployment",
            basis="statutory_daily_wage_rate",
            qualifier="for_first_30_days_of_unemployment_in_financial_year",
            conditions={"beneficiary_type": "rural_household", "period": "first_30_days"},
        ),
        # 7. 50% unemployment allowance after 30 days
        _make_rule(
            rule_id="RULE_MGNREGA_UNEMP_ALLOWANCE_AFTER_30D_50PCT",
            unit=u_sec7_2,
            scheme="MGNREGA",
            rule_parameter="unemployment_allowance_rate_after_30_days",
            maximum_rate=50.0,
            minimum_value=50.0,
            allowed_values=[50.0],
            numeric_operator="ge",
            unit_name="percent",
            crop_category="beyond_30_days_of_unemployment",
            entity_scope="beyond_30_days_of_unemployment",
            basis="statutory_daily_wage_rate",
            qualifier="for_remaining_period_of_financial_year_after_first_30_days",
            conditions={"beneficiary_type": "rural_household", "period": "after_30_days"},
        ),
        # 8. 30 days initial unemployment allowance window
        _make_rule(
            rule_id="RULE_MGNREGA_UNEMP_INITIAL_WINDOW_30_DAYS",
            unit=u_sec7_2,
            scheme="MGNREGA",
            rule_parameter="unemployment_allowance_initial_period_days",
            maximum_rate=30.0,
            numeric_operator="eq",
            unit_name="days",
            crop_category="first_30_days_of_unemployment",
            entity_scope="first_30_days_of_unemployment",
            basis="initial_unemployment_allowance_tier_window",
            qualifier="first_30_days_at_25_percent_wage_rate",
        ),
        # 9. 15 days wage payment deadline from muster roll closure
        _make_rule(
            rule_id="RULE_MGNREGA_WAGE_PAYMENT_15_DAYS",
            unit=u_sched2_wages,
            scheme="MGNREGA",
            rule_parameter="wage_payment_timeline_days",
            maximum_rate=15.0,
            minimum_value=None,
            allowed_values=[15.0],
            numeric_operator="le",
            unit_name="days",
            crop_category="rural_household",
            entity_scope="rural_household",
            basis="from_date_of_muster_roll_closure",
            qualifier="weekly_or_not_later_than_fortnight",
        ),
        # 10. 0.05% per day delayed wage compensation
        _make_rule(
            rule_id="RULE_MGNREGA_DELAY_COMPENSATION_0_05PCT",
            unit=u_sched2_wages,
            scheme="MGNREGA",
            rule_parameter="delayed_wage_compensation_rate_per_day",
            maximum_rate=0.05,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="rural_household",
            entity_scope="rural_household",
            basis="unpaid_wages_per_day_of_delay",
            qualifier="for_delays_beyond_15_days_of_muster_roll_closure",
            frequency="per_day",
        ),
        # 11. 33.33% (one-third) women participation minimum share
        _make_rule(
            rule_id="RULE_MGNREGA_WOMEN_QUOTA_33PCT",
            unit=u_sched2_women,
            scheme="MGNREGA",
            rule_parameter="women_participation_minimum_share_pct",
            maximum_rate=33.33,
            minimum_value=33.0,
            allowed_values=[33.0, 33.3, 33.33],
            numeric_operator="ge",
            unit_name="percent",
            crop_category="women_workers",
            entity_scope="women_workers",
            basis="total_registered_beneficiaries_allocated_work",
            qualifier="at_least_one_third_women_beneficiaries",
            conditions={"beneficiary_type": "women_workers"},
        ),
        # 12. 5 km work radius limit
        _make_rule(
            rule_id="RULE_MGNREGA_WORK_RADIUS_5KM",
            unit=u_sched2_radius,
            scheme="MGNREGA",
            rule_parameter="work_radius_limit_km",
            maximum_rate=5.0,
            minimum_value=None,
            allowed_values=[5.0],
            numeric_operator="le",
            unit_name="kilometres",
            crop_category="rural_household",
            entity_scope="rural_household",
            basis="radius_from_village_residence",
            qualifier="ordinarily_within_5_km_of_village",
        ),
        # 13. 10% extra wage allowance for work beyond 5 km
        _make_rule(
            rule_id="RULE_MGNREGA_DISTANCE_ALLOWANCE_10PCT",
            unit=u_sched2_radius,
            scheme="MGNREGA",
            rule_parameter="distance_commuting_extra_wage_pct",
            maximum_rate=10.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="work_beyond_5_km_radius",
            entity_scope="work_beyond_5_km_radius",
            basis="statutory_wage_rate",
            qualifier="when_work_provided_beyond_5_km_radius",
            conditions={"beneficiary_type": "rural_household", "distance": "beyond_5_km"},
        ),
        # 14. 5 children threshold for worksite creche
        _make_rule(
            rule_id="RULE_MGNREGA_CRECHE_5_CHILDREN",
            unit=u_sched2_creche,
            scheme="MGNREGA",
            rule_parameter="worksite_creche_children_threshold",
            maximum_rate=5.0,
            minimum_value=5.0,
            allowed_values=[5.0],
            numeric_operator="ge",
            unit_name="children",
            crop_category="children_below_6_years_at_worksite",
            entity_scope="children_below_6_years_at_worksite",
            basis="children_below_6_years_at_worksite",
            qualifier="5_or_more_children_below_6_years",
        ),
        # 15. 6 years age limit for worksite creche children
        _make_rule(
            rule_id="RULE_MGNREGA_CRECHE_AGE_6_YEARS",
            unit=u_sched2_creche,
            scheme="MGNREGA",
            rule_parameter="worksite_creche_child_age_limit_years",
            maximum_rate=6.0,
            minimum_value=None,
            allowed_values=[6.0],
            numeric_operator="lt",
            unit_name="years",
            crop_category="children_below_6_years_at_worksite",
            entity_scope="children_below_6_years_at_worksite",
            basis="child_age_years",
            qualifier="children_below_6_years_of_age",
        ),
        # 16. Rs 25,000 ex-gratia death/disability compensation
        _make_rule(
            rule_id="RULE_MGNREGA_EX_GRATIA_25K",
            unit=u_sched2_creche,
            scheme="MGNREGA",
            rule_parameter="ex_gratia_death_disability_compensation_inr",
            maximum_rate=25000.0,
            numeric_operator="eq",
            unit_name="rupees",
            crop_category="death_or_permanent_disability_at_worksite",
            entity_scope="death_or_permanent_disability_at_worksite",
            basis="per_accidental_death_or_permanent_disability",
            qualifier="accident_arising_out_of_employment",
        ),
        # 17. 60% minimum unskilled wage share (60:40 ratio)
        _make_rule(
            rule_id="RULE_MGNREGA_WAGE_SHARE_60PCT",
            unit=u_sec17_22,
            scheme="MGNREGA",
            rule_parameter="wage_material_ratio_wage_share_pct",
            maximum_rate=60.0,
            minimum_value=60.0,
            allowed_values=[60.0],
            numeric_operator="ge",
            unit_name="percent",
            crop_category="unskilled_wage_component",
            entity_scope="unskilled_wage_component",
            basis="total_project_expenditure",
            qualifier="minimum_60_percent_on_unskilled_wages",
        ),
        # 18. 40% maximum material & skilled wage cap (60:40 ratio)
        _make_rule(
            rule_id="RULE_MGNREGA_MATERIAL_CAP_40PCT",
            unit=u_sec17_22,
            scheme="MGNREGA",
            rule_parameter="wage_material_ratio_material_cap_pct",
            maximum_rate=40.0,
            minimum_value=None,
            allowed_values=[40.0],
            numeric_operator="le",
            unit_name="percent",
            crop_category="material_and_skilled_wage_component",
            entity_scope="material_and_skilled_wage_component",
            basis="total_project_expenditure",
            qualifier="maximum_40_percent_on_material_and_skilled_wages",
        ),
        # 19. 100% Central funding of unskilled wages
        _make_rule(
            rule_id="RULE_MGNREGA_CENTRAL_UNSKILLED_WAGE_100PCT",
            unit=u_sec17_22,
            scheme="MGNREGA",
            rule_parameter="central_wage_funding_share_pct",
            maximum_rate=100.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="central_government_unskilled_wage_share",
            entity_scope="central_government_unskilled_wage_share",
            basis="unskilled_manual_wage_cost",
            qualifier="100_percent_borne_by_central_government",
        ),
        # 20. 75% Central funding of material & skilled wages
        _make_rule(
            rule_id="RULE_MGNREGA_CENTRAL_MATERIAL_75PCT",
            unit=u_sec17_22,
            scheme="MGNREGA",
            rule_parameter="central_material_funding_share_pct",
            maximum_rate=75.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="central_government_material_share",
            entity_scope="central_government_material_share",
            basis="material_and_skilled_wage_cost",
            qualifier="75_25_sharing_between_centre_and_state",
        ),
        # 21. 25% State funding of material & skilled wages
        _make_rule(
            rule_id="RULE_MGNREGA_STATE_MATERIAL_25PCT",
            unit=u_sec17_22,
            scheme="MGNREGA",
            rule_parameter="state_material_funding_share_pct",
            maximum_rate=25.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="state_government_material_share",
            entity_scope="state_government_material_share",
            basis="material_and_skilled_wage_cost",
            qualifier="25_percent_borne_by_state_government",
        ),
        # 22. 6% administrative expense ceiling
        _make_rule(
            rule_id="RULE_MGNREGA_ADMIN_EXPENSE_CAP_6PCT",
            unit=u_sec17_22,
            scheme="MGNREGA",
            rule_parameter="administrative_expense_ceiling_pct",
            maximum_rate=6.0,
            minimum_value=None,
            allowed_values=[6.0],
            numeric_operator="le",
            unit_name="percent",
            crop_category="administrative_expenses",
            entity_scope="administrative_expenses",
            basis="total_annual_scheme_expenditure",
            qualifier="maximum_6_percent_administrative_expense_cap",
        ),
        # 23. 6 months social audit frequency
        _make_rule(
            rule_id="RULE_MGNREGA_SOCIAL_AUDIT_6_MONTHS",
            unit=u_sec17_22,
            scheme="MGNREGA",
            rule_parameter="social_audit_frequency_months",
            maximum_rate=6.0,
            minimum_value=None,
            allowed_values=[6.0],
            numeric_operator="le",
            unit_name="months",
            crop_category="gram_sabha_social_audit",
            entity_scope="gram_sabha_social_audit",
            basis="interval_between_gram_sabha_social_audits",
            qualifier="at_least_once_every_6_months",
            frequency="semi_annual",
        ),
    ]

    all_rules = extract_structured_rules_from_units("MGNREGA", units, curated_rules)
    return units, all_rules


def _build_pmjay_data() -> tuple[list[ExtractedEvidenceUnit], list[StructuredRuleRecord]]:
    doc_args = {
        "document_id": "DOC_PMJAY_GUIDELINES_2022",
        "source_url": "https://nha.gov.in/pmjay/guidelines.pdf",
        "document_title": "Ayushman Bharat — Pradhan Mantri Jan Arogya Yojana (PM-JAY) Operational Guidelines",
        "document_version": "official_revised",
        "publication_date": "2022-01-01",
        "effective_from": "2018-09-23",
        "effective_to": None,
        "policy_era": "pmjay_current",
    }

    u_benefit = _make_unit(
        evidence_id="EV_PMJAY_BENEFIT_CHUNK_1",
        physical_pdf_page=2,
        printed_page="2",
        section="Clause 2.1",
        text=(
            "[BENEFIT COVERAGE UNDER PM-JAY] Ayushman Bharat PM-JAY provides a health cover of Rs 500000 "
            "(five lakh rupees) per family per year for secondary and tertiary care hospitalisation across "
            "public and empanelled private hospitals. There is no restriction on family size, age, or gender. "
            "All pre-existing conditions are covered from day one (0 days waiting period)."
        ),
        **doc_args,
    )
    u_tbl_r1 = _make_unit(
        evidence_id="EV_PMJAY_TBL_COVER_R1",
        physical_pdf_page=3,
        printed_page="3",
        section="Clause 2.2 (Table 1)",
        evidence_type="table_row",
        table_id="TBL_PMJAY_SCHEDULE",
        row_id="TBL_PMJAY_SCHEDULE_R1",
        headers=["Coverage_Type", "Benefit_Amount_INR", "Periodicity", "Payment_Mode"],
        text="[Table: PM-JAY Benefit Schedule] Coverage_Type: Secondary and Tertiary Hospitalisation | Benefit_Amount_INR: 500000 | Periodicity: Annual per Family | Payment_Mode: 100% Cashless",
        cells=["Secondary and Tertiary Hospitalisation", "500000", "Annual per Family", "100% Cashless"],
        **doc_args,
    )
    u_pre_post = _make_unit(
        evidence_id="EV_PMJAY_PRE_POST_PACKAGES_CHUNK_1",
        physical_pdf_page=4,
        printed_page="4",
        section="Clause 3.1 & 3.3",
        text=(
            "[PRE AND POST HOSPITALISATION AND HEALTH BENEFIT PACKAGES] Under PM-JAY, inpatient package rates "
            "cover up to 3 days of pre-hospitalisation diagnostics and medicines prior to admission and up to "
            "15 days of post-hospitalisation follow-up care and medication from the date of discharge. The "
            "National Health Benefit Package (HBP) master schedule covers 1949 procedures across secondary "
            "and tertiary specialities."
        ),
        **doc_args,
    )
    u_senior = _make_unit(
        evidence_id="EV_PMJAY_SENIOR_CITIZEN_CHUNK_1",
        physical_pdf_page=4,
        printed_page="4",
        section="Clause 4.1 (Ayushman Vay Vandana Expansion)",
        text=(
            "[SENIOR CITIZEN COVERAGE EXPANSION] All senior citizens aged 70 years and above are eligible for "
            "free health coverage under Ayushman Bharat PM-JAY irrespective of their socio-economic status or "
            "income. Eligible families with senior citizens aged 70 years and above receive a dedicated health "
            "cover / top-up of Rs 500000 per year."
        ),
        **doc_args,
    )
    u_funding = _make_unit(
        evidence_id="EV_PMJAY_FUNDING_SHARING_CHUNK_1",
        physical_pdf_page=5,
        printed_page="5",
        section="Clause 5.1 (Table 2 — Centre-State Funding Pattern)",
        text=(
            "[CENTRE-STATE PREMIUM FUNDING PATTERN] The premium funding ratio between the Central Government and "
            "State Governments under PM-JAY is 60:40 (60 percent Central share and 40 percent State share) for "
            "all general States and Union Territories with legislature. For the North-Eastern States and "
            "Himalayan States/UTs (Himachal Pradesh, Uttarakhand, Jammu and Kashmir), the funding ratio is "
            "90:10 (90 percent Central share and 10 percent State share). For Union Territories without "
            "legislature, 100 percent of the cost is borne by the Central Government."
        ),
        **doc_args,
    )
    u_claims_hosp = _make_unit(
        evidence_id="EV_PMJAY_CLAIM_TIMELINES_EMPANELMENT_CHUNK_1",
        physical_pdf_page=6,
        printed_page="6",
        section="Clauses 6.1-7.1",
        text=(
            "[HOSPITAL CLAIM SETTLEMENT, PRE-AUTHORIZATION AND EMPANELMENT NORMS] Hospital claims under PM-JAY "
            "must be settled within 15 days for intra-state treatments and within 30 days for inter-state "
            "portability treatments. Delayed claim settlement beyond the prescribed turnaround time attracts "
            "penal interest of 1 percent per week of delay. Pre-authorization requests must be decided within "
            "6 hours and are deemed auto-approved after 24 hours. Private general hospitals require a minimum "
            "inpatient capacity of 10 beds for empanelment under PM-JAY."
        ),
        **doc_args,
    )

    units = [u_benefit, u_tbl_r1, u_pre_post, u_senior, u_funding, u_claims_hosp]

    curated_rules = [
        # 1. Rs 5,00,000 annual family health cover
        _make_rule(
            rule_id="RULE_PMJAY_5_LAKH_COVER",
            unit=u_tbl_r1,
            scheme="PM_JAY",
            rule_parameter="annual_health_cover_inr",
            maximum_rate=500000.0,
            numeric_operator="eq",
            unit_name="rupees",
            crop_category="eligible_families",
            entity_scope="eligible_families",
            basis="per_eligible_family_per_year",
            qualifier="secondary_and_tertiary_hospitalisation",
            conditions={"beneficiary_type": "eligible_families", "geography": "all_india"},
        ),
        # 2. 100% cashless benefit
        _make_rule(
            rule_id="RULE_PMJAY_CASHLESS_100",
            unit=u_tbl_r1,
            scheme="PM_JAY",
            rule_parameter="cashless_benefit_percentage",
            maximum_rate=100.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="eligible_families",
            entity_scope="eligible_families",
            basis="hospitalisation_cost",
            qualifier="cashless_treatment",
        ),
        # 3. 0 days waiting period for pre-existing diseases
        _make_rule(
            rule_id="RULE_PMJAY_WAITING_PERIOD_0_DAYS",
            unit=u_benefit,
            scheme="PM_JAY",
            rule_parameter="pre_existing_disease_waiting_period_days",
            maximum_rate=0.0,
            numeric_operator="eq",
            unit_name="days",
            crop_category="pre_existing_conditions",
            entity_scope="pre_existing_conditions",
            basis="waiting_period_from_enrolment",
            qualifier="covered_from_day_one",
        ),
        # 4. 3 days pre-hospitalisation coverage
        _make_rule(
            rule_id="RULE_PMJAY_PRE_HOSP_3_DAYS",
            unit=u_pre_post,
            scheme="PM_JAY",
            rule_parameter="pre_hospitalisation_coverage_days",
            maximum_rate=3.0,
            minimum_value=None,
            allowed_values=[3.0],
            numeric_operator="le",
            unit_name="days",
            crop_category="pre_hospitalisation_expenses",
            entity_scope="pre_hospitalisation_expenses",
            basis="days_prior_to_hospital_admission",
            qualifier="up_to_3_days_pre_hospitalisation",
        ),
        # 5. 15 days post-hospitalisation coverage
        _make_rule(
            rule_id="RULE_PMJAY_POST_HOSP_15_DAYS",
            unit=u_pre_post,
            scheme="PM_JAY",
            rule_parameter="post_hospitalisation_coverage_days",
            maximum_rate=15.0,
            minimum_value=None,
            allowed_values=[15.0],
            numeric_operator="le",
            unit_name="days",
            crop_category="post_hospitalisation_expenses",
            entity_scope="post_hospitalisation_expenses",
            basis="days_after_hospital_discharge",
            qualifier="up_to_15_days_post_hospitalisation",
        ),
        # 6. 1949 health benefit packages
        _make_rule(
            rule_id="RULE_PMJAY_HBP_1949_PACKAGES",
            unit=u_pre_post,
            scheme="PM_JAY",
            rule_parameter="health_benefit_packages_count",
            maximum_rate=1949.0,
            minimum_value=1949.0,
            allowed_values=[1949.0],
            numeric_operator="ge",
            unit_name="packages",
            crop_category="health_benefit_packages",
            entity_scope="health_benefit_packages",
            basis="national_health_benefit_package_master",
            qualifier="secondary_and_tertiary_procedures",
        ),
        # 7. 70 years senior citizen universal age threshold
        _make_rule(
            rule_id="RULE_PMJAY_SENIOR_AGE_70_YEARS",
            unit=u_senior,
            scheme="PM_JAY",
            rule_parameter="senior_citizen_age_eligibility_years",
            maximum_rate=70.0,
            minimum_value=70.0,
            allowed_values=[70.0],
            numeric_operator="ge",
            unit_name="years",
            crop_category="senior_citizens_70_plus",
            entity_scope="senior_citizens_70_plus",
            basis="minimum_age_for_universal_senior_citizen_cover",
            qualifier="aged_70_years_and_above_irrespective_of_income",
        ),
        # 8. Rs 5,00,000 senior citizen top-up / family cover
        _make_rule(
            rule_id="RULE_PMJAY_SENIOR_TOPUP_5_LAKH",
            unit=u_senior,
            scheme="PM_JAY",
            rule_parameter="senior_citizen_topup_cover_inr",
            maximum_rate=500000.0,
            numeric_operator="eq",
            unit_name="rupees",
            crop_category="senior_citizens_70_plus",
            entity_scope="senior_citizens_70_plus",
            basis="per_family_per_year_for_senior_citizens_70_plus",
            qualifier="dedicated_topup_cover_for_senior_citizens_aged_70_plus",
        ),
        # 9. 60% Central funding share (General States)
        _make_rule(
            rule_id="RULE_PMJAY_CENTRAL_SHARE_GENERAL_60PCT",
            unit=u_funding,
            scheme="PM_JAY",
            rule_parameter="central_funding_share_pct",
            maximum_rate=60.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="general_states",
            entity_scope="general_states",
            geography="general_states",
            basis="total_scheme_premium_cost",
            qualifier="60_40_centre_state_ratio_for_general_states",
            conditions={"geography": "general_states"},
        ),
        # 10. 40% State funding share (General States)
        _make_rule(
            rule_id="RULE_PMJAY_STATE_SHARE_GENERAL_40PCT",
            unit=u_funding,
            scheme="PM_JAY",
            rule_parameter="state_funding_share_pct",
            maximum_rate=40.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="general_states",
            entity_scope="general_states",
            geography="general_states",
            basis="total_scheme_premium_cost",
            qualifier="40_percent_state_share_in_general_states",
            conditions={"geography": "general_states"},
        ),
        # 11. 90% Central funding share (NE & Himalayan States)
        _make_rule(
            rule_id="RULE_PMJAY_CENTRAL_SHARE_NER_90PCT",
            unit=u_funding,
            scheme="PM_JAY",
            rule_parameter="central_funding_share_pct",
            maximum_rate=90.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="north_eastern_states",
            entity_scope="north_eastern_states",
            geography="north_eastern_states",
            basis="total_scheme_premium_cost",
            qualifier="90_10_centre_state_ratio_for_ner_and_himalayan_states",
            conditions={"geography": "north_eastern_states"},
        ),
        # 12. 10% State funding share (NE & Himalayan States)
        _make_rule(
            rule_id="RULE_PMJAY_STATE_SHARE_NER_10PCT",
            unit=u_funding,
            scheme="PM_JAY",
            rule_parameter="state_funding_share_pct",
            maximum_rate=10.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="north_eastern_states",
            entity_scope="north_eastern_states",
            geography="north_eastern_states",
            basis="total_scheme_premium_cost",
            qualifier="10_percent_state_share_in_ner_and_himalayan_states",
            conditions={"geography": "north_eastern_states"},
        ),
        # 13. 100% Central funding share (UTs without legislature)
        _make_rule(
            rule_id="RULE_PMJAY_CENTRAL_SHARE_UT_100PCT",
            unit=u_funding,
            scheme="PM_JAY",
            rule_parameter="central_funding_share_pct",
            maximum_rate=100.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="union_territories",
            entity_scope="union_territories",
            geography="union_territories",
            basis="total_scheme_premium_cost",
            qualifier="100_percent_central_funding_for_uts_without_legislature",
            conditions={"geography": "union_territories"},
        ),
        # 14. 15 days intra-state hospital claim settlement turnaround
        _make_rule(
            rule_id="RULE_PMJAY_CLAIM_SETTLEMENT_INTRASTATE_15D",
            unit=u_claims_hosp,
            scheme="PM_JAY",
            rule_parameter="claim_settlement_turnaround_days",
            maximum_rate=15.0,
            minimum_value=None,
            allowed_values=[15.0],
            numeric_operator="le",
            unit_name="days",
            crop_category="intrastate_empanelled_hospitals",
            entity_scope="intrastate_empanelled_hospitals",
            basis="days_from_claim_submission",
            qualifier="within_15_days_for_intrastate_hospital_claims",
            conditions={"claim_scope": "intrastate"},
        ),
        # 15. 30 days inter-state portability claim settlement turnaround
        _make_rule(
            rule_id="RULE_PMJAY_CLAIM_SETTLEMENT_PORTABILITY_30D",
            unit=u_claims_hosp,
            scheme="PM_JAY",
            rule_parameter="claim_settlement_turnaround_days_portability",
            maximum_rate=30.0,
            minimum_value=None,
            allowed_values=[30.0],
            numeric_operator="le",
            unit_name="days",
            crop_category="interstate_portability_hospitals",
            entity_scope="interstate_portability_hospitals",
            basis="days_from_claim_submission",
            qualifier="within_30_days_for_interstate_portability_claims",
            conditions={"claim_scope": "portability"},
        ),
        # 16. 1% per week penal interest on delayed hospital claims
        _make_rule(
            rule_id="RULE_PMJAY_DELAY_INTEREST_1PCT_WEEKLY",
            unit=u_claims_hosp,
            scheme="PM_JAY",
            rule_parameter="delayed_claim_penal_interest_weekly_pct",
            maximum_rate=1.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="delayed_hospital_claim_settlement",
            entity_scope="delayed_hospital_claim_settlement",
            basis="claimed_amount_per_week_of_delay",
            qualifier="1_percent_per_week_beyond_turnaround_time",
            frequency="weekly",
        ),
        # 17. 6 hours pre-authorization turnaround
        _make_rule(
            rule_id="RULE_PMJAY_PREAUTH_6_HOURS",
            unit=u_claims_hosp,
            scheme="PM_JAY",
            rule_parameter="pre_authorization_turnaround_hours",
            maximum_rate=6.0,
            minimum_value=None,
            allowed_values=[6.0],
            numeric_operator="le",
            unit_name="hours",
            crop_category="pre_authorization_approval",
            entity_scope="pre_authorization_approval",
            basis="hours_from_preauth_request",
            qualifier="within_6_hours_decision_window",
        ),
        # 18. 24 hours deemed auto-approval ceiling
        _make_rule(
            rule_id="RULE_PMJAY_PREAUTH_AUTO_24_HOURS",
            unit=u_claims_hosp,
            scheme="PM_JAY",
            rule_parameter="pre_authorization_auto_approval_hours",
            maximum_rate=24.0,
            minimum_value=None,
            allowed_values=[24.0],
            numeric_operator="le",
            unit_name="hours",
            crop_category="pre_authorization_auto_approval",
            entity_scope="pre_authorization_auto_approval",
            basis="hours_from_preauth_request",
            qualifier="deemed_auto_approved_after_24_hours",
        ),
        # 19. 10 beds minimum hospital capacity for empanelment
        _make_rule(
            rule_id="RULE_PMJAY_EMPANELMENT_MIN_10_BEDS",
            unit=u_claims_hosp,
            scheme="PM_JAY",
            rule_parameter="minimum_hospital_beds_general_empanelment",
            maximum_rate=10.0,
            minimum_value=10.0,
            allowed_values=[10.0],
            numeric_operator="ge",
            unit_name="beds",
            crop_category="general_private_hospital_empanelment",
            entity_scope="general_private_hospital_empanelment",
            basis="inpatient_bed_capacity",
            qualifier="minimum_10_beds_for_general_hospital_empanelment",
        ),
    ]

    all_rules = extract_structured_rules_from_units("PM_JAY", units, curated_rules)
    return units, all_rules


def _build_pmayg_data() -> tuple[list[ExtractedEvidenceUnit], list[StructuredRuleRecord]]:
    doc_args = {
        "document_id": "DOC_PMAYG_FRAMEWORK_2020",
        "source_url": "https://pmayg.nic.in/netiwas/uploaded/guidelines.pdf",
        "document_title": "Pradhan Mantri Awas Yojana — Gramin (PMAY-G) Framework for Implementation",
        "document_version": "revised_framework",
        "publication_date": "2020-01-01",
        "effective_from": "2016-11-20",
        "effective_to": None,
        "policy_era": "pmayg_current",
    }

    u_assist = _make_unit(
        evidence_id="EV_PMAYG_UNIT_ASSISTANCE_CHUNK_1",
        physical_pdf_page=4,
        printed_page="4",
        section="Clause 4.1",
        text=(
            "[UNIT ASSISTANCE NORMS] The unit assistance under PMAY-G is Rs 120000 in plain areas "
            "and Rs 130000 in hilly states, difficult areas, and Integrated Action Plan (IAP) districts. "
            "The minimum size of the house has been fixed at 25 sq. metres including a dedicated hygienic cooking space."
        ),
        **doc_args,
    )
    u_tbl_r1 = _make_unit(
        evidence_id="EV_PMAYG_TBL_ASSISTANCE_R1",
        physical_pdf_page=5,
        printed_page="5",
        section="Clause 4.2 (Table 2)",
        evidence_type="table_row",
        table_id="TBL_PMAYG_GRANTS",
        row_id="TBL_PMAYG_GRANTS_R1",
        headers=["Region_Type", "Unit_Assistance_INR", "Minimum_House_Area_Sqm"],
        text="[Table: PMAY-G Financial Norms] Region_Type: Plain Areas | Unit_Assistance_INR: 120000 | Minimum_House_Area_Sqm: 25",
        cells=["Plain Areas", "120000", "25"],
        **doc_args,
    )
    u_tbl_r2 = _make_unit(
        evidence_id="EV_PMAYG_TBL_ASSISTANCE_R2",
        physical_pdf_page=5,
        printed_page="5",
        section="Clause 4.2 (Table 2)",
        evidence_type="table_row",
        table_id="TBL_PMAYG_GRANTS",
        row_id="TBL_PMAYG_GRANTS_R2",
        headers=["Region_Type", "Unit_Assistance_INR", "Minimum_House_Area_Sqm"],
        text="[Table: PMAY-G Financial Norms] Region_Type: Hilly States and Difficult Areas | Unit_Assistance_INR: 130000 | Minimum_House_Area_Sqm: 25",
        cells=["Hilly States and Difficult Areas", "130000", "25"],
        **doc_args,
    )
    u_convergence = _make_unit(
        evidence_id="EV_PMAYG_CONVERGENCE_LOAN_CHUNK_1",
        physical_pdf_page=6,
        printed_page="6",
        section="Clauses 4.3-4.5",
        text=(
            "[CONVERGENCE FOR TOILET, MGNREGS LABOUR AND OPTIONAL LOAN] Under PMAY-G, beneficiaries receive "
            "Rs 12000 for construction of a household toilet in convergence with Swachh Bharat Mission-Gramin "
            "(SBM-G). Additionally, beneficiaries are entitled to 90 person-days of unskilled manual labour "
            "wages under MGNREGA in plain areas and 95 person-days in hilly states, difficult areas, and IAP "
            "districts. Beneficiaries may also avail an optional institutional bank loan of up to Rs 70000 "
            "with a 3 percent interest subvention."
        ),
        **doc_args,
    )
    u_sharing = _make_unit(
        evidence_id="EV_PMAYG_COST_SHARING_CHUNK_1",
        physical_pdf_page=7,
        printed_page="7",
        section="Clause 5.1 (Table 3 — Cost Sharing Pattern)",
        text=(
            "[CENTRE-STATE COST SHARING PATTERN] The cost of unit assistance under PMAY-G is shared between "
            "the Central and State Governments in the ratio 60:40 (60 percent Central share and 40 percent "
            "State share) in plain areas, and in the ratio 90:10 (90 percent Central share and 10 percent "
            "State share) in North Eastern States and Himalayan States (Himachal Pradesh, Uttarakhand, and "
            "UT of Jammu & Kashmir). In Union Territories without legislature, 100 percent of the cost is "
            "borne by the Central Government."
        ),
        **doc_args,
    )
    u_targets_timeline = _make_unit(
        evidence_id="EV_PMAYG_TIMELINE_EARMARKING_CHUNK_1",
        physical_pdf_page=8,
        printed_page="8",
        section="Clauses 3.2, 6.1-6.2 & 9.1",
        text=(
            "[CONSTRUCTION TIMELINE, INSTALMENTS, TARGET EARMARKING AND ADMIN CAP] House construction under "
            "PMAY-G shall be completed within 12 months from the date of sanction of the first instalment. "
            "Funds are transferred electronically in a minimum of 3 instalments linked to geo-tagged stages "
            "of construction. At the national level, at least 60 percent of targets are earmarked for SC/ST "
            "households, up to 15 percent for minority households, and at least 5 percent reservation for "
            "Persons with Disabilities (PwD). Administrative expenses are capped at 2 percent of programme funds."
        ),
        **doc_args,
    )
    u_hist_iay = _make_unit(
        evidence_id="EV_PMAYG_IAY_HIST_CHUNK_1",
        document_id="DOC_PMAYG_FRAMEWORK_2020",
        source_url="https://pmayg.nic.in/netiwas/uploaded/guidelines.pdf",
        document_title="Pradhan Mantri Awas Yojana — Gramin (PMAY-G) Framework for Implementation",
        document_version="revised_framework",
        publication_date="2020-01-01",
        effective_from="1996-01-01",
        effective_to="2016-03-31",
        physical_pdf_page=2,
        printed_page="2",
        section="Clause 1.2 (Historical IAY Baseline)",
        policy_era="iay_historical_pre2016",
        text=(
            "[HISTORICAL IAY COMPARISON] Prior to the restructuring into PMAY-G in April 2016, under the "
            "erstwhile Indira Awaas Yojana (IAY), the minimum house area was 20 sq. metres and the unit "
            "assistance was Rs 70000 in plain areas and Rs 75000 in hilly/difficult areas."
        ),
    )

    units = [u_assist, u_tbl_r1, u_tbl_r2, u_convergence, u_sharing, u_targets_timeline, u_hist_iay]

    curated_rules = [
        # 1. Rs 1,20,000 unit assistance in plain areas
        _make_rule(
            rule_id="RULE_PMAYG_PLAINS_120K",
            unit=u_tbl_r1,
            scheme="PMAY_G",
            rule_parameter="unit_grant_assistance_inr",
            maximum_rate=120000.0,
            numeric_operator="eq",
            unit_name="rupees",
            crop_category="rural_beneficiary",
            entity_scope="rural_beneficiary",
            geography="plains_areas",
            basis="per_housing_unit",
            qualifier="plain_areas",
            requires_qualifier_for_unconditional_claim=True,
            conditions={"geography": "plains_areas", "beneficiary_type": "rural_beneficiary"},
            frequency="one_time_grant",
        ),
        # 2. Rs 1,30,000 unit assistance in hilly/difficult/IAP areas
        _make_rule(
            rule_id="RULE_PMAYG_HILLY_130K",
            unit=u_tbl_r2,
            scheme="PMAY_G",
            rule_parameter="unit_grant_assistance_inr",
            maximum_rate=130000.0,
            numeric_operator="eq",
            unit_name="rupees",
            crop_category="rural_beneficiary",
            entity_scope="rural_beneficiary",
            geography="hilly_and_difficult_areas",
            basis="per_housing_unit",
            qualifier="hilly_states_and_difficult_areas",
            requires_qualifier_for_unconditional_claim=True,
            conditions={"geography": "hilly_and_difficult_areas", "beneficiary_type": "rural_beneficiary"},
            frequency="one_time_grant",
        ),
        # 3. 25 sq. metres minimum house area
        _make_rule(
            rule_id="RULE_PMAYG_MINIMUM_AREA_25",
            unit=u_assist,
            scheme="PMAY_G",
            rule_parameter="minimum_house_size_sqm",
            maximum_rate=25.0,
            minimum_value=25.0,
            allowed_values=[25.0],
            numeric_operator="ge",
            unit_name="square_metres",
            crop_category="rural_beneficiary",
            entity_scope="rural_beneficiary",
            geography="all_india",
            basis="house_floor_area",
            qualifier="including_hygienic_cooking_space",
            frequency="one_time_grant",
        ),
        # 4. Rs 12,000 toilet assistance under SBM-G convergence
        _make_rule(
            rule_id="RULE_PMAYG_TOILET_ASSISTANCE_12K",
            unit=u_convergence,
            scheme="PMAY_G",
            rule_parameter="toilet_construction_assistance_inr",
            maximum_rate=12000.0,
            numeric_operator="eq",
            unit_name="rupees",
            crop_category="toilet_convergence_sbmg",
            entity_scope="toilet_convergence_sbmg",
            basis="per_household_toilet",
            qualifier="in_convergence_with_sbmg_or_mgnrega",
            frequency="one_time_grant",
        ),
        # 5. 90 person-days MGNREGA unskilled labour (plain areas)
        _make_rule(
            rule_id="RULE_PMAYG_MGNREGA_90_DAYS_PLAINS",
            unit=u_convergence,
            scheme="PMAY_G",
            rule_parameter="mgnrega_unskilled_labour_person_days",
            maximum_rate=90.0,
            numeric_operator="eq",
            unit_name="days",
            crop_category="mgnrega_convergence_plains",
            entity_scope="mgnrega_convergence_plains",
            geography="plains_areas",
            basis="unskilled_mgnrega_person_days",
            qualifier="plain_areas_mgnrega_convergence",
            conditions={"geography": "plains_areas"},
        ),
        # 6. 95 person-days MGNREGA unskilled labour (hilly/difficult/IAP areas)
        _make_rule(
            rule_id="RULE_PMAYG_MGNREGA_95_DAYS_HILLY",
            unit=u_convergence,
            scheme="PMAY_G",
            rule_parameter="mgnrega_unskilled_labour_person_days",
            maximum_rate=95.0,
            numeric_operator="eq",
            unit_name="days",
            crop_category="mgnrega_convergence_hilly",
            entity_scope="mgnrega_convergence_hilly",
            geography="hilly_and_difficult_areas",
            basis="unskilled_mgnrega_person_days",
            qualifier="hilly_and_difficult_areas_mgnrega_convergence",
            conditions={"geography": "hilly_and_difficult_areas"},
        ),
        # 7. Rs 70,000 optional institutional bank loan cap
        _make_rule(
            rule_id="RULE_PMAYG_OPTIONAL_LOAN_70K",
            unit=u_convergence,
            scheme="PMAY_G",
            rule_parameter="optional_institutional_loan_cap_inr",
            maximum_rate=70000.0,
            minimum_value=None,
            allowed_values=[70000.0],
            numeric_operator="le",
            unit_name="rupees",
            crop_category="optional_housing_loan",
            entity_scope="optional_housing_loan",
            basis="per_housing_unit_loan",
            qualifier="optional_institutional_credit_up_to_70000",
        ),
        # 8. 3% interest subvention on optional loan
        _make_rule(
            rule_id="RULE_PMAYG_LOAN_INTEREST_SUBVENTION_3PCT",
            unit=u_convergence,
            scheme="PMAY_G",
            rule_parameter="loan_interest_subvention_pct",
            maximum_rate=3.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="optional_housing_loan",
            entity_scope="optional_housing_loan",
            basis="per_annum_on_optional_loan_up_to_70000",
            qualifier="3_percent_interest_subvention",
        ),
        # 9. 60% Central share in plain areas
        _make_rule(
            rule_id="RULE_PMAYG_CENTRAL_SHARE_PLAINS_60PCT",
            unit=u_sharing,
            scheme="PMAY_G",
            rule_parameter="central_funding_share_pct",
            maximum_rate=60.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="centre_state_sharing_plains",
            entity_scope="centre_state_sharing_plains",
            geography="plains_areas",
            basis="unit_assistance_cost",
            qualifier="60_40_sharing_in_plain_areas",
            conditions={"geography": "plains_areas"},
        ),
        # 10. 40% State share in plain areas
        _make_rule(
            rule_id="RULE_PMAYG_STATE_SHARE_PLAINS_40PCT",
            unit=u_sharing,
            scheme="PMAY_G",
            rule_parameter="state_funding_share_pct",
            maximum_rate=40.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="centre_state_sharing_plains",
            entity_scope="centre_state_sharing_plains",
            geography="plains_areas",
            basis="unit_assistance_cost",
            qualifier="40_percent_state_share_in_plain_areas",
            conditions={"geography": "plains_areas"},
        ),
        # 11. 90% Central share in NE & Himalayan states
        _make_rule(
            rule_id="RULE_PMAYG_CENTRAL_SHARE_HILLY_90PCT",
            unit=u_sharing,
            scheme="PMAY_G",
            rule_parameter="central_funding_share_pct",
            maximum_rate=90.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="centre_state_sharing_hilly",
            entity_scope="centre_state_sharing_hilly",
            geography="hilly_and_difficult_areas",
            basis="unit_assistance_cost",
            qualifier="90_10_sharing_in_ner_and_himalayan_states",
            conditions={"geography": "hilly_and_difficult_areas"},
        ),
        # 12. 10% State share in NE & Himalayan states
        _make_rule(
            rule_id="RULE_PMAYG_STATE_SHARE_HILLY_10PCT",
            unit=u_sharing,
            scheme="PMAY_G",
            rule_parameter="state_funding_share_pct",
            maximum_rate=10.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="centre_state_sharing_hilly",
            entity_scope="centre_state_sharing_hilly",
            geography="hilly_and_difficult_areas",
            basis="unit_assistance_cost",
            qualifier="10_percent_state_share_in_ner_and_himalayan_states",
            conditions={"geography": "hilly_and_difficult_areas"},
        ),
        # 13. 100% Central share in Union Territories
        _make_rule(
            rule_id="RULE_PMAYG_CENTRAL_SHARE_UT_100PCT",
            unit=u_sharing,
            scheme="PMAY_G",
            rule_parameter="central_funding_share_pct",
            maximum_rate=100.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="centre_sharing_union_territories",
            entity_scope="centre_sharing_union_territories",
            geography="union_territories",
            basis="unit_assistance_cost",
            qualifier="100_percent_central_share_in_union_territories",
            conditions={"geography": "union_territories"},
        ),
        # 14. 12 months construction completion timeline
        _make_rule(
            rule_id="RULE_PMAYG_COMPLETION_12_MONTHS",
            unit=u_targets_timeline,
            scheme="PMAY_G",
            rule_parameter="construction_completion_timeline_months",
            maximum_rate=12.0,
            minimum_value=None,
            allowed_values=[12.0],
            numeric_operator="le",
            unit_name="months",
            crop_category="house_construction_completion",
            entity_scope="house_construction_completion",
            basis="from_date_of_sanction_of_first_instalment",
            qualifier="within_12_months_of_sanction",
        ),
        # 15. Minimum 3 instalments linked to geo-tagged stages
        _make_rule(
            rule_id="RULE_PMAYG_MIN_3_INSTALMENTS",
            unit=u_targets_timeline,
            scheme="PMAY_G",
            rule_parameter="minimum_disbursement_instalments_count",
            maximum_rate=3.0,
            minimum_value=3.0,
            allowed_values=[3.0, 4.0],
            numeric_operator="ge",
            unit_name="instalments",
            crop_category="geo_tagged_instalments",
            entity_scope="geo_tagged_instalments",
            basis="construction_stage_linked_tranches",
            qualifier="minimum_3_geo_tagged_instalments",
        ),
        # 16. 60% SC/ST target earmarking
        _make_rule(
            rule_id="RULE_PMAYG_SC_ST_EARMARKING_60PCT",
            unit=u_targets_timeline,
            scheme="PMAY_G",
            rule_parameter="sc_st_target_earmarking_pct",
            maximum_rate=60.0,
            minimum_value=60.0,
            allowed_values=[60.0],
            numeric_operator="ge",
            unit_name="percent",
            crop_category="sc_st_households",
            entity_scope="sc_st_households",
            basis="total_national_housing_targets",
            qualifier="at_least_60_percent_for_sc_st_households",
            conditions={"beneficiary_type": "sc_st_households"},
        ),
        # 17. 15% minority target earmarking cap
        _make_rule(
            rule_id="RULE_PMAYG_MINORITY_EARMARKING_15PCT",
            unit=u_targets_timeline,
            scheme="PMAY_G",
            rule_parameter="minority_target_earmarking_pct",
            maximum_rate=15.0,
            minimum_value=None,
            allowed_values=[15.0],
            numeric_operator="le",
            unit_name="percent",
            crop_category="minority_households",
            entity_scope="minority_households",
            basis="total_national_housing_targets",
            qualifier="up_to_15_percent_for_minority_households",
            conditions={"beneficiary_type": "minority_households"},
        ),
        # 18. 5% PwD reservation
        _make_rule(
            rule_id="RULE_PMAYG_PWD_RESERVATION_5PCT",
            unit=u_targets_timeline,
            scheme="PMAY_G",
            rule_parameter="pwd_reservation_pct",
            maximum_rate=5.0,
            minimum_value=5.0,
            allowed_values=[5.0],
            numeric_operator="ge",
            unit_name="percent",
            crop_category="persons_with_disabilities",
            entity_scope="persons_with_disabilities",
            basis="horizontal_beneficiary_reservation",
            qualifier="at_least_5_percent_for_pwd",
            conditions={"beneficiary_type": "persons_with_disabilities"},
        ),
        # 19. 2% administrative funds ceiling
        _make_rule(
            rule_id="RULE_PMAYG_ADMIN_FUNDS_CAP_2PCT",
            unit=u_targets_timeline,
            scheme="PMAY_G",
            rule_parameter="administrative_funds_ceiling_pct",
            maximum_rate=2.0,
            minimum_value=None,
            allowed_values=[2.0],
            numeric_operator="le",
            unit_name="percent",
            crop_category="administrative_expenses",
            entity_scope="administrative_expenses",
            basis="total_programme_funds",
            qualifier="maximum_2_percent_administrative_allocation",
        ),
        # 20. Historical IAY 20 sq.m minimum house size
        _make_rule(
            rule_id="RULE_PMAYG_HIST_IAY_AREA_20SQM",
            unit=u_hist_iay,
            scheme="PMAY_G",
            rule_parameter="minimum_house_size_sqm",
            maximum_rate=20.0,
            minimum_value=20.0,
            allowed_values=[20.0],
            numeric_operator="ge",
            unit_name="square_metres",
            crop_category="rural_beneficiary",
            entity_scope="rural_beneficiary",
            basis="house_floor_area",
            qualifier="historical_iay_pre_2016_norm",
        ),
    ]

    all_rules = extract_structured_rules_from_units("PMAY_G", units, curated_rules)
    return units, all_rules


def _build_pmkusum_data() -> tuple[list[ExtractedEvidenceUnit], list[StructuredRuleRecord]]:
    doc_args = {
        "document_id": "DOC_PMKUSUM_GUIDELINES_2021",
        "source_url": "https://mnre.gov.in/kusum/guidelines.pdf",
        "document_title": "PM-KUSUM Operational Guidelines — Component A, B & C",
        "document_version": "official_guidelines",
        "publication_date": "2021-01-01",
        "effective_from": "2019-03-08",
        "effective_to": None,
        "policy_era": "pmkusum_current",
    }

    u_comp_b = _make_unit(
        evidence_id="EV_PMKUSUM_SUBSIDY_CHUNK_1",
        physical_pdf_page=3,
        printed_page="3",
        section="Clause 3.1",
        text=(
            "[FINANCIAL ASSISTANCE FOR SOLAR PUMPS] Under Component-B of PM-KUSUM, Central Financial Assistance (CFA) "
            "of 30 percent of the benchmark cost or tender cost, whichever is lower, is provided by the Central Government. "
            "The State Government provides a subsidy of at least 30 percent, and the remaining 40 percent is provided by the farmer. "
            "Subsidy is available for standalone solar pumps up to 7.5 HP capacity."
        ),
        **doc_args,
    )
    u_comp_b_loan_ner = _make_unit(
        evidence_id="EV_PMKUSUM_COMPB_NER_LOAN_CHUNK_1",
        physical_pdf_page=4,
        printed_page="4",
        section="Clause 3.2 & 3.3",
        text=(
            "[SPECIAL CATEGORY STATES SUBSIDY AND BANK LOAN FINANCING] In General States, out of the 40 percent "
            "farmer share under Component-B and Component-C, farmers may avail bank loan financing for up to "
            "30 percent of the total cost and pay the remaining 10 percent as upfront farmer margin money. "
            "In North Eastern States, Sikkim, Jammu & Kashmir, Ladakh, Himachal Pradesh, Uttarakhand, and "
            "Island UTs (Lakshadweep and Andaman & Nicobar), Central Financial Assistance (CFA) is enhanced to "
            "50 percent of benchmark/tender cost, State Government provides at least 30 percent (total subsidy "
            "80 percent), and the farmer bears only 20 percent of the cost. For FPOs and cluster community "
            "irrigation, solar pumps up to 15 HP are permitted with CFA capped at the 7.5 HP level."
        ),
        **doc_args,
    )
    u_comp_a = _make_unit(
        evidence_id="EV_PMKUSUM_COMPA_PLANTS_CHUNK_1",
        physical_pdf_page=2,
        printed_page="2",
        section="Clauses 1.1 & 2.1-2.4 (Component-A Solar Power Plants)",
        text=(
            "[COMPONENT-A DECENTRALIZED SOLAR POWER PLANTS AND DISCOM PBI] Component-A of PM-KUSUM targets "
            "setting up 10000 MW of decentralized ground-mounted or stilt-mounted renewable solar power plants. "
            "Each individual solar power plant under Component-A must have a minimum capacity of 500 kW and a "
            "maximum capacity of 2 MW, located within a 5 km radius of the 33/11 kV distribution substation. "
            "Distribution Companies (DISCOMs) are eligible for a Performance Based Incentive (PBI) of Rs 0.40 "
            "per kWh (or a maximum cap of Rs 660000 per MW per year, whichever is less) for a period of "
            "5 years from the Commercial Operation Date."
        ),
        **doc_args,
    )
    u_comp_c_cmc = _make_unit(
        evidence_id="EV_PMKUSUM_COMPC_CMC_CHUNK_1",
        physical_pdf_page=5,
        printed_page="5",
        section="Clauses 4.2 & 5.1 (Component-C & Mandatory Vendor CMC)",
        text=(
            "[COMPONENT-C GRID-CONNECTED SOLARISATION AND VENDOR CMC] Under Component-C of PM-KUSUM "
            "(solarisation of existing grid-connected agricultural pumps up to 7.5 HP), solar PV capacity in kW "
            "is permitted up to 2 times the pump capacity in HP so farmers can feed surplus solar power into "
            "the grid. Empanelled vendors must provide a mandatory Comprehensive Maintenance Contract (CMC) "
            "for at least 5 years."
        ),
        **doc_args,
    )
    u_tbl_r1 = _make_unit(
        evidence_id="EV_PMKUSUM_TBL_SUBSIDY_R1",
        physical_pdf_page=4,
        printed_page="4",
        section="Clause 3.2 (Table 1)",
        evidence_type="table_row",
        table_id="TBL_PMKUSUM_SUBSIDY_SHARING",
        row_id="TBL_PMKUSUM_SUBSIDY_SHARING_R1",
        headers=["State_Category", "Central_CFA_Pct", "State_Subsidy_Pct", "Total_Subsidy_Pct", "Farmer_Share_Pct", "Max_Pump_HP"],
        text="[Table: PM-KUSUM Component B & C Subsidy Pattern] State_Category: General States | Central_CFA_Pct: 30% | State_Subsidy_Pct: 30% | Total_Subsidy_Pct: 60% | Farmer_Share_Pct: 40% | Max_Pump_HP: 7.5 HP",
        cells=["General States", "30%", "30%", "60%", "40%", "7.5 HP"],
        **doc_args,
    )
    u_tbl_r2 = _make_unit(
        evidence_id="EV_PMKUSUM_TBL_SUBSIDY_R2",
        physical_pdf_page=4,
        printed_page="4",
        section="Clause 3.2 (Table 1)",
        evidence_type="table_row",
        table_id="TBL_PMKUSUM_SUBSIDY_SHARING",
        row_id="TBL_PMKUSUM_SUBSIDY_SHARING_R2",
        headers=["State_Category", "Central_CFA_Pct", "State_Subsidy_Pct", "Total_Subsidy_Pct", "Farmer_Share_Pct", "Max_Pump_HP"],
        text="[Table: PM-KUSUM Component B & C Subsidy Pattern] State_Category: North Eastern, Hilly States & Island UTs | Central_CFA_Pct: 50% | State_Subsidy_Pct: 30% | Total_Subsidy_Pct: 80% | Farmer_Share_Pct: 20% | Max_Pump_HP: 7.5 HP",
        cells=["North Eastern, Hilly States & Island UTs", "50%", "30%", "80%", "20%", "7.5 HP"],
        **doc_args,
    )

    units = [u_comp_b, u_comp_b_loan_ner, u_comp_a, u_comp_c_cmc, u_tbl_r1, u_tbl_r2]

    curated_rules = [
        # 1. 30% Central CFA (General States)
        _make_rule(
            rule_id="RULE_PMKUSUM_CFA_30PCT",
            unit=u_comp_b,
            scheme="PM_KUSUM",
            rule_parameter="central_subsidy_pct",
            maximum_rate=30.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="individual_farmers",
            entity_scope="individual_farmers",
            geography="all_india",
            basis="benchmark_or_tender_cost",
            qualifier="central_financial_assistance",
            frequency="one_time_capital_subsidy",
            conditions={"beneficiary_type": "individual_farmers", "geography": "all_india"},
        ),
        # 2. 30% State subsidy (All States)
        _make_rule(
            rule_id="RULE_PMKUSUM_STATE_SUBSIDY_30PCT",
            unit=u_comp_b,
            scheme="PM_KUSUM",
            rule_parameter="state_subsidy_pct",
            maximum_rate=30.0,
            minimum_value=30.0,
            allowed_values=[30.0],
            numeric_operator="ge",
            unit_name="percent",
            crop_category="individual_farmers",
            entity_scope="individual_farmers",
            geography="all_india",
            basis="benchmark_or_tender_cost",
            qualifier="at_least_30_percent_state_government_subsidy",
            frequency="one_time_capital_subsidy",
        ),
        # 3. 60% Total subsidy (General States)
        _make_rule(
            rule_id="RULE_PMKUSUM_TOTAL_SUBSIDY_60PCT",
            unit=u_comp_b,
            scheme="PM_KUSUM",
            rule_parameter="total_subsidy_pct",
            maximum_rate=60.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="individual_farmers",
            entity_scope="individual_farmers",
            geography="all_india",
            basis="benchmark_or_tender_cost",
            qualifier="central_plus_state_subsidy",
            frequency="one_time_capital_subsidy",
            conditions={"beneficiary_type": "individual_farmers", "geography": "all_india"},
        ),
        # 4. 40% Farmer contribution (General States)
        _make_rule(
            rule_id="RULE_PMKUSUM_FARMER_SHARE_40PCT",
            unit=u_comp_b,
            scheme="PM_KUSUM",
            rule_parameter="farmer_contribution_pct",
            maximum_rate=40.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="individual_farmers",
            entity_scope="individual_farmers",
            geography="all_india",
            basis="benchmark_or_tender_cost",
            qualifier="remaining_40_percent_borne_by_farmer_in_general_states",
            frequency="one_time_capital_subsidy",
            conditions={"beneficiary_type": "individual_farmers", "geography": "all_india"},
        ),
        # 5. 7.5 HP individual solar pump capacity limit
        _make_rule(
            rule_id="RULE_PMKUSUM_PUMP_CAPACITY_7_5",
            unit=u_comp_b,
            scheme="PM_KUSUM",
            rule_parameter="max_pump_capacity_hp",
            maximum_rate=7.5,
            minimum_value=None,
            allowed_values=[7.5],
            numeric_operator="le",
            unit_name="horsepower",
            crop_category="individual_farmers",
            entity_scope="individual_farmers",
            geography="all_india",
            basis="standalone_pump_capacity",
            qualifier="component_b_standalone_pumps",
            frequency="one_time_capital_subsidy",
        ),
        # 6. 30% bank loan financing share
        _make_rule(
            rule_id="RULE_PMKUSUM_BANK_LOAN_30PCT",
            unit=u_comp_b_loan_ner,
            scheme="PM_KUSUM",
            rule_parameter="farmer_bank_loan_share_pct",
            maximum_rate=30.0,
            minimum_value=None,
            allowed_values=[30.0],
            numeric_operator="le",
            unit_name="percent",
            crop_category="bank_loan_component",
            entity_scope="bank_loan_component",
            basis="benchmark_or_tender_cost",
            qualifier="up_to_30_percent_bank_credit_within_40_percent_farmer_share",
        ),
        # 7. 10% upfront farmer margin money (when availing 30% bank loan)
        _make_rule(
            rule_id="RULE_PMKUSUM_FARMER_MARGIN_10PCT",
            unit=u_comp_b_loan_ner,
            scheme="PM_KUSUM",
            rule_parameter="farmer_upfront_margin_pct",
            maximum_rate=10.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="farmer_down_payment",
            entity_scope="farmer_down_payment",
            basis="benchmark_or_tender_cost",
            qualifier="10_percent_upfront_margin_with_30_percent_bank_loan",
        ),
        # 8. 50% Central CFA in NE, Hilly States & Island UTs
        _make_rule(
            rule_id="RULE_PMKUSUM_CFA_NER_50PCT",
            unit=u_tbl_r2,
            scheme="PM_KUSUM",
            rule_parameter="central_subsidy_pct",
            maximum_rate=50.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="individual_farmers_special_states",
            entity_scope="individual_farmers_special_states",
            geography="north_eastern_states",
            basis="benchmark_or_tender_cost",
            qualifier="enhanced_50_percent_cfa_for_ner_hilly_and_island_states",
            conditions={"beneficiary_type": "individual_farmers", "geography": "north_eastern_states"},
            frequency="one_time_capital_subsidy",
        ),
        # 9. 80% Total subsidy in NE, Hilly States & Island UTs
        _make_rule(
            rule_id="RULE_PMKUSUM_TOTAL_SUBSIDY_NER_80PCT",
            unit=u_tbl_r2,
            scheme="PM_KUSUM",
            rule_parameter="total_subsidy_pct",
            maximum_rate=80.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="individual_farmers_special_states",
            entity_scope="individual_farmers_special_states",
            geography="north_eastern_states",
            basis="benchmark_or_tender_cost",
            qualifier="50_percent_central_plus_30_percent_state_in_ner_hilly_states",
            conditions={"beneficiary_type": "individual_farmers", "geography": "north_eastern_states"},
            frequency="one_time_capital_subsidy",
        ),
        # 10. 20% Farmer share in NE, Hilly States & Island UTs
        _make_rule(
            rule_id="RULE_PMKUSUM_FARMER_SHARE_NER_20PCT",
            unit=u_tbl_r2,
            scheme="PM_KUSUM",
            rule_parameter="farmer_contribution_pct",
            maximum_rate=20.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="individual_farmers_special_states",
            entity_scope="individual_farmers_special_states",
            geography="north_eastern_states",
            basis="benchmark_or_tender_cost",
            qualifier="reduced_20_percent_farmer_share_in_ner_hilly_states",
            conditions={"beneficiary_type": "individual_farmers", "geography": "north_eastern_states"},
            frequency="one_time_capital_subsidy",
        ),
        # 11. 15 HP community/FPO cluster pump capacity ceiling
        _make_rule(
            rule_id="RULE_PMKUSUM_CLUSTER_PUMP_15HP",
            unit=u_comp_b_loan_ner,
            scheme="PM_KUSUM",
            rule_parameter="cluster_community_pump_capacity_hp",
            maximum_rate=15.0,
            minimum_value=None,
            allowed_values=[15.0],
            numeric_operator="le",
            unit_name="horsepower",
            crop_category="fpo_water_user_associations",
            entity_scope="fpo_water_user_associations",
            basis="community_cluster_pump_capacity",
            qualifier="up_to_15_hp_for_fpos_with_cfa_capped_at_7_5_hp",
            conditions={"beneficiary_type": "fpo_water_user_associations"},
        ),
        # 12. 10,000 MW Component-A national target
        _make_rule(
            rule_id="RULE_PMKUSUM_COMPA_TARGET_10000MW",
            unit=u_comp_a,
            scheme="PM_KUSUM",
            rule_parameter="component_a_national_target_mw",
            maximum_rate=10000.0,
            numeric_operator="eq",
            unit_name="megawatts",
            crop_category="component_a_solar_plants",
            entity_scope="component_a_solar_plants",
            basis="national_cumulative_decentralized_solar_capacity",
            qualifier="component_a_decentralized_grid_connected_plants",
        ),
        # 13. 500 kW minimum Component-A plant capacity
        _make_rule(
            rule_id="RULE_PMKUSUM_COMPA_MIN_500KW",
            unit=u_comp_a,
            scheme="PM_KUSUM",
            rule_parameter="component_a_min_plant_capacity_kw",
            maximum_rate=500.0,
            minimum_value=500.0,
            allowed_values=[500.0],
            numeric_operator="ge",
            unit_name="kilowatts",
            crop_category="component_a_solar_plants",
            entity_scope="component_a_solar_plants",
            basis="individual_solar_plant_capacity",
            qualifier="minimum_500_kw_capacity_under_component_a",
        ),
        # 14. 2 MW maximum Component-A plant capacity
        _make_rule(
            rule_id="RULE_PMKUSUM_COMPA_MAX_2MW",
            unit=u_comp_a,
            scheme="PM_KUSUM",
            rule_parameter="component_a_max_plant_capacity_mw",
            maximum_rate=2.0,
            minimum_value=0.5,
            allowed_values=[2.0],
            numeric_operator="le",
            unit_name="megawatts",
            crop_category="component_a_solar_plants",
            entity_scope="component_a_solar_plants",
            basis="individual_solar_plant_capacity",
            qualifier="500_kw_to_2_mw_plant_capacity_range",
        ),
        # 15. 5 km substation radius for Component-A plants
        _make_rule(
            rule_id="RULE_PMKUSUM_COMPA_RADIUS_5KM",
            unit=u_comp_a,
            scheme="PM_KUSUM",
            rule_parameter="component_a_substation_radius_km",
            maximum_rate=5.0,
            minimum_value=None,
            allowed_values=[5.0],
            numeric_operator="le",
            unit_name="kilometres",
            crop_category="component_a_solar_plants",
            entity_scope="component_a_solar_plants",
            basis="radius_from_distribution_substation",
            qualifier="within_5_km_radius_of_substation",
        ),
        # 16. Rs 0.40 per kWh DISCOM PBI rate
        _make_rule(
            rule_id="RULE_PMKUSUM_DISCOM_PBI_0_40_INR",
            unit=u_comp_a,
            scheme="PM_KUSUM",
            rule_parameter="discom_pbi_rate_per_kwh_inr",
            maximum_rate=0.40,
            minimum_value=None,
            allowed_values=[0.40],
            numeric_operator="le",
            unit_name="rupees",
            crop_category="discom_performance_based_incentive",
            entity_scope="discom_performance_based_incentive",
            basis="per_kwh_solar_power_purchased",
            qualifier="or_6_60_lakh_per_mw_per_year_whichever_is_less",
        ),
        # 17. Rs 6,60,000 per MW per year DISCOM PBI annual cap
        _make_rule(
            rule_id="RULE_PMKUSUM_DISCOM_PBI_CAP_660K",
            unit=u_comp_a,
            scheme="PM_KUSUM",
            rule_parameter="discom_pbi_annual_cap_per_mw_inr",
            maximum_rate=660000.0,
            minimum_value=None,
            allowed_values=[660000.0],
            numeric_operator="le",
            unit_name="rupees",
            crop_category="discom_performance_based_incentive",
            entity_scope="discom_performance_based_incentive",
            basis="per_mw_per_year",
            qualifier="maximum_annual_pbi_ceiling_per_mw",
        ),
        # 18. 5 years DISCOM PBI duration
        _make_rule(
            rule_id="RULE_PMKUSUM_DISCOM_PBI_5_YEARS",
            unit=u_comp_a,
            scheme="PM_KUSUM",
            rule_parameter="discom_pbi_duration_years",
            maximum_rate=5.0,
            numeric_operator="eq",
            unit_name="years",
            crop_category="discom_performance_based_incentive",
            entity_scope="discom_performance_based_incentive",
            basis="years_from_commercial_operation_date",
            qualifier="5_years_from_cod",
        ),
        # 19. 2x solar PV capacity multiplier under Component-C
        _make_rule(
            rule_id="RULE_PMKUSUM_COMPC_PV_MULTIPLIER_2X",
            unit=u_comp_c_cmc,
            scheme="PM_KUSUM",
            rule_parameter="component_c_solar_pv_multiplier",
            maximum_rate=2.0,
            minimum_value=None,
            allowed_values=[2.0],
            numeric_operator="le",
            unit_name="dimensionless",
            crop_category="component_c_grid_connected_pumps",
            entity_scope="component_c_grid_connected_pumps",
            basis="multiple_of_pump_capacity_in_hp",
            qualifier="solar_pv_kw_up_to_2_times_pump_hp",
        ),
        # 20. 5 years mandatory vendor CMC warranty
        _make_rule(
            rule_id="RULE_PMKUSUM_VENDOR_CMC_5_YEARS",
            unit=u_comp_c_cmc,
            scheme="PM_KUSUM",
            rule_parameter="mandatory_vendor_cmc_years",
            maximum_rate=5.0,
            minimum_value=5.0,
            allowed_values=[5.0],
            numeric_operator="ge",
            unit_name="years",
            crop_category="vendor_maintenance_warranty",
            entity_scope="vendor_maintenance_warranty",
            basis="comprehensive_maintenance_contract_duration",
            qualifier="mandatory_5_year_vendor_cmc",
        ),
    ]

    all_rules = extract_structured_rules_from_units("PM_KUSUM", units, curated_rules)
    return units, all_rules


def _build_pmmy_data() -> tuple[list[ExtractedEvidenceUnit], list[StructuredRuleRecord]]:
    doc_args = {
        "document_id": "DOC_PMMY_GUIDELINES_2023",
        "source_url": "https://www.mudra.org.in/guidelines.pdf",
        "document_title": "Pradhan Mantri Mudra Yojana (PMMY) Operational Guidelines",
        "document_version": "official_guidelines",
        "publication_date": "2023-01-01",
        "effective_from": "2015-04-08",
        "effective_to": None,
        "policy_era": "pmmy_current",
    }

    u_loans = _make_unit(
        evidence_id="EV_PMMY_LOAN_CHUNK_1",
        physical_pdf_page=2,
        printed_page="2",
        section="Clause 2.1",
        text=(
            "[MUDRA LOAN CATEGORIES] PMMY provides collateral-free institutional credit to non-corporate, non-farm "
            "small/micro enterprises. The loan products are categorized as: Shishu covering loans up to Rs 50000, "
            "Kishore covering loans above Rs 50000 and up to Rs 500000, and Tarun covering loans above Rs 500000 and up to Rs 1000000."
        ),
        **doc_args,
    )
    u_tarun_plus = _make_unit(
        evidence_id="EV_PMMY_TARUN_PLUS_CHUNK_1",
        physical_pdf_page=3,
        printed_page="3",
        section="Clause 2.2 (Tarun Plus Category)",
        text=(
            "[TARUN PLUS ENHANCED LOAN TIER] Under the Tarun Plus category of PMMY, micro-enterprise loans "
            "above Rs 1000000 and up to Rs 2000000 (20 lakh rupees) are extended exclusively to repeat "
            "entrepreneurs who have previously availed and successfully repaid a Tarun category loan."
        ),
        **doc_args,
    )
    u_tbl_r1 = _make_unit(
        evidence_id="EV_PMMY_TBL_TIERS_R1",
        physical_pdf_page=3,
        printed_page="3",
        section="Clause 2.3 (Table 1)",
        evidence_type="table_row",
        table_id="TBL_PMMY_LOAN_TIERS",
        row_id="TBL_PMMY_LOAN_TIERS_R1",
        headers=["Loan_Category", "Min_Loan_INR", "Max_Loan_INR", "Processing_Fee_Pct", "Margin_Money_Pct"],
        text="[Table: PMMY Loan Products] Loan_Category: Shishu | Min_Loan_INR: 0 | Max_Loan_INR: 50000 | Processing_Fee_Pct: 0% | Margin_Money_Pct: 0%",
        cells=["Shishu", "0", "50000", "0%", "0%"],
        **doc_args,
    )
    u_tbl_r2 = _make_unit(
        evidence_id="EV_PMMY_TBL_TIERS_R2",
        physical_pdf_page=3,
        printed_page="3",
        section="Clause 2.3 (Table 1)",
        evidence_type="table_row",
        table_id="TBL_PMMY_LOAN_TIERS",
        row_id="TBL_PMMY_LOAN_TIERS_R2",
        headers=["Loan_Category", "Min_Loan_INR", "Max_Loan_INR", "Processing_Fee_Pct", "Margin_Money_Pct"],
        text="[Table: PMMY Loan Products] Loan_Category: Kishore | Min_Loan_INR: 50000 | Max_Loan_INR: 500000 | Processing_Fee_Pct: As per bank norms | Margin_Money_Pct: 10%",
        cells=["Kishore", "50000", "500000", "As per bank norms", "10%"],
        **doc_args,
    )
    u_tbl_r3 = _make_unit(
        evidence_id="EV_PMMY_TBL_TIERS_R3",
        physical_pdf_page=3,
        printed_page="3",
        section="Clause 2.3 (Table 1)",
        evidence_type="table_row",
        table_id="TBL_PMMY_LOAN_TIERS",
        row_id="TBL_PMMY_LOAN_TIERS_R3",
        headers=["Loan_Category", "Min_Loan_INR", "Max_Loan_INR", "Processing_Fee_Pct", "Margin_Money_Pct"],
        text="[Table: PMMY Loan Products] Loan_Category: Tarun | Min_Loan_INR: 500000 | Max_Loan_INR: 1000000 | Processing_Fee_Pct: As per bank norms | Margin_Money_Pct: 10%",
        cells=["Tarun", "500000", "1000000", "As per bank norms", "10%"],
        **doc_args,
    )
    u_terms_subvention = _make_unit(
        evidence_id="EV_PMMY_TERMS_SUBVENTION_CHUNK_1",
        physical_pdf_page=4,
        printed_page="4",
        section="Clauses 3.1-3.3",
        text=(
            "[COLLATERAL, PROCESSING FEE, MARGIN MONEY AND SHISHU INTEREST SUBVENTION] All loans sanctioned "
            "under PMMY require 0 percent collateral security from borrowers. For Shishu loans up to Rs 50000, "
            "banks charge 0 percent upfront processing fee and require 0 percent promoter margin money, whereas "
            "Kishore and Tarun loans require a minimum promoter margin contribution of 10 percent. Eligible "
            "Shishu borrowers receive a 2 percent per annum interest subvention for a period of 12 months "
            "on prompt repayment."
        ),
        **doc_args,
    )
    u_cgfmu_tenure = _make_unit(
        evidence_id="EV_PMMY_CGFMU_TENURE_AGE_CHUNK_1",
        physical_pdf_page=5,
        printed_page="5",
        section="Clauses 4.1-4.2 & 5.1-5.2",
        text=(
            "[CGFMU CREDIT GUARANTEE, SHISHU CORPUS EARMARKING, TENURE AND AGE NORMS] Under the Credit "
            "Guarantee Fund for Micro Units (CGFMU), portfolio guarantee cover is provided for up to "
            "75 percent of the amount in default, after the first 3 percent first-loss default of the "
            "crystallized portfolio is borne by the lending institution. At least 60 percent of the total "
            "PMMY credit corpus is earmarked for Shishu category units. Standard MUDRA term loan repayment "
            "tenure is up to 5 years (extendable up to 7 years based on cash flow). Individual borrowers "
            "must be at least 18 years of age and not more than 65 years of age."
        ),
        **doc_args,
    )

    units = [
        u_loans,
        u_tarun_plus,
        u_tbl_r1,
        u_tbl_r2,
        u_tbl_r3,
        u_terms_subvention,
        u_cgfmu_tenure,
    ]

    curated_rules = [
        # 1. Shishu loan cap: Rs 50,000
        _make_rule(
            rule_id="RULE_PMMY_SHISHU_50K",
            unit=u_loans,
            scheme="PMMY",
            rule_parameter="shishu_loan_cap_inr",
            maximum_rate=50000.0,
            minimum_value=None,
            allowed_values=[50000.0],
            numeric_operator="le",
            unit_name="rupees",
            crop_category="shishu_borrowers",
            entity_scope="shishu_borrowers",
            geography="all_india",
            basis="per_enterprise_loan",
            qualifier="shishu_category",
            requires_qualifier_for_unconditional_claim=True,
            conditions={"loan_category": "shishu", "beneficiary_type": "shishu_borrowers"},
            frequency="one_time_credit",
        ),
        # 2. Kishore loan cap: Rs 5,00,000 (above Rs 50,000)
        _make_rule(
            rule_id="RULE_PMMY_KISHORE_500K",
            unit=u_loans,
            scheme="PMMY",
            rule_parameter="kishore_loan_cap_inr",
            maximum_rate=500000.0,
            minimum_value=50000.0,
            allowed_values=[500000.0],
            numeric_operator="le",
            unit_name="rupees",
            crop_category="kishore_borrowers",
            entity_scope="kishore_borrowers",
            geography="all_india",
            basis="per_enterprise_loan",
            qualifier="kishore_category_above_50000_up_to_500000",
            requires_qualifier_for_unconditional_claim=True,
            conditions={"loan_category": "kishore", "beneficiary_type": "kishore_borrowers"},
            frequency="one_time_credit",
        ),
        # 3. Kishore loan lower bound: Rs 50,000
        _make_rule(
            rule_id="RULE_PMMY_KISHORE_MIN_50K",
            unit=u_tbl_r2,
            scheme="PMMY",
            rule_parameter="kishore_loan_min_inr",
            maximum_rate=50000.0,
            minimum_value=50000.0,
            allowed_values=[50000.0],
            numeric_operator="gt",
            unit_name="rupees",
            crop_category="kishore_borrowers",
            entity_scope="kishore_borrowers",
            basis="per_enterprise_loan",
            qualifier="loans_above_50000_up_to_500000",
            conditions={"loan_category": "kishore", "beneficiary_type": "kishore_borrowers"},
            frequency="one_time_credit",
        ),
        # 4. Tarun loan cap: Rs 10,00,000 (above Rs 5,00,000)
        _make_rule(
            rule_id="RULE_PMMY_TARUN_1000K",
            unit=u_loans,
            scheme="PMMY",
            rule_parameter="tarun_loan_cap_inr",
            maximum_rate=1000000.0,
            minimum_value=500000.0,
            allowed_values=[1000000.0],
            numeric_operator="le",
            unit_name="rupees",
            crop_category="tarun_borrowers",
            entity_scope="tarun_borrowers",
            geography="all_india",
            basis="per_enterprise_loan",
            qualifier="tarun_category_above_500000_up_to_1000000",
            requires_qualifier_for_unconditional_claim=True,
            conditions={"loan_category": "tarun", "beneficiary_type": "tarun_borrowers"},
            frequency="one_time_credit",
        ),
        # 5. Tarun loan lower bound: Rs 5,00,000
        _make_rule(
            rule_id="RULE_PMMY_TARUN_MIN_500K",
            unit=u_tbl_r3,
            scheme="PMMY",
            rule_parameter="tarun_loan_min_inr",
            maximum_rate=500000.0,
            minimum_value=500000.0,
            allowed_values=[500000.0],
            numeric_operator="gt",
            unit_name="rupees",
            crop_category="tarun_borrowers",
            entity_scope="tarun_borrowers",
            basis="per_enterprise_loan",
            qualifier="loans_above_500000_up_to_1000000",
            conditions={"loan_category": "tarun", "beneficiary_type": "tarun_borrowers"},
            frequency="one_time_credit",
        ),
        # 6. Tarun Plus loan cap: Rs 20,00,000 (for repeat Tarun borrowers)
        _make_rule(
            rule_id="RULE_PMMY_TARUN_PLUS_2000K",
            unit=u_tarun_plus,
            scheme="PMMY",
            rule_parameter="tarun_plus_loan_cap_inr",
            maximum_rate=2000000.0,
            minimum_value=1000000.0,
            allowed_values=[2000000.0],
            numeric_operator="le",
            unit_name="rupees",
            crop_category="tarun_plus_repeat_borrowers",
            entity_scope="tarun_plus_repeat_borrowers",
            basis="per_enterprise_loan",
            qualifier="only_for_repeat_borrowers_who_repaid_previous_tarun_loan",
            requires_qualifier_for_unconditional_claim=True,
            conditions={"loan_category": "tarun_plus", "beneficiary_type": "tarun_plus_repeat_borrowers"},
            frequency="one_time_credit",
        ),
        # 7. 0% collateral security requirement
        _make_rule(
            rule_id="RULE_PMMY_ZERO_COLLATERAL",
            unit=u_terms_subvention,
            scheme="PMMY",
            rule_parameter="collateral_security_requirement_pct",
            maximum_rate=0.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="all_mudra_borrowers",
            entity_scope="all_mudra_borrowers",
            basis="loan_amount",
            qualifier="collateral_free_institutional_credit",
        ),
        # 8. 0% processing fee for Shishu loans
        _make_rule(
            rule_id="RULE_PMMY_SHISHU_ZERO_PROC_FEE",
            unit=u_tbl_r1,
            scheme="PMMY",
            rule_parameter="shishu_processing_fee_pct",
            maximum_rate=0.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="shishu_borrowers",
            entity_scope="shishu_borrowers",
            basis="loan_amount",
            qualifier="nil_processing_fee_for_shishu_loans",
            conditions={"loan_category": "shishu"},
        ),
        # 9. 0% margin money for Shishu loans
        _make_rule(
            rule_id="RULE_PMMY_SHISHU_ZERO_MARGIN",
            unit=u_tbl_r1,
            scheme="PMMY",
            rule_parameter="shishu_margin_money_pct",
            maximum_rate=0.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="shishu_borrowers",
            entity_scope="shishu_borrowers",
            basis="project_cost",
            qualifier="nil_margin_money_for_shishu_loans",
            conditions={"loan_category": "shishu"},
        ),
        # 10. 10% minimum margin money for Kishore & Tarun loans
        _make_rule(
            rule_id="RULE_PMMY_KISHORE_TARUN_MARGIN_10PCT",
            unit=u_terms_subvention,
            scheme="PMMY",
            rule_parameter="kishore_tarun_margin_money_min_pct",
            maximum_rate=10.0,
            minimum_value=10.0,
            allowed_values=[10.0, 15.0, 20.0, 25.0],
            numeric_operator="ge",
            unit_name="percent",
            crop_category="kishore_and_tarun_borrowers",
            entity_scope="kishore_and_tarun_borrowers",
            basis="project_cost",
            qualifier="promoter_margin_contribution_for_kishore_and_tarun",
        ),
        # 11. 2% interest subvention on Shishu loans
        _make_rule(
            rule_id="RULE_PMMY_SHISHU_SUBVENTION_2PCT",
            unit=u_terms_subvention,
            scheme="PMMY",
            rule_parameter="shishu_interest_subvention_pct",
            maximum_rate=2.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="shishu_prompt_repayment_borrowers",
            entity_scope="shishu_prompt_repayment_borrowers",
            basis="per_annum_on_shishu_loans",
            qualifier="for_12_months_on_prompt_repayment",
            conditions={"loan_category": "shishu"},
        ),
        # 12. 12 months Shishu interest subvention period
        _make_rule(
            rule_id="RULE_PMMY_SHISHU_SUBVENTION_12_MONTHS",
            unit=u_terms_subvention,
            scheme="PMMY",
            rule_parameter="shishu_interest_subvention_period_months",
            maximum_rate=12.0,
            numeric_operator="eq",
            unit_name="months",
            crop_category="shishu_prompt_repayment_borrowers",
            entity_scope="shishu_prompt_repayment_borrowers",
            basis="interest_subvention_duration",
            qualifier="12_months_interest_subvention_window",
            conditions={"loan_category": "shishu"},
        ),
        # 13. 75% CGFMU credit guarantee cover
        _make_rule(
            rule_id="RULE_PMMY_CGFMU_GUARANTEE_75PCT",
            unit=u_cgfmu_tenure,
            scheme="PMMY",
            rule_parameter="cgfmu_guarantee_cover_pct",
            maximum_rate=75.0,
            minimum_value=None,
            allowed_values=[75.0],
            numeric_operator="le",
            unit_name="percent",
            crop_category="cgfmu_portfolio_guarantee",
            entity_scope="cgfmu_portfolio_guarantee",
            basis="amount_in_default",
            qualifier="up_to_75_percent_of_default_amount_under_cgfmu",
        ),
        # 14. 3% CGFMU first-loss default borne by lender
        _make_rule(
            rule_id="RULE_PMMY_CGFMU_FIRST_LOSS_3PCT",
            unit=u_cgfmu_tenure,
            scheme="PMMY",
            rule_parameter="cgfmu_first_loss_default_borne_by_lender_pct",
            maximum_rate=3.0,
            numeric_operator="eq",
            unit_name="percent",
            crop_category="cgfmu_portfolio_guarantee",
            entity_scope="cgfmu_portfolio_guarantee",
            basis="crystallized_portfolio_amount",
            qualifier="first_3_percent_borne_by_member_lending_institution",
        ),
        # 15. 60% minimum PMMY corpus earmarked for Shishu
        _make_rule(
            rule_id="RULE_PMMY_SHISHU_CORPUS_SHARE_60PCT",
            unit=u_cgfmu_tenure,
            scheme="PMMY",
            rule_parameter="shishu_corpus_earmarking_minimum_pct",
            maximum_rate=60.0,
            minimum_value=60.0,
            allowed_values=[60.0],
            numeric_operator="ge",
            unit_name="percent",
            crop_category="shishu_borrowers",
            entity_scope="shishu_borrowers",
            basis="total_pmmy_credit_corpus",
            qualifier="at_least_60_percent_earmarked_for_shishu",
            conditions={"loan_category": "shishu"},
        ),
        # 16. 5 years standard maximum repayment tenure
        _make_rule(
            rule_id="RULE_PMMY_TENURE_5_YEARS",
            unit=u_cgfmu_tenure,
            scheme="PMMY",
            rule_parameter="maximum_repayment_tenure_years",
            maximum_rate=5.0,
            minimum_value=None,
            allowed_values=[5.0, 7.0],
            numeric_operator="le",
            unit_name="years",
            crop_category="term_loan_repayment_tenure",
            entity_scope="term_loan_repayment_tenure",
            basis="loan_repayment_period",
            qualifier="up_to_5_years_standard_extendable_to_7_years",
        ),
        # 17. 7 years extended maximum repayment tenure
        _make_rule(
            rule_id="RULE_PMMY_EXTENDED_TENURE_7_YEARS",
            unit=u_cgfmu_tenure,
            scheme="PMMY",
            rule_parameter="extended_repayment_tenure_years",
            maximum_rate=7.0,
            minimum_value=None,
            allowed_values=[7.0],
            numeric_operator="le",
            unit_name="years",
            crop_category="extended_term_loan_tenure",
            entity_scope="extended_term_loan_tenure",
            basis="extended_loan_repayment_period",
            qualifier="extendable_up_to_7_years_based_on_cash_flow",
        ),
        # 18. 18 years minimum borrower age
        _make_rule(
            rule_id="RULE_PMMY_MIN_AGE_18_YEARS",
            unit=u_cgfmu_tenure,
            scheme="PMMY",
            rule_parameter="minimum_borrower_age_years",
            maximum_rate=18.0,
            minimum_value=18.0,
            allowed_values=[18.0],
            numeric_operator="ge",
            unit_name="years",
            crop_category="individual_mudra_borrowers",
            entity_scope="individual_mudra_borrowers",
            basis="borrower_age_years",
            qualifier="minimum_18_years_of_age",
        ),
        # 19. 65 years maximum borrower age
        _make_rule(
            rule_id="RULE_PMMY_MAX_AGE_65_YEARS",
            unit=u_cgfmu_tenure,
            scheme="PMMY",
            rule_parameter="maximum_borrower_age_years",
            maximum_rate=65.0,
            minimum_value=18.0,
            allowed_values=[65.0],
            numeric_operator="le",
            unit_name="years",
            crop_category="individual_mudra_borrowers",
            entity_scope="individual_mudra_borrowers",
            basis="borrower_age_years",
            qualifier="maximum_65_years_of_age",
        ),
    ]

    all_rules = extract_structured_rules_from_units("PMMY", units, curated_rules)
    return units, all_rules


def get_flagship_scheme_data(scheme_key: str) -> tuple[list[ExtractedEvidenceUnit], list[StructuredRuleRecord]]:
    """
    Return the official extracted evidence units and canonical verified structured rules
    for the requested flagship government scheme.
    """
    key = scheme_key.upper().replace("-", "_")
    if key in ("MGNREGA", "MGNREGS", "NREGA"):
        return _build_mgnrega_data()
    if key in ("PM_JAY", "PMJAY", "AYUSHMAN_BHARAT"):
        return _build_pmjay_data()
    if key in ("PMAY_G", "PMAYG", "PMAY"):
        return _build_pmayg_data()
    if key in ("PM_KUSUM", "PMKUSUM", "KUSUM"):
        return _build_pmkusum_data()
    if key in ("PMMY", "MUDRA"):
        return _build_pmmy_data()
    return [], []


def build_flagship_scheme_evidence_store(scheme_key: str, project_root: Path | None = None) -> EvidenceStore:
    """Build a validated EvidenceStore for any of the flagship government schemes."""
    units, rules = get_flagship_scheme_data(scheme_key)
    store = EvidenceStore()
    for u in units:
        store.register_evidence_unit(u)
    for r in rules:
        store.add_structured_rule(r, strict=False)
    return store
