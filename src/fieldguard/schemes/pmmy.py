"""PMMY (Pradhan Mantri Mudra Yojana) domain adapter."""

from __future__ import annotations

from typing import Any
from fieldguard.schemes.base import BaseScheme, SchemeContextValidationResult


class PMMYScheme(BaseScheme):
    """
    Scheme adapter for Pradhan Mantri Mudra Yojana (PMMY).
    Key domain rules:
    - Shishu category: loans up to ₹50,000
    - Kishore category: loans above ₹50,000 and up to ₹5,00,000
    - Tarun category: loans above ₹5,00,000 and up to ₹10,00,000 (and up to ₹20 lakh for Tarun Plus)
    - Zero collateral required for all Mudra loans
    """

    scheme_id = "PMMY"
    full_name = "Pradhan Mantri Mudra Yojana"
    domain = "micro_enterprise_credit"
    aliases = ["pmmy", "mudra", "mudra_yojana", "pradhan_mantri_mudra_yojana"]
    parameters = [
        "shishu_loan_cap_inr",
        "kishore_loan_cap_inr",
        "tarun_loan_cap_inr",
        "collateral_requirement",
    ]

    def get_required_context_keys(self, rule_parameter: str) -> list[str]:
        return ["loan_category"]

    def validate_claim_context(
        self,
        rule_parameter: str | None,
        context_dict: dict[str, Any],
        enable_switches: dict[str, bool] | None = None,
    ) -> SchemeContextValidationResult:
        return SchemeContextValidationResult(is_valid=True, missing_fields=[], details="Valid PMMY context")

    def match_conditions(
        self,
        claimed_context: dict[str, Any],
        rule_context: dict[str, Any],
        rule_parameter: str,
        enable_switches: dict[str, bool] | None = None,
    ) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        c_cat = claimed_context.get("entity_scope") or claimed_context.get("crop_category")
        r_cat = rule_context.get("entity_scope") or rule_context.get("crop_category")

        if c_cat and r_cat and c_cat != r_cat:
            reasons.append(f"mudra_category_mismatch(claimed={c_cat}, rule={r_cat})")

        return len(reasons) == 0, reasons

