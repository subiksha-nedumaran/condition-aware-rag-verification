"""PMAY-G (Pradhan Mantri Awas Yojana — Gramin) scheme adapter."""

from __future__ import annotations

from typing import Any

from fieldguard.schemes.base import ContextValidationResult, ParameterSpec, SchemeDefinition


class PMAYGScheme(SchemeDefinition):
    """Scheme adapter for PMAY-G."""

    @property
    def scheme_id(self) -> str:
        return "PMAY_G"

    @property
    def full_name(self) -> str:
        return "Pradhan Mantri Awas Yojana — Gramin (PMAY-G)"

    @property
    def aliases(self) -> list[str]:
        return ["pmay_g", "pmayg", "pmay-g", "awas_yojana_gramin", "pmay_rural"]

    @property
    def parameters(self) -> list[ParameterSpec]:
        return [
            ParameterSpec(
                name="unit_grant_assistance_inr",
                description="Financial grant assistance per housing unit (Rs 1,20,000 in plain areas; Rs 1,30,000 in hilly/difficult/IAP areas)",
                canonical_unit="rupees",
                required_context_fields=["geography"],
                optional_context_fields=["beneficiary_type"],
            ),
            ParameterSpec(
                name="minimum_house_size_sqm",
                description="Minimum prescribed house floor area in square metres (25 sq.m under PMAY-G; 20 sq.m under historical IAY)",
                canonical_unit="square_metres",
                required_context_fields=[],
                optional_context_fields=["geography"],
            ),
            ParameterSpec(
                name="toilet_construction_assistance_inr",
                description="Financial assistance for household toilet construction in convergence with SBM-G / MGNREGA (Rs 12,000)",
                canonical_unit="rupees",
                required_context_fields=[],
                optional_context_fields=["beneficiary_type"],
            ),
            ParameterSpec(
                name="mgnrega_unskilled_labour_person_days",
                description="Mandatory convergence of unskilled manual labour person-days under MGNREGA (90 days in plains; 95 days in hilly/difficult/IAP areas)",
                canonical_unit="days",
                required_context_fields=[],
                optional_context_fields=["geography"],
            ),
            ParameterSpec(
                name="optional_institutional_loan_cap_inr",
                description="Maximum optional institutional bank loan facilitated for PMAY-G house construction (Rs 70,000)",
                canonical_unit="rupees",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="loan_interest_subvention_pct",
                description="Interest subvention rate per annum on optional institutional housing loans up to Rs 70,000 (3%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="central_funding_share_pct",
                description="Central Government share of unit assistance cost (60% in plains, 90% in NE/Himalayan states, 100% in UTs)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["geography"],
            ),
            ParameterSpec(
                name="state_funding_share_pct",
                description="State Government share of unit assistance cost (40% in plains, 10% in NE/Himalayan states)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["geography"],
            ),
            ParameterSpec(
                name="construction_completion_timeline_months",
                description="Maximum timeline in months from sanction of first instalment to complete house construction (12 months)",
                canonical_unit="months",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="minimum_disbursement_instalments_count",
                description="Minimum number of geo-tagged stage-linked instalments for releasing unit assistance (3 instalments)",
                canonical_unit="instalments",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="sc_st_target_earmarking_pct",
                description="Minimum percentage of national/State targets earmarked for SC/ST households (60%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["beneficiary_type"],
            ),
            ParameterSpec(
                name="minority_target_earmarking_pct",
                description="Maximum percentage of targets earmarked for minority households (15%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["beneficiary_type"],
            ),
            ParameterSpec(
                name="pwd_reservation_pct",
                description="Minimum horizontal reservation percentage for Persons with Disabilities (5%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["beneficiary_type"],
            ),
            ParameterSpec(
                name="administrative_funds_ceiling_pct",
                description="Maximum percentage of programme funds permissible towards administrative expenses (2%)",
                canonical_unit="percent",
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
        if rule_parameter == "unit_grant_assistance_inr" and not context.get("geography"):
            return ContextValidationResult(is_valid=False, missing_fields=["geography"])
        return ContextValidationResult(is_valid=True)

    def match_conditions(
        self,
        claimed_context: dict[str, Any],
        rule_context: dict[str, Any],
        rule_parameter: str | None = None,
        enable_switches: dict[str, bool] | None = None,
    ) -> tuple[bool, list[str]]:
        mismatches: list[str] = []
        c_geo = claimed_context.get("geography")
        r_geo = rule_context.get("geography")

        c_ben = claimed_context.get("beneficiary_type")
        r_ben = rule_context.get("beneficiary_type")

        if c_ben == "urban_household":
            mismatches.append("scheme_scope_mismatch: PMAY-G covers rural households only, not urban_household")

        if (
            c_ben
            and r_ben
            and c_ben in ("sc_st_households", "minority_households", "persons_with_disabilities")
            and r_ben in ("sc_st_households", "minority_households", "persons_with_disabilities")
            and c_ben != r_ben
        ):
            mismatches.append(f"beneficiary_category_mismatch: claimed='{c_ben}' vs rule='{r_ben}'")

        def _norm_geo(g: str | None) -> str | None:
            if g in ("north_eastern_states", "hilly_areas", "hilly_and_difficult_areas", "north_eastern_and_himalayan_states"):
                return "hilly_and_difficult_areas"
            if g in ("general_states", "plains_areas"):
                return "plains_areas"
            if g in ("union_territories", "union_territories_without_legislature"):
                return "union_territories"
            return g

        norm_c_geo = _norm_geo(c_geo)
        norm_r_geo = _norm_geo(r_geo)

        if (
            norm_c_geo
            and norm_r_geo
            and norm_c_geo not in ("all_india",)
            and norm_r_geo not in ("all_india",)
            and norm_c_geo != norm_r_geo
        ):
            mismatches.append(f"geography_mismatch: claimed='{c_geo}' vs rule='{r_geo}'")

        return len(mismatches) == 0, mismatches

