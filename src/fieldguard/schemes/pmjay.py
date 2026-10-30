"""Ayushman Bharat PM-JAY (Pradhan Mantri Jan Arogya Yojana) domain adapter."""

from __future__ import annotations

from typing import Any
from fieldguard.schemes.base import BaseScheme, SchemeContextValidationResult


class PMJAYScheme(BaseScheme):
    """
    Scheme adapter for Ayushman Bharat — Pradhan Mantri Jan Arogya Yojana (PM-JAY).
    Key domain rules:
    - ₹5,00,000 (5 lakh) annual health coverage per eligible family per year
    - Secondary and tertiary care hospitalisation
    - 3 days pre-hospitalization and 15 days post-hospitalization coverage
    - 100% cashless and paperless benefit at public and empanelled private hospitals
    - No restriction on family size, age, or gender
    - Pre-existing conditions covered from Day 1
    """

    scheme_id = "PM_JAY"
    full_name = "Ayushman Bharat — Pradhan Mantri Jan Arogya Yojana"
    domain = "health_insurance_assurance"
    aliases = ["pmjay", "pm-jay", "ayushman_bharat", "ayushman", "ab-pmjay", "ab_pmjay"]
    parameters = [
        "annual_health_cover_inr",
        "pre_hospitalization_days",
        "post_hospitalization_days",
        "cashless_benefit_percentage",
        "family_size_limit",
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
            details="Valid PM-JAY context",
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
            if c_entity != r_entity and r_entity != "all_eligible_families":
                reasons.append(f"beneficiary_mismatch(claimed={c_entity}, rule={r_entity})")

        return len(reasons) == 0, reasons

