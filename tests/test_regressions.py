"""Regression tests ensuring all 25 adversarial failure modes remain guarded (Phase 11)."""

from __future__ import annotations

from pathlib import Path

from fieldguard.evaluation.runner import build_all_retrievers
from fieldguard.evidence_store import build_default_evidence_store
from fieldguard.verdicts import Verdict
from fieldguard.verifier import FieldGuardVerifier


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_regression_pib_dec2025_announcement_does_not_support_unannounced_premium_rate_change() -> None:
    """
    PIB PRID=2197713 (Dec 2025) announces wild animal attack add-on cover (100% State subsidy) and
    inundation SOPs, NOT a change in Kharif food-grain maximum farmer premium to 1.0%.
    """
    store = build_default_evidence_store(PROJECT_ROOT)
    retrievers = build_all_retrievers(store)
    verifier = FieldGuardVerifier(evidence_store=store)

    q = "Under the latest current 2026 revised PMFBY operational guidelines (following the December 2025 revision), is the maximum farmer premium for Kharif food grains still 2.0%?"
    c = "Under the latest current 2026 revised PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 2.0% of Sum Insured."
    ret_items = [r.to_dict() for r in retrievers["hybrid"].retrieve(f"{q} {c}", top_k=5)]
    pred = verifier.verify_claim("REG_PIB_01", q, c, ret_items)
    assert pred.predicted_verdict == Verdict.UNVERIFIABLE.value


def test_regression_pib_dec2025_supports_100_percent_state_subsidy_for_wild_animal_addon() -> None:
    """PIB PRID=2197713 explicitly supports 100.0% State subsidy for wild animal attack add-on cover."""
    store = build_default_evidence_store(PROJECT_ROOT)
    retrievers = build_all_retrievers(store)
    verifier = FieldGuardVerifier(evidence_store=store)

    q = "According to the December 2025 PIB press release (PRID=2197713), what share of the cost is borne by the State Government when notifying wild animal attack as an add-on cover under PMFBY?"
    c = "According to the December 2025 PIB press release (PRID=2197713), wild animal attack add-on cover under PMFBY is implemented 100.0% at the cost of the respective State Government."
    ret_items = [r.to_dict() for r in retrievers["hybrid"].retrieve(f"{q} {c}", top_k=5)]
    pred = verifier.verify_claim("REG_PIB_02", q, c, ret_items)
    assert pred.predicted_verdict == Verdict.SUPPORTED.value


def test_regression_same_number_multiple_times_on_page_table_row_disambiguation() -> None:
    """Adversarial Cases 7 & 8: Distractor numbers in other table rows on the same page do not cause false support."""
    store = build_default_evidence_store(PROJECT_ROOT)
    retrievers = build_all_retrievers(store)
    verifier = FieldGuardVerifier(evidence_store=store)

    q = "Under the 2023 PMFBY operational guidelines, is the Central Government premium subsidy capped at 30.0% actuarial rate for irrigated areas?"
    c = "Under the 2023 PMFBY operational guidelines, Central Government premium subsidy is capped for actuarial premium rates up to 30.0% for irrigated areas."
    ret_items = [r.to_dict() for r in retrievers["hybrid"].retrieve(f"{q} {c}", top_k=5)]
    pred = verifier.verify_claim("REG_TBL_ROW_01", q, c, ret_items)
    assert pred.predicted_verdict == Verdict.WRONG_CONTEXT.value
