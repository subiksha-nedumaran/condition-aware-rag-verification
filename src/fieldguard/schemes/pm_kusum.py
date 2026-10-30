"""PM-KUSUM (Pradhan Mantri Kisan Urja Suraksha evam Utthaan Mahabhiyan) domain adapter."""

from __future__ import annotations

from typing import Any
from fieldguard.schemes.base import BaseScheme, SchemeContextValidationResult


class PMKusumScheme(BaseScheme):
    """
    Scheme adapter for PM-KUSUM (Solar Agriculture).
    Key domain rules:
    - 60% total subsidy: 30% Central Financial Assistance (CFA) + 30% State Govt subsidy
    - 40% farmer contribution (or 10% cash + 30% institutional bank loan)
    - Standalone solar agriculture pumps up to 7.5 Horsepower (HP) capacity
    """

    scheme_id = "PM_KUSUM"
    full_name = "Pradhan Mantri Kisan Urja Suraksha evam Utthaan Mahabhiyan"
    domain = "solar_agriculture"
    aliases = ["pmkusum", "pm-kusum", "pm_kusum", "kusum", "solar_pumps"]
    parameters = [
        "central_subsidy_pct",
        "state_subsidy_pct",
        "total_subsidy_pct",
        "farmer_share_pct",
        "max_pump_capacity_hp",
    ]

    def get_required_context_keys(self, rule_parameter: str) -> list[str]:
        return ["beneficiary_type"]

    def validate_claim_context(
        self,
        rule_parameter: str | None,
        context_dict: dict[str, Any],
        enable_switches: dict[str, bool] | None = None,
    ) -> SchemeContextValidationResult:
        return SchemeContextValidationResult(is_valid=True, missing_fields=[], details="Valid PM-KUSUM context")

    def match_conditions(
        self,
        claimed_context: dict[str, Any],
        rule_context: dict[str, Any],
        rule_parameter: str,
        enable_switches: dict[str, bool] | None = None,
    ) -> tuple[bool, list[str]]:
        return True, []

