"""Tests for the four mandatory verdicts and VerificationPrediction schema (Phase 3 & 6)."""

from __future__ import annotations

from fieldguard.verdicts import (
    ALL_VERDICTS,
    VERDICT_DEFINITIONS,
    Verdict,
    is_abstention_verdict,
)
from fieldguard.verifier import VerificationPrediction


def test_four_mandatory_verdicts_and_definitions() -> None:
    """Verify the exact 4 verdicts exist with non-empty definitions."""
    assert ALL_VERDICTS == ("SUPPORTED", "CONTRADICTED", "WRONG_CONTEXT", "UNVERIFIABLE")
    for v_str in ALL_VERDICTS:
        assert v_str in VERDICT_DEFINITIONS
        assert len(VERDICT_DEFINITIONS[v_str]) > 20

    assert is_abstention_verdict("UNVERIFIABLE") is True
    assert is_abstention_verdict("SUPPORTED") is False
    assert is_abstention_verdict("WRONG_CONTEXT") is False
    assert is_abstention_verdict("CONTRADICTED") is False


def test_verification_prediction_serialization() -> None:
    res = VerificationPrediction(
        claim_id="CLM_TEST_001",
        predicted_verdict=Verdict.WRONG_CONTEXT.value,
        parsed_claim={"scheme": "PMFBY", "claimed_value": 5.0},
        matched_evidence_ids=["EV_DOC_PMFBY_OG_2023_P4_TBL_OG2023_PREMIUM_RATES_R3"],
        supporting_evidence_ids=[],
        contradicting_evidence_ids=["EV_DOC_PMFBY_OG_2023_P4_TBL_OG2023_PREMIUM_RATES_R3"],
        context_mismatch=["crop_category_mismatch"],
        temporal_status="matched_2023_guidelines",
        verification_rationale="Claim applies 5.0% commercial rate to Kharif food grains.",
        abstention_reason=None,
        retrieval_method="hybrid",
        latency_ms=1.25,
        verification_latency_ms=0.45,
        retrieval_latency_ms=0.80,
        config_name="fieldguard_full",
    )
    d = res.to_dict()
    assert d["claim_id"] == "CLM_TEST_001"
    assert d["predicted_verdict"] == "WRONG_CONTEXT"
    assert d["context_mismatch"] == ["crop_category_mismatch"]
