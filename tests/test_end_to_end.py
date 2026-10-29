"""End-to-end verification tests including the central PMFBY Kharif 5% vs 2% failure mode."""

from __future__ import annotations

from pathlib import Path

from fieldguard.evaluation.runner import build_all_retrievers
from fieldguard.evidence_store import build_default_evidence_store
from fieldguard.verdicts import Verdict
from fieldguard.verifier import FieldGuardVerifier, VerifierConfig


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_central_use_case_kharif_5_percent_commercial_rate_rejected_as_wrong_context() -> None:
    """
    Central Use Case (Section 2):
    'For Kharif food grains under PMFBY (2023 operational guidelines), is the maximum farmer premium 5%?'
    Baseline A & B falsely accept 5% because 5.0% appears in the same table for commercial/horticultural crops.
    Full FieldGuard must detect WRONG_CONTEXT.
    """
    store = build_default_evidence_store(PROJECT_ROOT)
    retrievers = build_all_retrievers(store)
    hybrid = retrievers["hybrid"]

    q = "Under the 2023 PMFBY operational guidelines, for Kharif food grains, is the maximum farmer premium 5%?"
    c = "Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Kharif food-grain and oilseed crops is 5.0% of Sum Insured or actuarial rate, whichever is less."

    ret_items = [r.to_dict() for r in hybrid.retrieve(f"{q} {c}", top_k=5)]

    # Baseline B (Numeric-Only Match) falsely returns SUPPORTED because 5.0% is in the retrieved table
    verifier_b = FieldGuardVerifier(
        evidence_store=store,
        config=VerifierConfig(config_name="baseline_b_numeric_only", mode="numeric_only"),
    )
    pred_b = verifier_b.verify_claim("CENTRAL_B", q, c, ret_items)
    assert pred_b.predicted_verdict == Verdict.SUPPORTED.value

    # Full FieldGuard returns WRONG_CONTEXT
    verifier_fg = FieldGuardVerifier(
        evidence_store=store,
        config=VerifierConfig(config_name="fieldguard_full", mode="fieldguard"),
    )
    pred_fg = verifier_fg.verify_claim("CENTRAL_FG", q, c, ret_items)
    assert pred_fg.predicted_verdict == Verdict.WRONG_CONTEXT.value
    assert any("crop_category_mismatch" in m for m in pred_fg.context_mismatch)


def test_paraphrased_claim_with_identical_meaning() -> None:
    """Adversarial Case 23: Paraphrased claim with identical meaning is verified as SUPPORTED."""
    store = build_default_evidence_store(PROJECT_ROOT)
    retrievers = build_all_retrievers(store)
    hybrid = retrievers["hybrid"]
    verifier = FieldGuardVerifier(evidence_store=store)

    q = "According to the 2023 PMFBY operational guidelines, is the farmer's premium contribution for Kharif cereals, pulses, and oilseeds capped at two percent?"
    c = "According to the 2023 PMFBY operational guidelines, a farmer growing Kharif food grains or oilseeds pays at most two percent of the Sum Insured or the actuarial rate, whichever is lower."

    ret_items = [r.to_dict() for r in hybrid.retrieve(f"{q} {c}", top_k=5)]
    pred = verifier.verify_claim("PARAPHRASE_01", q, c, ret_items)
    assert pred.predicted_verdict == Verdict.SUPPORTED.value


def test_multi_number_sentence_where_only_one_number_applies() -> None:
    """Adversarial Case 25: Multi-number sentence (2.0% Kharif, 1.5% Rabi, 5.0% commercial in one paragraph)."""
    store = build_default_evidence_store(PROJECT_ROOT)
    verifier = FieldGuardVerifier(evidence_store=store)
    retrievers = build_all_retrievers(store)

    q = "Under the 2023 PMFBY operational guidelines, is the maximum farmer premium for Rabi food-grain and oilseed crops 1.5%?"
    c = "Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Rabi food-grain and oilseed crops is 1.5% of Sum Insured or actuarial rate, whichever is less."
    ret_items = [r.to_dict() for r in retrievers["hybrid"].retrieve(f"{q} {c}", top_k=5)]

    pred_support = verifier.verify_claim("MULTI_NUM_SUPPORT", q, c, ret_items)
    assert pred_support.predicted_verdict == Verdict.SUPPORTED.value

    q_wrong = "Under the 2023 PMFBY operational guidelines, is the maximum farmer premium for Rabi food-grain and oilseed crops 2.0%?"
    c_wrong = "Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Rabi food-grain and oilseed crops is 2.0% of Sum Insured or actuarial rate, whichever is less."
    pred_wrong = verifier.verify_claim("MULTI_NUM_WRONG", q_wrong, c_wrong, ret_items)
    assert pred_wrong.predicted_verdict == Verdict.WRONG_CONTEXT.value
