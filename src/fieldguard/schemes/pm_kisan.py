"""PM-KISAN (Pradhan Mantri Kisan Samman Nidhi) scheme domain adapter."""

from __future__ import annotations

from typing import Any

from fieldguard.schemes.base import BaseScheme, SchemeContextValidationResult


class PMKisanScheme(BaseScheme):
    """
    Scheme adapter for Pradhan Mantri Kisan Samman Nidhi (PM-KISAN).
    Encapsulates domain taxonomy for direct income support:
    - Annual income support: ₹6,000 per year in 3 equal instalments of ₹2,000
    - Beneficiary categories: Landholding farmer families (cultivable land)
    - Non-eligible categories: Tenant farmers, sharecroppers, agricultural laborers
    - Statutory exclusions: Institutional holders, constitutional posts, govt employees,
      pensioners >= ₹10k, income tax payees, registered professionals (doctors/lawyers/CA)
    - Operational compliance: Mandatory eKYC, Aadhaar-seeded bank accounts, land registry seeding
    - Policy shifts: Feb 2019 (2 ha cap for SMFs) -> June 2019 (expanded to all landholding farmers).
    """

    scheme_id = "PM_KISAN"
    full_name = "Pradhan Mantri Kisan Samman Nidhi"
    domain = "direct_income_support"
    aliases = ["pm_kisan", "pm-kisan", "pmkisan", "kisan_samman_nidhi", "pmksny"]
    parameters = [
        "annual_income_support",
        "instalment_amount",
        "instalments_per_year",
        "instalment_period_months",
        "landholding_eligibility_cap_ha",
        "mandatory_ekyc_requirement",
        "statutory_exclusion",
        "aadhaar_seeding_requirement",
    ]

    # Standard exclusion categories defined in PM-KISAN Operational Guidelines
    STATUTORY_EXCLUSIONS = {
        "institutional_landholder",
        "constitutional_post_holder",
        "former_present_minister_mp_mla",
        "former_present_mayor_zilla_panchayat_chairperson",
        "government_employee",
        "pensioner_ge_10000",
        "income_tax_payee",
        "registered_professional",
    }

    # Ineligible farmer groups that do not own cultivable land
    NON_LANDHOLDING_INELIGIBLE = {
        "tenant_farmer",
        "sharecropper",
        "agricultural_laborer",
        "landless_cultivator",
    }

    def get_required_context_keys(self, rule_parameter: str) -> list[str]:
        if rule_parameter in ("annual_income_support", "instalment_amount"):
            return ["beneficiary_type"]
        elif rule_parameter == "statutory_exclusion":
            return ["exclusion_category"]
        elif rule_parameter == "landholding_eligibility_cap_ha":
            return ["beneficiary_type"]
        return []

    def validate_claim_context(
        self,
        rule_parameter: str | None,
        context_dict: dict[str, Any],
        enable_switches: dict[str, bool] | None = None,
    ) -> SchemeContextValidationResult:
        missing: list[str] = []
        beneficiary = context_dict.get("beneficiary_type") or context_dict.get("entity_scope")
        exclusion = context_dict.get("exclusion_category")

        if rule_parameter in ("annual_income_support", "instalment_amount"):
            if beneficiary is None:
                missing.append("beneficiary_type")
        elif rule_parameter == "statutory_exclusion":
            if exclusion is None and beneficiary is None:
                missing.append("exclusion_category")
        elif rule_parameter == "landholding_eligibility_cap_ha":
            if beneficiary is None:
                missing.append("beneficiary_type")

        return SchemeContextValidationResult(
            is_valid=len(missing) == 0,
            missing_fields=missing,
            details=f"Missing required PM-KISAN fields: {missing}" if missing else "Valid PM-KISAN context",
        )

    def match_conditions(
        self,
        claimed_context: dict[str, Any],
        rule_context: dict[str, Any],
        rule_parameter: str,
        enable_switches: dict[str, bool] | None = None,
    ) -> tuple[bool, list[str]]:
        reasons: list[str] = []

        claimed_beneficiary = claimed_context.get("beneficiary_type") or claimed_context.get("entity_scope") or claimed_context.get("crop_category")
        rule_beneficiary = rule_context.get("beneficiary_type") or rule_context.get("entity_scope") or rule_context.get("crop_category")
        claimed_freq = claimed_context.get("frequency") or claimed_context.get("season")
        rule_freq = rule_context.get("frequency") or rule_context.get("season")
        claimed_exclusion = claimed_context.get("exclusion_category")
        rule_exclusions = rule_context.get("exclusions", [])

        # 1. Beneficiary category matching
        if claimed_beneficiary is not None and rule_beneficiary is not None:
            if claimed_beneficiary == rule_beneficiary:
                # Same category matches directly (e.g. tenant_farmer to tenant_farmer)
                pass
            elif claimed_beneficiary in self.NON_LANDHOLDING_INELIGIBLE and rule_beneficiary == "all_landholding_farmers":
                reasons.append(
                    f"ineligible_beneficiary_mismatch(claimed={claimed_beneficiary}, "
                    f"rule_requires=cultivable_landholding_farmer_family)"
                )
            elif rule_beneficiary == "all_landholding_farmers":
                if claimed_beneficiary not in (
                    "all_landholding_farmers",
                    "small_and_marginal_farmers",
                    "medium_and_large_farmers",
                    "landholding_farmer_family",
                ):
                    reasons.append(
                        f"beneficiary_mismatch(claimed={claimed_beneficiary}, rule={rule_beneficiary})"
                    )
            elif claimed_beneficiary != rule_beneficiary:
                reasons.append(
                    f"beneficiary_mismatch(claimed={claimed_beneficiary}, rule={rule_beneficiary})"
                )

        # 2. Statutory exclusion checks
        excl_cat = claimed_exclusion or (claimed_beneficiary if claimed_beneficiary in self.STATUTORY_EXCLUSIONS else None)
        if excl_cat is not None:
            if excl_cat in self.STATUTORY_EXCLUSIONS:
                if rule_beneficiary == excl_cat:
                    pass
                elif rule_beneficiary == "all_landholding_farmers":
                    reasons.append(
                        f"exclusion_violation(claimed_category={excl_cat}_is_statutorily_excluded)"
                    )

        # 3. Frequency matching (annual vs per instalment / four-monthly)
        if claimed_freq is not None and rule_freq is not None:
            norm_c_freq = "per_instalment" if claimed_freq in ("per_instalment", "four_monthly") else claimed_freq
            norm_r_freq = "per_instalment" if rule_freq in ("per_instalment", "four_monthly") else rule_freq
            if norm_c_freq != norm_r_freq:
                reasons.append(f"frequency_mismatch(claimed={claimed_freq}, rule={rule_freq})")

        return len(reasons) == 0, reasons

