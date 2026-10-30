"""Unit tests for Stage 2 schema generalization and scheme registry."""

from __future__ import annotations

import pytest

from fieldguard.evidence_schema import (
    GenericEvidenceRecord,
    StructuredRuleRecord,
    validate_generic_evidence_record,
    validate_structured_rule_record,
)
from fieldguard.schemes import (
    PMFBYScheme,
    PMKisanScheme,
    SchemeRegistry,
    get_scheme_adapter,
)


def test_generic_evidence_record_lifecycle():
    rec = GenericEvidenceRecord(
        rule_id="RULE_PMKISAN_ANNUAL_6K",
        evidence_id="EV_DOC_PMKISAN_OG_P5_S2",
        scheme="PM_KISAN",
        rule_parameter="annual_income_support",
        primary_value=6000.0,
        unit="rupees",
        basis="per_eligible_farmer_family",
        qualifier="payable_in_three_equal_instalments_of_2000",
        requires_qualifier_for_unconditional_claim=True,
        entity_scope="all_landholding_farmers",
        conditions={"frequency": "annual", "eligible_landholding": "cultivable"},
        exclusions=["institutional_landholder", "income_tax_payee"],
        frequency="annual",
        geography="all_india",
        source_document_id="DOC_PMKISAN_OG_2020",
        document_version="revised_guidelines_2020",
        policy_era="universal_landholder_2019_onwards",
        section="Section 2: Scheme Modalities",
        physical_pdf_page=5,
        verification_status="trusted_official",
    )

    valid, errors = validate_generic_evidence_record(rec)
    assert valid, f"Validation failed: {errors}"
    assert rec.maximum_rate == 6000.0
    assert rec.conditions["frequency"] == "annual"

    # Test conversion to StructuredRuleRecord
    legacy = rec.to_structured_rule_record()
    assert legacy.rule_id == "RULE_PMKISAN_ANNUAL_6K"
    assert legacy.maximum_rate == 6000.0
    assert legacy.scheme == "PM_KISAN"
    assert legacy.entity_scope == "all_landholding_farmers"

    # Test conversion back to GenericEvidenceRecord
    roundtrip = legacy.to_generic_record()
    assert roundtrip.rule_id == rec.rule_id
    assert roundtrip.primary_value == rec.primary_value
    assert roundtrip.unit == rec.unit


def test_structured_rule_record_to_generic_conversion():
    rule = StructuredRuleRecord(
        rule_id="RULE_OG2023_KHARIF_FOODGRAIN_2PCT",
        evidence_id="EV_DOC_PMFBY_OG_2023_P5_TBL_OG2023_PREMIUM_RATES_R1",
        scheme="PMFBY",
        rule_parameter="farmer_premium_rate",
        season="kharif",
        crop_category="food_grain_and_oilseed",
        geography="all_india",
        minimum_value=None,
        maximum_rate=2.0,
        allowed_values=[2.0],
        numeric_operator="le",
        unit="percent",
        basis="sum_insured",
        qualifier="or_actuarial_rate_whichever_is_less",
        requires_qualifier_for_unconditional_claim=True,
        source_document_id="DOC_PMFBY_OG_2023",
        document_version="2023_revamped_guidelines",
        policy_era="guidelines_2023",
        publication_date="2023-01-01",
        section="Section IX (Table 1)",
        physical_pdf_page=5,
        printed_page="3",
        table_id="TBL_OG2023_PREMIUM_RATES",
        row_id="TBL_OG2023_PREMIUM_RATES_R1",
        effective_from="2020-04-01",
        effective_to=None,
        verification_status="trusted_official",
    )

    generic = rule.to_generic_record()
    assert generic.rule_id == "RULE_OG2023_KHARIF_FOODGRAIN_2PCT"
    assert generic.primary_value == 2.0
    assert generic.conditions["season"] == "kharif"
    assert generic.conditions["crop_category"] == "food_grain_and_oilseed"
    assert generic.crop_category == "food_grain_and_oilseed"
    assert generic.season == "kharif"


def test_scheme_registry_lookups():
    # Primary IDs
    assert SchemeRegistry.get_scheme("PMFBY") is not None
    assert SchemeRegistry.get_scheme("PM_KISAN") is not None

    # Aliases
    assert SchemeRegistry.get_scheme("pmfby") is not None
    assert SchemeRegistry.get_scheme("pm-kisan") is not None
    assert SchemeRegistry.get_scheme("pmkisan") is not None
    assert SchemeRegistry.get_scheme("PM-KISAN") is not None
    assert SchemeRegistry.get_scheme("kisan_samman_nidhi") is not None

    # Unsupported scheme returns None
    assert SchemeRegistry.get_scheme("UNKNOWN_SCHEME_XYZ") is None

    # List supported schemes
    schemes = SchemeRegistry.list_supported_schemes()
    assert "PMFBY" in schemes
    assert "PM_KISAN" in schemes


def test_pm_kisan_scheme_adapter():
    scheme = get_scheme_adapter("PM_KISAN")
    assert isinstance(scheme, PMKisanScheme)

    # Context validation
    valid_ctx = scheme.validate_claim_context(
        "annual_income_support",
        {"beneficiary_type": "all_landholding_farmers"},
    )
    assert valid_ctx.is_valid

    invalid_ctx = scheme.validate_claim_context(
        "annual_income_support",
        {},
    )
    assert not invalid_ctx.is_valid
    assert "beneficiary_type" in invalid_ctx.missing_fields

    # Condition matching: tenant farmer mismatch
    match_ok, reasons = scheme.match_conditions(
        claimed_context={"beneficiary_type": "tenant_farmer"},
        rule_context={"beneficiary_type": "all_landholding_farmers"},
        rule_parameter="annual_income_support",
    )
    assert not match_ok
    assert any("ineligible_beneficiary_mismatch" in r for r in reasons)

    # Condition matching: income tax payee exclusion
    match_ok, reasons = scheme.match_conditions(
        claimed_context={"beneficiary_type": "all_landholding_farmers", "exclusion_category": "income_tax_payee"},
        rule_context={"beneficiary_type": "all_landholding_farmers"},
        rule_parameter="annual_income_support",
    )
    assert not match_ok
    assert any("exclusion_violation" in r for r in reasons)

