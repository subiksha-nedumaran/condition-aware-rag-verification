"""Unit and adversarial tests for temporal applicability and policy-version checking (Phase 6 & 11)."""

from __future__ import annotations

from pathlib import Path

from fieldguard.claim_parser import DeterministicClaimParser
from fieldguard.evidence_store import build_default_evidence_store
from fieldguard.temporal_resolver import resolve_temporal_applicability


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_historical_2023_rule_applied_to_explicit_2023_question() -> None:
    """Adversarial Case 17: Historical 2023 rule applied to an explicit 2023-guideline question."""
    store = build_default_evidence_store(PROJECT_ROOT)
    rule_2023 = store.trusted_rules["RULE_OG2023_PREM_KHARIF_FOOD_OILSEED"]
    parser = DeterministicClaimParser()

    claim = parser.parse(
        "Under the 2023 PMFBY operational guidelines, is the maximum farmer premium for Kharif food grains 2.0%?",
        "Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 2.0% of Sum Insured or actuarial rate, whichever is less.",
    )
    res = resolve_temporal_applicability(claim, rule_2023, enable_temporal_checks=True)
    assert res.is_applicable is True
    assert res.temporal_status == "matched_2023_guidelines"


def test_historical_2023_rule_applied_to_current_policy_question_without_verified_current_evidence() -> None:
    """Adversarial Case 16: Historical 2023 rule applied to a current-policy question without verified current evidence."""
    store = build_default_evidence_store(PROJECT_ROOT)
    rule_2023 = store.trusted_rules["RULE_OG2023_PREM_KHARIF_FOOD_OILSEED"]
    parser = DeterministicClaimParser()

    claim = parser.parse(
        "Under the latest current 2026 revised PMFBY operational guidelines, is the maximum farmer premium for Kharif food grains still 2.0%?",
        "Under the latest current 2026 revised PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 2.0% of Sum Insured.",
    )
    res = resolve_temporal_applicability(claim, rule_2023, enable_temporal_checks=True)
    assert res.is_applicable is False
    assert res.requires_abstention is True
    assert res.temporal_status == "unresolved_latest_policy_version"


def test_publication_date_present_effective_date_unknown() -> None:
    """Adversarial Case 19: Publication date present (2025-12-12), effective date unknown — must never infer effective_from."""
    store = build_default_evidence_store(PROJECT_ROOT)
    rule_pib = store.trusted_rules["RULE_PIB2025_WILD_ANIMAL_STATE_COST"]
    parser = DeterministicClaimParser()

    claim = parser.parse(
        "Did the 100.0% State-funded wild animal attack add-on cover in PIB release PRID=2197713 take legal effect on 2025-12-12?",
        "Under PMFBY, the 100.0% State-funded wild animal attack add-on cover announced in PIB release PRID=2197713 has a verified effective start date of 2025-12-12.",
    )
    res = resolve_temporal_applicability(claim, rule_pib, enable_temporal_checks=True)
    assert res.is_applicable is False
    assert res.requires_abstention is True
    assert res.temporal_status == "unresolved_effective_date_not_inferred_from_publication"


def test_effective_date_mismatch_and_version_swap_2016_vs_2023() -> None:
    """Adversarial Case 18: Applying a 2016 historical rule to a 2023 guideline question yields version mismatch."""
    store = build_default_evidence_store(PROJECT_ROOT)
    rule_2016 = store.trusted_rules["RULE_OG2016_HIST_LOANEE_MANDATORY_RATE"]
    parser = DeterministicClaimParser()

    claim = parser.parse(
        "Under the 2023 revamped PMFBY operational guidelines, is scheme enrolment 100% compulsory for loanee farmers?",
        "Under the 2023 revamped PMFBY operational guidelines, scheme enrolment is 100.0% compulsory for loanee farmers.",
    )
    res = resolve_temporal_applicability(claim, rule_2016, enable_temporal_checks=True)
    assert res.is_applicable is False
    assert res.is_version_mismatch is True
    assert res.temporal_status == "superseded_2016_historical_rule"
