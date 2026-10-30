"""PMAY-G (Pradhan Mantri Awas Yojana — Gramin) domain adapter."""

from __future__ import annotations

from typing import Any
from fieldguard.schemes.base import BaseScheme, SchemeContextValidationResult


class PMAYGScheme(BaseScheme):
    """
    Scheme adapter for Pradhan Mantri Awas Yojana — Gramin (PMAY-G).
    Key domain rules:
    - ₹1,20,000 unit grant assistance in plain areas
    - ₹1,30,000 unit grant assistance in hilly, difficult, North-Eastern and IAP districts
    - 25 sq. metres minimum house floor area (including hygienic cooking space)
    - ₹12,000 additional assistance for toilet construction via Swachh Bharat Mission (SBM-G)
    - 90-95 person days of unskilled labour under MGNREGS
    """

    scheme_id = "PMAY_G"
    full_name = "Pradhan Mantri Awas Yojana — Gramin"
    domain = "rural_housing"
    aliases = ["pmay", "pmay-g", "pmay_g", "pmayg", "awas_yojana", "rural_housing"]
    parameters = [
        "unit_grant_assistance_inr",
        "minimum_house_size_sqm",
        "toilet_assistance_sbm_inr",
        "mgnregs_unskilled_labour_days",
    ]

    def get_required_context_keys(self, rule_parameter: str) -> list[str]:
        return ["geography"]

    def validate_claim_context(
        self,
        rule_parameter: str | None,
        context_dict: dict[str, Any],
        enable_switches: dict[str, bool] | None = None,
    ) -> SchemeContextValidationResult:
        return SchemeContextValidationResult(
            is_valid=True,
            missing_fields=[],
            details="Valid PMAY-G context",
        )

    def match_conditions(
        self,
        claimed_context: dict[str, Any],
        rule_context: dict[str, Any],
        rule_parameter: str,
        enable_switches: dict[str, bool] | None = None,
    ) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        c_geo = claimed_context.get("geography")
        r_geo = rule_context.get("geography")

        if c_geo and r_geo:
            if c_geo != r_geo and r_geo != "all_india":
                reasons.append(f"geography_mismatch(claimed={c_geo}, rule={r_geo})")

        return len(reasons) == 0, reasons
