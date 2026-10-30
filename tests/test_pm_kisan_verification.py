"""End-to-end verification tests for PM-KISAN under the generalized FieldGuard framework."""

from __future__ import annotations

import pytest

from fieldguard.evidence_store import build_pm_kisan_evidence_store
from fieldguard.verdicts import Verdict
from fieldguard.verifier import FieldGuardVerifier, VerifierConfig


@pytest.fixture(scope="module")
def pm_kisan_verifier():
    store = build_pm_kisan_evidence_store()
    verifier = FieldGuardVerifier(evidence_store=store, config=VerifierConfig())
    return verifier, store


def test_pm_kisan_annual_benefit_supported(pm_kisan_verifier):
    verifier, store = pm_kisan_verifier
    question = "Under PM-KISAN, what is the annual income support provided to eligible farmer families?"
    claim = "Under PM-KISAN, eligible landholding farmer families receive an annual financial benefit of Rs 6000."
    retrieved = [
        {"evidence_id": "EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R4", "retrieval_score": 0.95},
        {"evidence_id": "EV_DOC_PMKISAN_OG_2020_P2_CHUNK_1", "retrieval_score": 0.85},
    ]

    pred = verifier.verify_claim(
        claim_id="TEST_PMK_001",
        question=question,
        candidate_claim=claim,
        retrieved_items=retrieved,
    )

    assert pred.predicted_verdict == Verdict.SUPPORTED.value
    assert "EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R4" in pred.supporting_evidence_ids


def test_pm_kisan_instalment_amount_supported(pm_kisan_verifier):
    verifier, store = pm_kisan_verifier
    question = "What is the instalment amount disbursed per period under PM-KISAN?"
    claim = "Under PM-KISAN, each four-monthly instalment is Rs 2000 per eligible farmer family."
    retrieved = [
        {"evidence_id": "EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R1", "retrieval_score": 0.92},
    ]

    pred = verifier.verify_claim(
        claim_id="TEST_PMK_002",
        question=question,
        candidate_claim=claim,
        retrieved_items=retrieved,
    )

    assert pred.predicted_verdict == Verdict.SUPPORTED.value
    assert "EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R1" in pred.supporting_evidence_ids


def test_pm_kisan_tenant_farmer_wrong_context(pm_kisan_verifier):
    verifier, store = pm_kisan_verifier
    question = "Under PM-KISAN, what is the annual financial assistance for tenant farmers?"
    claim = "Tenant farmers receive Rs 6000 per year under the PM-KISAN scheme."
    # The retriever retrieves the 6000 rule, but it applies only to landholding farmers, not tenant farmers
    retrieved = [
        {"evidence_id": "EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R4", "retrieval_score": 0.90},
    ]

    pred = verifier.verify_claim(
        claim_id="TEST_PMK_003",
        question=question,
        candidate_claim=claim,
        retrieved_items=retrieved,
    )

    assert pred.predicted_verdict == Verdict.WRONG_CONTEXT.value
    assert any("ineligible_beneficiary_mismatch" in m for m in pred.context_mismatch)


def test_pm_kisan_instalment_frequency_mismatch_wrong_context(pm_kisan_verifier):
    verifier, store = pm_kisan_verifier
    question = "What is the amount received per instalment under PM-KISAN?"
    # Claim asserts Rs 6000 per instalment (matching the annual total number, but wrong periodicity)
    claim = "Under PM-KISAN, each instalment is Rs 6000."
    retrieved = [
        {"evidence_id": "EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R4", "retrieval_score": 0.91},
        {"evidence_id": "EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R1", "retrieval_score": 0.89},
    ]

    pred = verifier.verify_claim(
        claim_id="TEST_PMK_004",
        question=question,
        candidate_claim=claim,
        retrieved_items=retrieved,
    )

    # 6000 per instalment contradicts the 2000 instalment rule or matches the annual rule with wrong frequency context
    assert pred.predicted_verdict in (Verdict.WRONG_CONTEXT.value, Verdict.CONTRADICTED.value)


