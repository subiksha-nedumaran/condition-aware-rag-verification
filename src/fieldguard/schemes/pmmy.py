"""PMMY (Pradhan Mantri Mudra Yojana) scheme adapter."""

from __future__ import annotations

from typing import Any

from fieldguard.schemes.base import ContextValidationResult, ParameterSpec, SchemeDefinition


class PMMYScheme(SchemeDefinition):
    """Scheme adapter for PMMY (MUDRA)."""

    @property
    def scheme_id(self) -> str:
        return "PMMY"

    @property
    def full_name(self) -> str:
        return "Pradhan Mantri Mudra Yojana (PMMY)"

    @property
    def aliases(self) -> list[str]:
        return ["pmmy", "mudra", "mudra_yojana", "shishu_kishore_tarun"]

    @property
    def parameters(self) -> list[ParameterSpec]:
        return [
            ParameterSpec(
                name="shishu_loan_cap_inr",
                description="Maximum loan limit under the Shishu category of PMMY (up to Rs 50,000)",
                canonical_unit="rupees",
                required_context_fields=["loan_category"],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="kishore_loan_cap_inr",
                description="Maximum loan limit under the Kishore category of PMMY (above Rs 50,000 up to Rs 5,00,000)",
                canonical_unit="rupees",
                required_context_fields=["loan_category"],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="kishore_loan_min_inr",
                description="Minimum loan threshold above which Kishore category begins (Rs 50,000)",
                canonical_unit="rupees",
                required_context_fields=[],
                optional_context_fields=["loan_category"],
            ),
            ParameterSpec(
                name="tarun_loan_cap_inr",
                description="Maximum loan limit under the standard Tarun category of PMMY (above Rs 5,00,000 up to Rs 10,00,000)",
                canonical_unit="rupees",
                required_context_fields=["loan_category"],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="tarun_loan_min_inr",
                description="Minimum loan threshold above which Tarun category begins (Rs 5,00,000)",
                canonical_unit="rupees",
                required_context_fields=[],
                optional_context_fields=["loan_category"],
            ),
            ParameterSpec(
                name="tarun_plus_loan_cap_inr",
                description="Maximum loan limit under the Tarun Plus category for repeat Tarun borrowers (up to Rs 20,00,000)",
                canonical_unit="rupees",
                required_context_fields=[],
                optional_context_fields=["loan_category", "beneficiary_type"],
            ),
            ParameterSpec(
                name="collateral_security_requirement_pct",
                description="Collateral or third-party security percentage required for PMMY loans (0%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="shishu_processing_fee_pct",
                description="Upfront processing fee percentage charged by banks on Shishu category loans (0%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["loan_category"],
            ),
            ParameterSpec(
                name="shishu_margin_money_pct",
                description="Promoter margin money percentage required for Shishu category loans (0%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["loan_category"],
            ),
            ParameterSpec(
                name="kishore_tarun_margin_money_min_pct",
                description="Minimum promoter margin money contribution percentage for Kishore and Tarun loans (10%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["loan_category"],
            ),
            ParameterSpec(
                name="shishu_interest_subvention_pct",
                description="Interest subvention rate per annum for prompt repayment of Shishu loans (2%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["loan_category"],
            ),
            ParameterSpec(
                name="shishu_interest_subvention_period_months",
                description="Duration in months for which 2% interest subvention is payable on Shishu loans (12 months)",
                canonical_unit="months",
                required_context_fields=[],
                optional_context_fields=["loan_category"],
            ),
            ParameterSpec(
                name="cgfmu_guarantee_cover_pct",
                description="Maximum portfolio credit guarantee coverage percentage under CGFMU for amount in default (75%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="cgfmu_first_loss_default_borne_by_lender_pct",
                description="First-loss default percentage of crystallized portfolio borne by the lending institution under CGFMU (3%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="shishu_corpus_earmarking_minimum_pct",
                description="Minimum percentage of total PMMY credit corpus earmarked for Shishu category units (60%)",
                canonical_unit="percent",
                required_context_fields=[],
                optional_context_fields=["loan_category"],
            ),
            ParameterSpec(
                name="maximum_repayment_tenure_years",
                description="Standard maximum repayment tenure in years for MUDRA term loans (5 years)",
                canonical_unit="years",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="extended_repayment_tenure_years",
                description="Maximum extended repayment tenure in years for MUDRA term loans based on cash flow (7 years)",
                canonical_unit="years",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="minimum_borrower_age_years",
                description="Minimum eligible age in years for an individual MUDRA loan applicant (18 years)",
                canonical_unit="years",
                required_context_fields=[],
                optional_context_fields=[],
            ),
            ParameterSpec(
                name="maximum_borrower_age_years",
                description="Maximum eligible age in years for an individual MUDRA loan borrower (65 years)",
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
        c_cat = claimed_context.get("loan_category")
        r_cat = rule_context.get("loan_category")

        c_ben = claimed_context.get("beneficiary_type")
        if c_ben == "corporate_company":
            mismatches.append(
                "beneficiary_mismatch: PMMY covers non-corporate small/micro enterprises, not corporate_company"
            )
        if c_ben == "first_time_new_borrower" and (
            r_cat == "tarun_plus" or rule_parameter == "tarun_plus_loan_cap_inr"
        ):
            mismatches.append(
                "eligibility_mismatch: Tarun Plus loans up to Rs 20 lakh are restricted to repeat borrowers who repaid a previous Tarun loan"
            )

        if c_cat and r_cat and c_cat != r_cat:
            mismatches.append(f"loan_category_mismatch: claimed='{c_cat}' vs rule='{r_cat}'")

        return len(mismatches) == 0, mismatches

