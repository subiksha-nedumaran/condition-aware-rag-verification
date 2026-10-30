"""Generic Dynamic Scheme adapter for user-uploaded policy documents."""

from __future__ import annotations

from typing import Any
from fieldguard.schemes.base import BaseScheme, SchemeContextValidationResult


class GenericUploadedScheme(BaseScheme):
    """
    Adaptive scheme adapter for user-uploaded government scheme documents (PDF/Text).
    Accepts arbitrary numerical parameters, entity scopes, and eligibility constraints
    grounded directly in the uploaded document's extracted chunks and tables.
    """

    scheme_id = "CUSTOM_UPLOADED"
    full_name = "User Uploaded Government Policy Document"
    domain = "custom_uploaded_scheme"
    aliases = ["custom", "custom_uploaded", "uploaded_doc", "uploaded", "user_scheme"]
    parameters = ["custom_policy_rule"]

    def get_required_context_keys(self, rule_parameter: str) -> list[str]:
        return []

    def validate_claim_context(
        self,
        rule_parameter: str | None,
        context_dict: dict[str, Any],
        enable_switches: dict[str, bool] | None = None,
    ) -> SchemeContextValidationResult:
        return SchemeContextValidationResult(
            is_valid=True,
            missing_fields=[],
            details="Valid custom uploaded scheme context",
        )

    def match_conditions(
        self,
        claimed_context: dict[str, Any],
        rule_context: dict[str, Any],
        rule_parameter: str,
        enable_switches: dict[str, bool] | None = None,
    ) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        c_entity = claimed_context.get("entity_scope") or claimed_context.get("crop_category")
        r_entity = rule_context.get("entity_scope") or rule_context.get("crop_category")

        if c_entity and r_entity and c_entity != r_entity and r_entity != "all_general":
            reasons.append(f"entity_mismatch(claimed={c_entity}, rule={r_entity})")

        return len(reasons) == 0, reasons