def test_pm_kisan_contradicted_annual_amount(pm_kisan_verifier):
    verifier, store = pm_kisan_verifier
    question = "What is the total annual financial support under PM-KISAN?"
    claim = "Under PM-KISAN, eligible landholding farmer families receive Rs 12000 per year."
    retrieved = [
        {"evidence_id": "EV_DOC_PMKISAN_OG_2020_P2_TBL_PMKISAN_BENEFIT_SCHEDULE_R4", "retrieval_score": 0.94},
    ]

    pred = verifier.verify_claim(
        claim_id="TEST_PMK_005",
        question=question,
        candidate_claim=claim,
        retrieved_items=retrieved,
    )

    assert pred.predicted_verdict == Verdict.CONTRADICTED.value


def test_pm_kisan_unverifiable_unsupported_benefit(pm_kisan_verifier):
    verifier, store = pm_kisan_verifier
    question = "Under PM-KISAN, what is the tractor subsidy rate provided to farmers?"
    claim = "Under PM-KISAN, farmers receive a tractor purchase subsidy of 50 percent."
    # Retrieved chunks do not contain a tractor subsidy rule for PM-KISAN
    retrieved = [
        {"evidence_id": "EV_DOC_PMKISAN_OG_2020_P1_CHUNK_1", "retrieval_score": 0.40},
    ]

    pred = verifier.verify_claim(
        claim_id="TEST_PMK_006",
        question=question,
        candidate_claim=claim,
        retrieved_items=retrieved,
    )

    assert pred.predicted_verdict == Verdict.UNVERIFIABLE.value


def test_pm_kisan_statutory_exclusion_supported(pm_kisan_verifier):
    verifier, store = pm_kisan_verifier
    question = "Are institutional landholders eligible to receive benefits under PM-KISAN?"
    claim = "All institutional landholders are statutorily excluded (Rs 0 benefit) from PM-KISAN."
    retrieved = [
        {"evidence_id": "EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R1", "retrieval_score": 0.95},
    ]

    pred = verifier.verify_claim(
        claim_id="TEST_PMK_007",
        question=question,
        candidate_claim=claim,
        retrieved_items=retrieved,
    )

    assert pred.predicted_verdict == Verdict.SUPPORTED.value
    assert "EV_DOC_PMKISAN_OG_2020_P4_TBL_PMKISAN_EXCLUSIONS_R1" in pred.supporting_evidence_ids


def test_pm_kisan_tenant_ineligible_zero_benefit_supported(pm_kisan_verifier):
    verifier, store = pm_kisan_verifier
    question = "Are tenant farmers without land ownership title eligible for financial benefits under PM-KISAN?"
    claim = "Tenant farmers without cultivable land ownership are ineligible (Rs 0 benefit) under PM-KISAN."
    retrieved = [
        {"evidence_id": "EV_DOC_PMKISAN_OG_2020_P3_CHUNK_2", "retrieval_score": 0.94},
    ]

    pred = verifier.verify_claim(
        claim_id="TEST_PMK_008",
        question=question,
        candidate_claim=claim,
        retrieved_items=retrieved,
    )

    assert pred.predicted_verdict == Verdict.SUPPORTED.value
    assert "EV_DOC_PMKISAN_OG_2020_P3_CHUNK_2" in pred.supporting_evidence_ids


def test_pm_kisan_aadhaar_dbt_supported(pm_kisan_verifier):
    verifier, store = pm_kisan_verifier
    question = "How are financial benefits delivered to beneficiary bank accounts under PM-KISAN?"
    claim = "Benefits under PM-KISAN are transferred 100 percent electronically via Aadhaar Payment Bridge System (APBS)."
    retrieved = [
        {"evidence_id": "EV_DOC_PMKISAN_OG_2020_P5_CHUNK_1", "retrieval_score": 0.96},
    ]

    pred = verifier.verify_claim(
        claim_id="TEST_PMK_009",
        question=question,
        candidate_claim=claim,
        retrieved_items=retrieved,
    )

    assert pred.predicted_verdict == Verdict.SUPPORTED.value
    assert "EV_DOC_PMKISAN_OG_2020_P5_CHUNK_1" in pred.supporting_evidence_ids

