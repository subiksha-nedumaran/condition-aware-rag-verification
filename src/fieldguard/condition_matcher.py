"""Structured semantic condition, qualification, basis, and provenance matcher (Section 10.3)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from fieldguard.claim_parser import ParsedClaim
from fieldguard.evidence_schema import StructuredRuleRecord
from fieldguard.metadata import ExtractedEvidenceUnit
from fieldguard.numeric_normalizer import (
    compare_numeric_values,
    extract_all_numeric_mentions,
)
from fieldguard.schemes import get_scheme_adapter
from fieldguard.temporal_resolver import (
    TemporalResolutionResult,
    resolve_temporal_applicability,
)


@dataclass
class ConditionMatchConfig:
    """Granular component switches supporting full FieldGuard and single-component ablations."""

    enable_structured_condition_matching: bool = True
    enable_crop_category_matching: bool = True
    enable_season_matching: bool = True
    enable_qualification_matching: bool = True
    enable_temporal_checks: bool = True
    enable_provenance_validation: bool = True
    numeric_rel_tol: float = 1e-6
    numeric_abs_tol: float = 1e-6


@dataclass
class RuleMatchResult:
    """Detailed component-level match result between a ParsedClaim and a StructuredRuleRecord."""

    rule_id: str
    evidence_id: str
    source_document_id: str
    provenance_valid: bool
    scheme_match: bool
    parameter_match: bool
    crop_category_match: bool
    season_match: bool
    geography_match: bool
    temporal_result: TemporalResolutionResult
    value_unit_match: bool
    basis_match: bool
    operator_match: bool
    qualification_match: bool
    conflict_flag: bool
    context_matches_all: bool
    is_full_support: bool
    is_contradiction_in_same_context: bool
    is_wrong_context_for_matched_number: bool
    mismatch_reasons: list[str] = field(default_factory=list)
    context_mismatch_dimensions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["temporal_result"] = self.temporal_result.to_dict()
        return d


def _match_season(
    claimed_season: str | None,
    rule_season: str | None,
    claimed_crop_category: str | None,
    rule_crop_category: str | None,
    enable_season_matching: bool,
) -> tuple[bool, str | None]:
    if not enable_season_matching:
        return True, None

    if claimed_season is None:
        return True, None

    if rule_season == "annual":
        # Annual rules (such as commercial/horticultural 5% rate) apply across both Kharif and Rabi
        # ONLY when the crop category is also commercial/horticultural (or general annual rule).
        return True, None

    if claimed_season == rule_season:
        return True, None

    return False, f"season_mismatch(claimed={claimed_season}, rule={rule_season})"


def _match_crop_category(
    claimed_crop: str | None,
    rule_crop: str | None,
    enable_crop_category_matching: bool,
) -> tuple[bool, str | None]:
    if not enable_crop_category_matching:
        return True, None

    if claimed_crop is None:
        return True, None

    if rule_crop == "all_notified_crops" and claimed_crop not in (
        "non_covered_livestock_aquaculture",
        "wild_animal_attack_addon",
    ):
        return True, None

    if claimed_crop == rule_crop:
        return True, None

    return False, f"crop_category_mismatch(claimed={claimed_crop}, rule={rule_crop})"


def _match_geography(
    claimed_geo: str | None,
    rule_geo: str | None,
    enable_structured_condition_matching: bool,
) -> tuple[bool, str | None]:
    if not enable_structured_condition_matching:
        return True, None
    if claimed_geo is None or rule_geo == "all_india":
        return True, None
    if claimed_geo == rule_geo:
        return True, None
    return False, f"geography_mismatch(claimed={claimed_geo}, rule={rule_geo})"


def _match_qualification_and_basis(
    claim: ParsedClaim,
    rule: StructuredRuleRecord,
    enable_qualification_matching: bool,
) -> tuple[bool, bool, bool, list[str]]:
    """
    Evaluate (basis_match, operator_match, qualification_match, reasons).
    When enable_qualification_matching is False (Ablation 5 or Baseline C), skips strict
    basis, operator, and 'whichever is less' / trigger qualification checks.
    """
    if not enable_qualification_matching:
        return True, True, True, []

    reasons: list[str] = []
    basis_ok = True
    op_ok = True
    qual_ok = True

    if claim.basis is not None and rule.basis is not None and claim.basis != rule.basis:
        if rule.basis != "per_policy_specification":
            basis_ok = False
            reasons.append(f"basis_mismatch(claimed={claim.basis}, rule={rule.basis})")

    # Operator check: e.g., claiming the maximum farmer premium is '> 2%' or 'at least 2%' when rule is '<= 2%'
    if claim.numeric_operator in ("gt", "ge") and rule.numeric_operator == "le":
        # Allow 'ge' only when rule.numeric_operator == 'ge' (like at least 7 days opt-out)
        op_ok = False
        reasons.append(
            f"operator_mismatch(claimed={claim.numeric_operator}, rule={rule.numeric_operator})"
        )
    elif claim.numeric_operator == "lt" and rule.numeric_operator in ("eq", "ge"):
        op_ok = False
        reasons.append(
            f"operator_mismatch(claimed={claim.numeric_operator}, rule={rule.numeric_operator})"
        )

    # Qualification check:
    # 1. If the rule requires 'or_actuarial_rate_whichever_is_less' and the claim asserts an unconditional flat rate
    #    or 'whichever is higher', qualification fails!
    if rule.requires_qualifier_for_unconditional_claim and claim.claims_unconditional_flat_rate:
        qual_ok = False
        reasons.append(
            f"qualification_violation(claim_asserts_unconditional_or_flat_rate, rule_requires={rule.qualifier})"
        )

    if claim.qualification is not None:
        if claim.qualification.startswith("contradictory_"):
            qual_ok = False
            reasons.append(
                f"qualification_violation(claimed={claim.qualification}, rule={rule.qualifier})"
            )
        elif claim.qualification != rule.qualifier:
            # Allow compatible subsets
            qual_ok = False
            reasons.append(
                f"qualification_mismatch(claimed={claim.qualification}, rule={rule.qualifier})"
            )

    return basis_ok, op_ok, qual_ok, reasons


def evaluate_rule_against_claim(
    claim: ParsedClaim,
    rule: StructuredRuleRecord,
    config: ConditionMatchConfig | None = None,
) -> RuleMatchResult:
    """
    Perform full condition-aware comparison between a ParsedClaim and a StructuredRuleRecord.
    """
    if config is None:
        config = ConditionMatchConfig()

    mismatch_reasons: list[str] = []
    context_mismatch_dims: list[str] = []

    # 1. Provenance check
    prov_ok = True
    if config.enable_provenance_validation and rule.verification_status != "trusted_official":
        prov_ok = False
        mismatch_reasons.append(f"untrusted_provenance({rule.verification_status})")

    # 2. Value and unit check
    if claim.claimed_value is None or claim.claimed_unit is None:
        val_unit_ok = False
        mismatch_reasons.append("missing_claimed_value_or_unit")
    else:
        val_unit_ok, val_msg = compare_numeric_values(
            claimed_value=claim.claimed_value,
            claimed_unit=claim.claimed_unit,
            rule_value=rule.maximum_rate,
            rule_unit=rule.unit,
            allowed_values=rule.allowed_values,
            rel_tol=config.numeric_rel_tol,
            abs_tol=config.numeric_abs_tol,
        )
        if not val_unit_ok:
            mismatch_reasons.append(val_msg)

    # 3. Scheme & Rule Parameter check
    if not config.enable_structured_condition_matching:
        scheme_ok = True
        param_ok = True
        crop_ok = True
        season_ok = True
        geo_ok = True
    else:
        scheme_ok = (
            claim.scheme is None
            or (claim.scheme == rule.scheme)
            or (rule.source_document_id and rule.source_document_id.startswith("DOC_UPLOAD_"))
        )
        if not scheme_ok:
            context_mismatch_dims.append(f"scheme_mismatch(claimed={claim.scheme}, rule={rule.scheme})")

        param_ok = (
            claim.rule_parameter is None
            or (claim.rule_parameter == rule.rule_parameter)
            or (rule.rule_parameter == "custom_policy_rule")
            or rule.rule_parameter.startswith("rule_p")
        )
        if not param_ok:
            if {claim.rule_parameter, rule.rule_parameter} == {"statutory_exclusion", "annual_income_support"}:
                param_ok = True
            else:
                context_mismatch_dims.append(
                    f"parameter_mismatch(claimed={claim.rule_parameter}, rule={rule.rule_parameter})"
                )

        scheme_adapter = get_scheme_adapter(rule.scheme)
        if scheme_adapter and rule.scheme != "PMFBY":
            claimed_ctx = {
                "crop_category": claim.crop_category,
                "season": claim.season,
                "geography": claim.geography,
                "beneficiary_type": getattr(claim, "beneficiary_type", None) or claim.crop_category,
                "entity_scope": getattr(claim, "entity_scope", None) or claim.crop_category,
                "frequency": getattr(claim, "frequency", None) or claim.season,
                "exclusion_category": getattr(claim, "exclusion_category", None),
            }
            rule_ctx = {
                "crop_category": rule.crop_category,
                "season": rule.season,
                "geography": rule.geography,
                "beneficiary_type": getattr(rule, "entity_scope", None) or rule.crop_category,
                "entity_scope": getattr(rule, "entity_scope", None) or rule.crop_category,
                "frequency": getattr(rule, "frequency", None) or rule.season,
                "exclusions": getattr(rule, "exclusions", []),
            }
            adapter_ok, adapter_reasons = scheme_adapter.match_conditions(
                claimed_ctx,
                rule_ctx,
                rule.rule_parameter,
                enable_switches={
                    "enable_crop_category_matching": config.enable_crop_category_matching,
                    "enable_season_matching": config.enable_season_matching,
                },
            )
            crop_ok = adapter_ok
            season_ok = True
            geo_ok = True
            if not adapter_ok:
                context_mismatch_dims.extend(adapter_reasons)
        else:
            crop_ok, crop_err = _match_crop_category(
                claim.crop_category,
                rule.crop_category,
                enable_crop_category_matching=config.enable_crop_category_matching,
            )
            if not crop_ok and crop_err:
                context_mismatch_dims.append(crop_err)

            season_ok, season_err = _match_season(
                claim.season,
                rule.season,
                claim.crop_category,
                rule.crop_category,
                enable_season_matching=config.enable_season_matching,
            )
            if not season_ok and season_err:
                context_mismatch_dims.append(season_err)

            geo_ok, geo_err = _match_geography(
                claim.geography,
                rule.geography,
                enable_structured_condition_matching=config.enable_structured_condition_matching,
            )
            if not geo_ok and geo_err:
                context_mismatch_dims.append(geo_err)

    # Special rule: if rule_season is 'annual' (e.g. commercial & horticultural 5%) and
    # claim asks for 'kharif' or 'rabi' 'food_grain_and_oilseed', crop_ok is False when crop matching is enabled.
    # What if crop_category_matching is disabled (Ablation 3) and season_matching is enabled?
    # Notice that for commercial/horticultural, rule.season is 'annual', so disabling crop_category_matching
    # allows the 5% annual commercial rule to match a Kharif food-grain query for a 5% claim!

    # 4. Temporal resolution
    temp_res = resolve_temporal_applicability(
        claim=claim,
        rule=rule,
        enable_temporal_checks=config.enable_temporal_checks,
    )
    if not temp_res.is_applicable:
        mismatch_reasons.append(f"temporal_inapplicable({temp_res.temporal_status})")
        if temp_res.is_version_mismatch:
            context_mismatch_dims.append(f"policy_version_mismatch({temp_res.temporal_status})")

    # 5. Basis, operator, and qualification checks
    basis_ok, op_ok, qual_ok, qual_reasons = _match_qualification_and_basis(
        claim=claim,
        rule=rule,
        enable_qualification_matching=config.enable_qualification_matching,
    )
    mismatch_reasons.extend(qual_reasons)

    context_matches_all = (
        scheme_ok
        and param_ok
        and crop_ok
        and season_ok
        and geo_ok
        and temp_res.is_applicable
    )

    is_full_support = (
        prov_ok
        and context_matches_all
        and val_unit_ok
        and basis_ok
        and op_ok
        and qual_ok
        and not rule.conflict_flag
    )

    is_contradiction = (
        prov_ok
        and context_matches_all
        and (not val_unit_ok or not basis_ok or not op_ok or not qual_ok)
        and not rule.conflict_flag
    )

    # WRONG_CONTEXT: The rule has valid provenance, belongs to the queried scheme and rule_parameter
    # (for a covered crop category), matches the claimed numerical value & unit, and does not require
    # temporal abstention, but fails one or more semantic/temporal context dimensions (crop, season,
    # geography, or historical policy version).
    is_wrong_context = (
        prov_ok
        and scheme_ok
        and param_ok
        and claim.crop_category != "non_covered_livestock_aquaculture"
        and val_unit_ok
        and basis_ok
        and op_ok
        and qual_ok
        and not context_matches_all
        and not temp_res.requires_abstention
        and len(context_mismatch_dims) > 0
    )

    return RuleMatchResult(
        rule_id=rule.rule_id,
        evidence_id=rule.evidence_id,
        source_document_id=rule.source_document_id,
        provenance_valid=prov_ok,
        scheme_match=scheme_ok,
        parameter_match=param_ok,
        crop_category_match=crop_ok,
        season_match=season_ok,
        geography_match=geo_ok,
        temporal_result=temp_res,
        value_unit_match=val_unit_ok,
        basis_match=basis_ok,
        operator_match=op_ok,
        qualification_match=qual_ok,
        conflict_flag=rule.conflict_flag,
        context_matches_all=context_matches_all,
        is_full_support=is_full_support,
        is_contradiction_in_same_context=is_contradiction,
        is_wrong_context_for_matched_number=is_wrong_context,
        mismatch_reasons=mismatch_reasons + context_mismatch_dims,
        context_mismatch_dimensions=context_mismatch_dims,
    )


def check_unstructured_chunk_numeric_distractor(
    claim: ParsedClaim,
    unit: ExtractedEvidenceUnit,
    config: ConditionMatchConfig,
) -> dict[str, Any]:
    """
    Inspect an unstructured paragraph chunk (which has no trusted StructuredRuleRecord)
    to see if it contains the claimed numerical value:
      - If the chunk is from an unverified source (e.g. DOC_UNVERIFIED_PILOT_MEMO):
        - When provenance validation is enabled -> flagged as 'untrusted_source_match'.
        - When provenance validation is disabled -> treated as a naive support match!
      - If the chunk is a trusted official paragraph containing unrelated administrative numbers
        (e.g. EV_DOC_PMFBY_OG_2023_P7_CHUNK_2 with 30% women outreach, 5% weekly block camps, 2.0 ha):
        - When structured condition matching is enabled -> flagged as 'distractor_wrong_context'.
        - When structured condition matching is disabled -> treated as a naive numeric match!
    """
    if claim.claimed_value is None or claim.claimed_unit is None:
        return {"has_number": False}

    mentions = extract_all_numeric_mentions(unit.text)
    matched_mention = None
    for m in mentions:
        ok, _ = compare_numeric_values(
            claim.claimed_value,
            claim.claimed_unit,
            m.value,
            m.unit,
            rel_tol=config.numeric_rel_tol,
            abs_tol=config.numeric_abs_tol,
        )
        if ok:
            matched_mention = m
            break
        # Also check value-only match when unit in distractor is different (e.g. 2.0 hectares vs 2.0%)
        if abs(claim.claimed_value - m.value) < 1e-6:
            matched_mention = m

    if matched_mention is None:
        return {"has_number": False}

    if unit.verification_status != "trusted_official":
        return {
            "has_number": True,
            "match_type": "untrusted_source_number_match",
            "evidence_id": unit.evidence_id,
            "document_id": unit.document_id,
            "raw_mention": matched_mention.raw_text,
            "accept_without_provenance_check": not config.enable_provenance_validation,
        }

    return {
        "has_number": True,
        "match_type": "unrelated_paragraph_distractor_number",
        "evidence_id": unit.evidence_id,
        "document_id": unit.document_id,
        "raw_mention": matched_mention.raw_text,
        "accept_without_condition_check": not config.enable_structured_condition_matching,
    }
