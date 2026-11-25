"""PM-JAY (Ayushman Bharat Pradhan Mantri Jan Arogya Yojana) scheme adapter."""

from __future__ import annotations

from typing import Any

from fieldguard.schemes.base import ContextValidationResult, ParameterSpec, SchemeDefinition


class PMJAYScheme(SchemeDefinition):
    """Scheme adapter for Ayushman Bharat PM-JAY."""

    @property
    def scheme_id(self) -> str:
        return "PM_JAY"

    @property
    def full_name(self) -> str:
        return "Ayushman Bharat — Pradhan Mantri Jan Arogya Yojana (PM-JAY)"

    @property
    def aliases(self) -> list[str]:
        return ["pm_jay", "pmjay", "pm-jay", "ayushman_bharat", "jan_arogya_yojana"]

    @property
    def parameters(self) -> list[ParameterSpec]:
        return [
            ParameterSpec(
                name="annual_health_cover_inr",
                description="Maximum annual health insurance cover per family per year for secondary and tertiary hospitalisation (Rs 5,00,000)",
                canonical_unit="rupees",
                required_context_fields=["beneficiary_type"],
                optional_context_fields=["frequency", "care_level"],
            ),
            ParameterSpec(
                name="cashless_benefit_percentage",
                description="Percentage of secondary and tertiary hospitalisation covered cashless at empanelled hospitals (100%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["beneficiary_type"],
            ),
            ParameterSpec(
                name="pre_existing_disease_waiting_period_days",
                description="Waiting period in days for coverage of pre-existing medical conditions under PM-JAY (0 days)",
                canonical_unit="days",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="pre_hospitalisation_coverage_days",
                description="Number of days of pre-hospitalisation diagnostics and medication expenses covered prior to admission (3 days)",
                canonical_unit="days",
                required_context_fields=[],
                optional_context_fields=["hospitalisation_phase"],
            ),
            ParameterSpec(
                name="post_hospitalisation_coverage_days",
                description="Number of days of post-hospitalisation follow-up and medication expenses covered after discharge (15 days)",
                canonical_unit="days",
                required_context_fields=[],
                optional_context_fields=["hospitalisation_phase"],
            ),
            ParameterSpec(
                name="health_benefit_packages_count",
                description="Total number of medical and surgical procedures covered in the National Health Benefit Package master schedule (1949 packages)",
                canonical_unit="packages",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="senior_citizen_age_eligibility_years",
                description="Minimum age in years for universal senior citizen health coverage under Ayushman Vay Vandana (70 years)",
                canonical_unit="years",
                required_context_fields=[],
                optional_context_fields=["beneficiary_type"],
            ),
            ParameterSpec(
                name="senior_citizen_topup_cover_inr",
                description="Dedicated annual health cover / top-up for families with senior citizens aged 70 years and above (Rs 5,00,000)",
                canonical_unit="rupees",
                required_context_fields=[],
                optional_context_fields=["beneficiary_type"],
            ),
            ParameterSpec(
                name="central_funding_share_pct",
                description="Central Government premium funding share (60% in general states, 90% in NE/Himalayan states, 100% in UTs without legislature)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["geography"],
            ),
            ParameterSpec(
                name="state_funding_share_pct",
                description="State Government premium funding share (40% in general states, 10% in NE/Himalayan states)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["geography"],
            ),
            ParameterSpec(
                name="claim_settlement_turnaround_days",
                description="Maximum turnaround time in days for settling intra-state hospital claims (15 days)",
                canonical_unit="days",
                required_context_fields=[],
                optional_context_fields=["claim_scope"],
            ),
            ParameterSpec(
                name="claim_settlement_turnaround_days_portability",
                description="Maximum turnaround time in days for settling inter-state portability hospital claims (30 days)",
                canonical_unit="days",
                required_context_fields=[],
                optional_context_fields=["claim_scope"],
            ),
            ParameterSpec(
                name="delayed_claim_penal_interest_weekly_pct",
                description="Penal interest rate per week payable on delayed hospital claim settlement beyond turnaround time (1% per week)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["frequency"],
            ),
            ParameterSpec(
                name="pre_authorization_turnaround_hours",
                description="Maximum turnaround time in hours for deciding hospital pre-authorization requests (6 hours)",
                canonical_unit="hours",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="pre_authorization_auto_approval_hours",
                description="Hours after which an undecided pre-authorization request is deemed auto-approved (24 hours)",
                canonical_unit="hours",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="minimum_hospital_beds_general_empanelment",
                description="Minimum inpatient bed capacity required for general private hospital empanelment (10 beds)",
                canonical_unit="beds",
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
        c_freq = claimed_context.get("frequency")
        if c_freq == "monthly" and rule_parameter in ("annual_health_cover_inr", "senior_citizen_topup_cover_inr"):
            mismatches.append("frequency_mismatch: claimed='monthly' vs rule='annual'")

        c_scope = claimed_context.get("beneficiary_scope")
        if c_scope == "per_individual" and rule_parameter == "annual_health_cover_inr":
            mismatches.append("scope_mismatch: claimed='per_individual' vs rule='per_family'")

        c_care = claimed_context.get("care_level")
        if c_care == "outpatient_opd_only":
            mismatches.append(
                "care_level_mismatch: claimed='outpatient_opd_only' vs rule='secondary_and_tertiary_hospitalisation'"
            )

        c_phase = claimed_context.get("hospitalisation_phase")
        if c_phase == "pre_hospitalisation" and rule_parameter == "post_hospitalisation_coverage_days":
            mismatches.append("phase_mismatch: claimed='pre_hospitalisation' vs rule='post_hospitalisation'")
        if c_phase == "post_hospitalisation" and rule_parameter == "pre_hospitalisation_coverage_days":
            mismatches.append("phase_mismatch: claimed='post_hospitalisation' vs rule='pre_hospitalisation'")

        def _norm_geo(g: str | None) -> str | None:
            if g in ("north_eastern_states", "hilly_areas", "hilly_and_difficult_areas", "north_eastern_and_himalayan_states"):
                return "north_eastern_and_himalayan_states"
            if g in ("general_states", "plains_areas"):
                return "general_states"
            if g in ("union_territories", "union_territories_without_legislature"):
                return "union_territories_without_legislature"
            return g

        c_geog = _norm_geo(claimed_context.get("geography"))
        r_geog = _norm_geo(rule_context.get("geography"))
        if rule_parameter in ("central_funding_share_pct", "state_funding_share_pct") and c_geog in (None, "all_india"):
            c_geog = "general_states"
        if (
            c_geog
            and r_geog
            and c_geog not in ("all_india",)
            and r_geog not in ("all_india",)
            and c_geog != r_geog
        ):
            mismatches.append(f"geography_mismatch: claimed='{claimed_context.get('geography')}' vs rule='{rule_context.get('geography')}'")

        c_claim_scope = claimed_context.get("claim_scope")
        r_claim_scope = rule_context.get("claim_scope")
        if c_claim_scope and r_claim_scope and c_claim_scope != r_claim_scope:
            mismatches.append(f"claim_scope_mismatch: claimed='{c_claim_scope}' vs rule='{r_claim_scope}'")
        if c_claim_scope == "intrastate" and rule_parameter == "claim_settlement_turnaround_days_portability":
            mismatches.append("claim_scope_mismatch: claimed='intrastate' vs rule='portability'")
        if c_claim_scope == "portability" and rule_parameter == "claim_settlement_turnaround_days":
            mismatches.append("claim_scope_mismatch: claimed='portability' vs rule='intrastate'")

        return len(mismatches) == 0, mismatches

