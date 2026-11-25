"""MGNREGA (Mahatma Gandhi National Rural Employment Guarantee Act) scheme adapter."""

from __future__ import annotations

from typing import Any

from fieldguard.schemes.base import ContextValidationResult, ParameterSpec, SchemeDefinition


class MGNREGAScheme(SchemeDefinition):
    """Scheme adapter for MGNREGA / MGNREGS."""

    @property
    def scheme_id(self) -> str:
        return "MGNREGA"

    @property
    def full_name(self) -> str:
        return "Mahatma Gandhi National Rural Employment Guarantee Act (MGNREGA)"

    @property
    def aliases(self) -> list[str]:
        return ["mgnrega", "mgnregs", "nrega", "rural_employment_guarantee", "100_days_work"]

    @property
    def parameters(self) -> list[ParameterSpec]:
        return [
            ParameterSpec(
                name="guaranteed_employment_days",
                description="Statutory minimum guaranteed days of unskilled wage employment per rural household per financial year (100 days standard; 150 days for FRA/drought/calamity areas)",
                canonical_unit="days",
                required_context_fields=["beneficiary_type"],
                optional_context_fields=["geography", "frequency"],
            ),
            ParameterSpec(
                name="additional_employment_days_fra_drought",
                description="Additional days of employment above 100 days for FRA beneficiaries and notified drought/calamity areas (50 days)",
                canonical_unit="days",
                required_context_fields=[],
                optional_context_fields=["beneficiary_type", "geography"],
            ),
            ParameterSpec(
                name="work_allocation_timeline_days",
                description="Maximum days from application within which employment must be provided before unemployment allowance triggers (15 days)",
                canonical_unit="days",
                required_context_fields=[],
                optional_context_fields=["beneficiary_type"],
            ),
            ParameterSpec(
                name="job_card_issuance_timeline_days",
                description="Maximum days from registration application within which Gram Panchayat must issue a Job Card (15 days)",
                canonical_unit="days",
                required_context_fields=[],
                optional_context_fields=["beneficiary_type"],
            ),
            ParameterSpec(
                name="unemployment_allowance_rate_first_30_days",
                description="Minimum unemployment allowance rate as percentage of daily wage rate for the first 30 days (25%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["period", "beneficiary_type"],
            ),
            ParameterSpec(
                name="unemployment_allowance_rate_after_30_days",
                description="Minimum unemployment allowance rate as percentage of daily wage rate after the first 30 days (50%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["period", "beneficiary_type"],
            ),
            ParameterSpec(
                name="unemployment_allowance_initial_period_days",
                description="Initial duration in days at the 25% unemployment allowance tier before stepping up to 50% (30 days)",
                canonical_unit="days",
                required_context_fields=[],
                optional_context_fields=["period"],
            ),
            ParameterSpec(
                name="wage_payment_timeline_days",
                description="Maximum days from closure of muster roll within which wages must be disbursed (15 days)",
                canonical_unit="days",
                required_context_fields=[],
                optional_context_fields=["beneficiary_type"],
            ),
            ParameterSpec(
                name="delayed_wage_compensation_rate_per_day",
                description="Daily compensation rate as percentage of unpaid wages for delays beyond 15 days after muster roll closure (0.05% per day)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["frequency"],
            ),
            ParameterSpec(
                name="women_participation_minimum_share_pct",
                description="Statutory minimum share of women among registered beneficiaries allocated work (33.33% / one-third)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["beneficiary_type"],
            ),
            ParameterSpec(
                name="work_radius_limit_km",
                description="Radius in kilometres from village residence within which work must ordinarily be provided without extra wage allowance (5 km)",
                canonical_unit="kilometres",
                required_context_fields=[],
                optional_context_fields=["beneficiary_type"],
            ),
            ParameterSpec(
                name="distance_commuting_extra_wage_pct",
                description="Extra wage allowance percentage payable when work is provided beyond 5 km radius of the village (10%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["distance"],
            ),
            ParameterSpec(
                name="worksite_creche_children_threshold",
                description="Minimum number of children below 6 years at a worksite triggering mandatory creche facility (5 children)",
                canonical_unit="children",
                required_context_fields=[],
                optional_context_fields=["beneficiary_type"],
            ),
            ParameterSpec(
                name="worksite_creche_child_age_limit_years",
                description="Upper age limit in years of children counted for worksite creche provision (below 6 years)",
                canonical_unit="years",
                required_context_fields=[],
                optional_context_fields=["beneficiary_type"],
            ),
            ParameterSpec(
                name="ex_gratia_death_disability_compensation_inr",
                description="Statutory ex-gratia compensation for accidental death or permanent disability at worksite (Rs 25,000)",
                canonical_unit="rupees",
                required_context_fields=[],
                optional_context_fields=["beneficiary_type"],
            ),
            ParameterSpec(
                name="wage_material_ratio_wage_share_pct",
                description="Minimum percentage of project expenditure required to be spent on unskilled manual wages (60%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="wage_material_ratio_material_cap_pct",
                description="Maximum percentage of project expenditure permitted on materials and skilled/semi-skilled wages (40%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="central_wage_funding_share_pct",
                description="Central Government funding share for unskilled manual wages under MGNREGA (100%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="central_material_funding_share_pct",
                description="Central Government funding share for material and skilled/semi-skilled wages (75%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="state_material_funding_share_pct",
                description="State Government funding share for material and skilled/semi-skilled wages (25%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="administrative_expense_ceiling_pct",
                description="Maximum percentage of annual scheme expenditure permissible towards administrative expenses (6%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="social_audit_frequency_months",
                description="Maximum interval in months between mandatory Gram Sabha social audits of MGNREGA works (6 months)",
                canonical_unit="months",
                required_context_fields=[],
                optional_context_fields=[],
            ),
        ]

    def validate_claim_context(
        self,
        rule_parameter: str | None,
        context: dict[str, Any],
        enable_switches: dict[str, bool] | None = None,
    ) -> ContextValidationResult:
        if not rule_parameter:
            return ContextValidationResult(is_valid=False, missing_fields=["rule_parameter"])
        return ContextValidationResult(is_valid=True)

    def match_conditions(
        self,
        claimed_context: dict[str, Any],
        rule_context: dict[str, Any],
        rule_parameter: str | None = None,
        enable_switches: dict[str, bool] | None = None,
    ) -> tuple[bool, list[str]]:
        mismatches: list[str] = []
        c_ben = claimed_context.get("beneficiary_type")
        r_ben = rule_context.get("beneficiary_type")
        c_geog = claimed_context.get("geography")
        r_geog = rule_context.get("geography")
        c_period = claimed_context.get("period")
        r_period = rule_context.get("period")

        if c_ben == "urban_household" and r_ben in (
            "rural_household",
            "fra_and_drought_notified_households",
            "women_workers",
            "all",
            None,
        ):
            mismatches.append("geography_eligibility_mismatch: claimed='urban_household' vs rule='rural_household'")

        if c_ben == "skilled_or_contractor_work":
            mismatches.append(
                "work_category_mismatch: claimed='skilled_or_contractor_work' vs rule='unskilled_manual_work'"
            )

        # Distinguish standard 100-day rural household guarantee vs 150-day FRA/drought guarantee
        if rule_parameter == "guaranteed_employment_days":
            if (
                c_ben == "fra_and_drought_notified_households"
                or c_geog == "drought_or_calamity_notified_areas"
            ) and r_ben == "rural_household" and r_geog == "all_india":
                mismatches.append(
                    "beneficiary_scope_mismatch: claimed='fra_and_drought_notified_households' vs rule='rural_household'"
                )
            elif (
                c_ben == "rural_household"
                and c_geog != "drought_or_calamity_notified_areas"
                and (
                    r_ben == "fra_and_drought_notified_households"
                    or r_geog == "drought_or_calamity_notified_areas"
                )
            ):
                mismatches.append(
                    "geography_mismatch: claimed='all_india_standard_rural' vs rule='drought_or_calamity_notified_areas'"
                )

        # Distinguish first 30 days (25%) vs after 30 days (50%) unemployment allowance
        if c_period and r_period and c_period != r_period:
            mismatches.append(f"period_mismatch: claimed='{c_period}' vs rule='{r_period}'")
        if c_period == "first_30_days" and rule_parameter == "unemployment_allowance_rate_after_30_days":
            mismatches.append("period_mismatch: claimed='first_30_days' vs rule='after_30_days'")
        if c_period == "after_30_days" and rule_parameter == "unemployment_allowance_rate_first_30_days":
            mismatches.append("period_mismatch: claimed='after_30_days' vs rule='first_30_days'")

        # Distinguish within 5 km vs beyond 5 km
        c_dist = claimed_context.get("distance")
        if c_dist == "within_5_km" and rule_parameter == "distance_commuting_extra_wage_pct":
            mismatches.append("distance_condition_mismatch: extra wage applies only beyond 5 km radius")

        return len(mismatches) == 0, mismatches

