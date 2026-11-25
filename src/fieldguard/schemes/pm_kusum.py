"""PM-KUSUM (Pradhan Mantri Kisan Urja Suraksha evam Utthaan Mahabhiyan) scheme adapter."""

from __future__ import annotations

from typing import Any

from fieldguard.schemes.base import ContextValidationResult, ParameterSpec, SchemeDefinition


class PMKusumScheme(SchemeDefinition):
    """Scheme adapter for PM-KUSUM."""

    @property
    def scheme_id(self) -> str:
        return "PM_KUSUM"

    @property
    def full_name(self) -> str:
        return "Pradhan Mantri Kisan Urja Suraksha evam Utthaan Mahabhiyan (PM-KUSUM)"

    @property
    def aliases(self) -> list[str]:
        return ["pm_kusum", "pmkusum", "pm-kusum", "kusum", "solar_pump_scheme"]

    @property
    def parameters(self) -> list[ParameterSpec]:
        return [
            ParameterSpec(
                name="central_subsidy_pct",
                description="Central Financial Assistance (CFA) percentage for solar pumps (30% in general states; 50% in NE/Hilly/Island states)",
                canonical_unit="percent",
                required_context_fields=["beneficiary_type"],
                optional_context_fields=["geography", "component"],
            ),
            ParameterSpec(
                name="state_subsidy_pct",
                description="Minimum State Government subsidy percentage for solar pumps (30%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["geography", "beneficiary_type"],
            ),
            ParameterSpec(
                name="total_subsidy_pct",
                description="Combined Central and State Government subsidy percentage (60% in general states; 80% in NE/Hilly/Island states)",
                canonical_unit="percent",
                required_context_fields=["beneficiary_type"],
                optional_context_fields=["geography"],
            ),
            ParameterSpec(
                name="farmer_contribution_pct",
                description="Remaining percentage of cost borne by the farmer (40% in general states; 20% in NE/Hilly/Island states)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["geography", "beneficiary_type"],
            ),
            ParameterSpec(
                name="farmer_bank_loan_share_pct",
                description="Maximum percentage of pump cost financeable via bank loan within farmer share (30%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="farmer_upfront_margin_pct",
                description="Upfront farmer down-payment percentage when availing 30% bank loan and 60% subsidy (10%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="max_pump_capacity_hp",
                description="Maximum individual solar pump capacity in horsepower eligible for CFA under Component-B/C (7.5 HP)",
                canonical_unit="horsepower",
                required_context_fields=[],
                optional_context_fields=["beneficiary_type"],
            ),
            ParameterSpec(
                name="cluster_community_pump_capacity_hp",
                description="Maximum solar pump capacity in HP permitted for FPOs/WUAs/cluster irrigation in dark zones (15 HP)",
                canonical_unit="horsepower",
                required_context_fields=[],
                optional_context_fields=["beneficiary_type"],
            ),
            ParameterSpec(
                name="component_a_national_target_mw",
                description="National cumulative capacity target in MW for decentralized solar power plants under Component-A (10,000 MW)",
                canonical_unit="megawatts",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="component_a_min_plant_capacity_kw",
                description="Minimum individual solar power plant capacity in kW under Component-A (500 kW)",
                canonical_unit="kilowatts",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="component_a_max_plant_capacity_mw",
                description="Maximum individual solar power plant capacity in MW under Component-A (2 MW)",
                canonical_unit="megawatts",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="component_a_substation_radius_km",
                description="Maximum distance radius in km from distribution substation for Component-A plants (5 km)",
                canonical_unit="kilometres",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="discom_pbi_rate_per_kwh_inr",
                description="DISCOM Performance Based Incentive rate per kWh under Component-A (Rs 0.40 per kWh)",
                canonical_unit="rupees",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="discom_pbi_annual_cap_per_mw_inr",
                description="Maximum annual DISCOM Performance Based Incentive per MW per year under Component-A (Rs 6,60,000)",
                canonical_unit="rupees",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="discom_pbi_duration_years",
                description="Duration in years for which DISCOM Performance Based Incentive is payable from COD (5 years)",
                canonical_unit="years",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="component_c_solar_pv_multiplier",
                description="Maximum ratio of solar PV capacity (kW) to pump capacity (HP) under Component-C (2 times)",
                canonical_unit="dimensionless",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="mandatory_vendor_cmc_years",
                description="Minimum duration in years of mandatory vendor Comprehensive Maintenance Contract (5 years)",
                canonical_unit="years",
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

        if c_ben == "commercial_industrial_corporations":
            mismatches.append(
                f"beneficiary_mismatch: claimed='{c_ben}' vs rule='{r_ben or 'individual_farmers'}'"
            )

        c_geo = claimed_context.get("geography")
        r_geo = rule_context.get("geography")

        # Normalize hilly_and_difficult_areas -> north_eastern_states for PM-KUSUM special category states
        norm_c_geo = "north_eastern_states" if c_geo in ("north_eastern_states", "hilly_and_difficult_areas") else c_geo
        norm_r_geo = "north_eastern_states" if r_geo in ("north_eastern_states", "hilly_and_difficult_areas") else r_geo

        if rule_parameter in ("central_subsidy_pct", "total_subsidy_pct", "farmer_contribution_pct"):
            if norm_c_geo == "north_eastern_states" and norm_r_geo in ("all_india", "general_states"):
                mismatches.append(
                    f"geography_mismatch: claimed='{c_geo}' vs rule='general_states'"
                )
            elif norm_c_geo in ("general_states", "plains_areas", "all_india", None) and norm_r_geo == "north_eastern_states":
                mismatches.append(
                    "geography_mismatch: claimed='general_states' vs rule='north_eastern_and_hilly_states'"
                )

        if rule_parameter == "max_pump_capacity_hp" and c_ben == "fpo_water_user_associations":
            mismatches.append("beneficiary_mismatch: claimed='fpo_water_user_associations' vs rule='individual_farmers'")
        if rule_parameter == "cluster_community_pump_capacity_hp" and c_ben == "individual_farmers":
            mismatches.append("beneficiary_mismatch: claimed='individual_farmers' vs rule='fpo_water_user_associations'")

        return len(mismatches) == 0, mismatches


PMKUSUMScheme = PMKusumScheme

