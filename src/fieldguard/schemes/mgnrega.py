"""MGNREGS (Mahatma Gandhi National Rural Employment Guarantee Scheme) domain adapter."""

from __future__ import annotations

from typing import Any
import re
from fieldguard.schemes.base import BaseScheme, SchemeContextValidationResult


class MGNREGAScheme(BaseScheme):
    """
    Scheme adapter for Mahatma Gandhi National Rural Employment Guarantee Act (MGNREGS).
    Key domain rules:
    - 100 days statutory guaranteed wage employment per rural household per financial year
    - 15 days timeline from application to work allocation (otherwise unemployment allowance)
    - 15 days wage disbursement timeline (delay compensation at 0.05% per day)
    - Minimum 33.33% (1/3rd) women participation quota
    - 60:40 wage to material cost ratio at the Gram Panchayat level
    """

    scheme_id = "MGNREGA"
    full_name = "Mahatma Gandhi National Rural Employment Guarantee Act"
    domain = "rural_wage_employment"
    aliases = ["mgnrega", "nrega", "mgnregs", "rural_employment", "nregs"]
    parameters = [
        "guaranteed_employment_days",
        "work_allocation_timeline_days",
        "unemployment_allowance_timeline_days",
        "wage_payment_timeline_days",
        "delay_compensation_rate",
        "women_participation_quota",
        "wage_material_ratio",
    ]

    def get_required_context_keys(self, rule_parameter: str) -> list[str]:
        return ["beneficiary_type"]

    def validate_claim_context(
        self,
        rule_parameter: str | None,
        context_dict: dict[str, Any],
        enable_switches: dict[str, bool] | None = None,
    ) -> SchemeContextValidationResult:
        return SchemeContextValidationResult(
            is_valid=True,
            missing_fields=[],
            details="Valid MGNREGS context",
        )

    def match_conditions(
        self,
        claimed_context: dict[str, Any],
        rule_context: dict[str, Any],
        rule_parameter: str,
        enable_switches: dict[str, bool] | None = None,
    ) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        c_entity = claimed_context.get("beneficiary_type") or claimed_context.get("entity_scope") or claimed_context.get("crop_category")
        r_entity = rule_context.get("beneficiary_type") or rule_context.get("entity_scope") or rule_context.get("crop_category")

        if c_entity and r_entity:
            # Check urban vs rural
            if "urban" in str(c_entity).lower() and "rural" in str(r_entity).lower():
                reasons.append(f"entity_mismatch(claimed={c_entity}, rule_restricted_to={r_entity})")
            elif c_entity != r_entity and r_entity != "all_rural_households":
                reasons.append(f"beneficiary_mismatch(claimed={c_entity}, rule={r_entity})")

        return len(reasons) == 0, reasons

