"""Unit and adversarial tests for condition matching (crop, season, geography, qualification)."""

from __future__ import annotations

from pathlib import Path

from fieldguard.claim_parser import DeterministicClaimParser
from fieldguard.condition_matcher import ConditionMatchConfig, evaluate_rule_against_claim
from fieldguard.evidence_store import build_default_evidence_store


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_correct_number_wrong_crop_category() -> None:
    """Adversarial Case 1: Correct number (5%), wrong crop category (Kharif food grains vs commercial)."""
    store = build_default_evidence_store(PROJECT_ROOT)
    comm_rule = store.trusted_rules["RULE_OG2023_PREM_ANNUAL_COMM_HORT"]
    parser = DeterministicClaimParser()

    claim = parser.parse(
        "Under the 2023 PMFBY operational guidelines, for Kharif food grains, is the maximum farmer premium 5%?",
        "Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 5.0% of Sum Insured or actuarial rate, whichever is less.",
    )
    res = evaluate_rule_against_claim(claim, comm_rule, ConditionMatchConfig())
    assert res.value_unit_match is True
    assert res.crop_category_match is False
    assert res.is_wrong_context_for_matched_number is True
    assert any("crop_category_mismatch" in d for d in res.context_mismatch_dimensions)


def test_correct_number_wrong_season() -> None:
    """Adversarial Case 2: Correct number (1.5% Rabi rate), wrong season (applied to Kharif)."""
    store = build_default_evidence_store(PROJECT_ROOT)
    rabi_rule = store.trusted_rules["RULE_OG2023_PREM_RABI_FOOD_OILSEED"]
    parser = DeterministicClaimParser()

    claim = parser.parse(
        "Under the 2023 PMFBY operational guidelines, for Kharif food grains, is the maximum farmer premium 1.5%?",
        "Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 1.5% of Sum Insured or actuarial rate, whichever is less.",
    )
    res = evaluate_rule_against_claim(claim, rabi_rule, ConditionMatchConfig())
    assert res.value_unit_match is True
    assert res.season_match is False
    assert res.is_wrong_context_for_matched_number is True
    assert any("season_mismatch" in d for d in res.context_mismatch_dimensions)


def test_correct_number_wrong_geography() -> None:
    """Adversarial Case 3: Correct number (90% NER subsidy share), wrong geography (General States)."""
    store = build_default_evidence_store(PROJECT_ROOT)
    ner_rule = store.trusted_rules["RULE_OG2023_SUBSIDY_SHARE_NER_STATES"]
    parser = DeterministicClaimParser()

    claim = parser.parse(
        "Under the 2023 PMFBY operational guidelines, is the Central Government's share of normal premium subsidy 90.0% in General States?",
        "Under the 2023 PMFBY operational guidelines, the Central Government's share of normal premium subsidy is 90.0% in General States.",
    )
    res = evaluate_rule_against_claim(claim, ner_rule, ConditionMatchConfig())
    assert res.value_unit_match is True
    assert res.geography_match is False
    assert res.is_wrong_context_for_matched_number is True
    assert any("geography_mismatch" in d for d in res.context_mismatch_dimensions)


def test_missing_and_contradicted_qualification() -> None:
    """Adversarial Cases 5 & 6: Flat unconditional rate vs 'whichever is higher' qualification violations."""
    store = build_default_evidence_store(PROJECT_ROOT)
    kharif_rule = store.trusted_rules["RULE_OG2023_PREM_KHARIF_FOOD_OILSEED"]
    rabi_rule = store.trusted_rules["RULE_OG2023_PREM_RABI_FOOD_OILSEED"]
    parser = DeterministicClaimParser()

    claim_flat = parser.parse(
        "Under the 2023 PMFBY operational guidelines, does a Kharif food-grain farmer always pay a flat 2.0% premium even if the actuarial rate is 1.2%?",
        "Under the 2023 PMFBY operational guidelines, a Kharif food-grain farmer always pays a fixed 2.0% of Sum Insured even when the actuarial rate is lower at 1.2%.",
    )
    res_flat = evaluate_rule_against_claim(claim_flat, kharif_rule, ConditionMatchConfig())
    assert res_flat.qualification_match is False
    assert res_flat.is_contradiction_in_same_context is True

    claim_higher = parser.parse(
        "For Rabi food-grain crops under the 2023 PMFBY guidelines, is the farmer premium 1.5% of Sum Insured or the actuarial rate, whichever is higher?",
        "Under the 2023 PMFBY guidelines, the farmer premium for Rabi food-grain crops is 1.5% of Sum Insured or the actuarial rate, whichever is higher.",
    )
    res_higher = evaluate_rule_against_claim(claim_higher, rabi_rule, ConditionMatchConfig())
    assert res_higher.qualification_match is False
    assert res_higher.is_contradiction_in_same_context is True
