"""PMFBY (Pradhan Mantri Fasal Bima Yojana) scheme domain adapter."""

from __future__ import annotations

from typing import Any

from fieldguard.schemes.base import BaseScheme, SchemeContextValidationResult


class PMFBYScheme(BaseScheme):
    """
    Scheme adapter for Pradhan Mantri Fasal Bima Yojana (PMFBY).
    Preserves exact condition logic and parameter definitions from Stage 1.
    """

    scheme_id = "PMFBY"
    full_name = "Pradhan Mantri Fasal Bima Yojana"
    domain = "crop_insurance"
    aliases = ["pmfby", "fasal_bima", "pm_fasal_bima"]
    parameters = [
        "farmer_premium_rate",
        "central_subsidy_actuarial_cap",
        "central_subsidy_share",
        "threshold_yield_best_years",
        "prevented_sowing_on_account_payout",
        "mid_season_adversity_relief",
        "post_harvest_coverage_window",
        "localized_loss_intimation_window",
    ]

    def get_required_context_keys(self, rule_parameter: str) -> list[str]:
        if rule_parameter == "farmer_premium_rate":
            return ["crop_category", "season"]
        elif rule_parameter == "central_subsidy_actuarial_cap":
            return ["crop_category"]
        elif rule_parameter == "central_subsidy_share":
            return ["geography"]
        return []

    def validate_claim_context(
        self,
        rule_parameter: str | None,
        context_dict: dict[str, Any],
        enable_switches: dict[str, bool] | None = None,
    ) -> SchemeContextValidationResult:
        switches = enable_switches or {}
        missing: list[str] = []

        crop_cat = context_dict.get("crop_category")
        season = context_dict.get("season")
        geo = context_dict.get("geography")

        if rule_parameter == "farmer_premium_rate":
            if switches.get("enable_crop_category_matching", True) and crop_cat is None:
                missing.append("crop_category")
            if (
                switches.get("enable_season_matching", True)
                and season is None
                and crop_cat != "commercial_and_horticultural"
            ):
                missing.append("season")
        elif rule_parameter == "central_subsidy_actuarial_cap":
            if switches.get("enable_crop_category_matching", True) and crop_cat is None:
                missing.append("crop_category")
        elif rule_parameter == "central_subsidy_share":
            if geo is None:
                missing.append("geography")

        return SchemeContextValidationResult(
            is_valid=len(missing) == 0,
            missing_fields=missing,
            details=f"Missing required PMFBY fields: {missing}" if missing else "Valid PMFBY context",
        )

    def match_conditions(
        self,
        claimed_context: dict[str, Any],
        rule_context: dict[str, Any],
        rule_parameter: str,
        enable_switches: dict[str, bool] | None = None,
    ) -> tuple[bool, list[str]]:
        switches = enable_switches or {}
        reasons: list[str] = []

        claimed_crop = claimed_context.get("crop_category")
        rule_crop = rule_context.get("crop_category")
        claimed_season = claimed_context.get("season")
        rule_season = rule_context.get("season")
        claimed_geo = claimed_context.get("geography")
        rule_geo = rule_context.get("geography")

        # 1. Crop category matching
        if switches.get("enable_crop_category_matching", True) and claimed_crop is not None:
            if rule_crop == "all_notified_crops" and claimed_crop not in (
                "non_covered_livestock_aquaculture",
                "wild_animal_attack_addon",
            ):
                pass
            elif claimed_crop != rule_crop:
                reasons.append(f"crop_category_mismatch(claimed={claimed_crop}, rule={rule_crop})")

        # 2. Season matching
        if switches.get("enable_season_matching", True) and claimed_season is not None:
            if rule_season == "annual":
                pass
            elif claimed_season != rule_season:
                reasons.append(f"season_mismatch(claimed={claimed_season}, rule={rule_season})")

        # 3. Geography matching
        if claimed_geo is not None and rule_geo != "all_india":
            if claimed_geo != rule_geo:
                reasons.append(f"geography_mismatch(claimed={claimed_geo}, rule={rule_geo})")

        return len(reasons) == 0, reasons

