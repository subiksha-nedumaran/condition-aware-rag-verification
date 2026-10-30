"""Tests for Flagship Scheme Adapters, Evidence Stores, and Dynamic Document Engine.
"""

import pytest
from fieldguard.schemes.registry import (
    get_scheme_adapter,
    list_supported_schemes,
)
from fieldguard.flagship_schemes_data import build_flagship_scheme_evidence_store
from fieldguard.uploaded_doc_engine import (
    process_uploaded_document,
    answer_question_from_uploaded_doc,
)
from fieldguard.verifier import FieldGuardVerifier
from fieldguard.evaluation.runner import build_all_retrievers
from fieldguard.verdicts import Verdict


def test_registry_contains_all_flagship_schemes():
    schemes = list_supported_schemes()
    expected = ["PMFBY", "PM_KISAN", "MGNREGA", "PM_JAY", "PMAY_G", "PM_KUSUM", "PMMY", "CUSTOM_UPLOADED"]
    for s in expected:
        assert s in schemes, f"Scheme {s} missing from registered schemes: {schemes}"


@pytest.mark.parametrize("scheme_code", ["MGNREGA", "PM_JAY", "PMAY_G", "PM_KUSUM", "PMMY"])
def test_flagship_scheme_evidence_store_builds_valid_rules(scheme_code):
    adapter = get_scheme_adapter(scheme_code)
    assert adapter is not None
    assert adapter.scheme_id == scheme_code

    store = build_flagship_scheme_evidence_store(scheme_code)
    assert len(store.evidence_units) >= 1
    assert len(store.trusted_rules) >= 1

    # Verify all rules have required fields
    for rule in store.trusted_rules.values():
        assert rule.scheme == scheme_code
        assert rule.rule_parameter is not None
        assert rule.qualifier is not None


def test_mgnrega_claim_verification():
    store = build_flagship_scheme_evidence_store("MGNREGA")
    verifier = FieldGuardVerifier(evidence_store=store)
    retrievers = build_all_retrievers(store)

    # 1. Supported Claim: 100 days
    query = "How many days of guaranteed wage employment are provided under MGNREGS?"
    ret_items = [r.to_dict() for r in retrievers["hybrid"].retrieve(query, top_k=5)]
    res = verifier.verify_claim(
        claim_id="MGNREGA_TEST_1",
        question=query,
        candidate_claim="Rural households volunteer for 100 days guaranteed wage employment.",
        retrieved_items=ret_items,
    )
    assert res.predicted_verdict == Verdict.SUPPORTED.value

    # 2. Contradicted Claim: 200 days
    res2 = verifier.verify_claim(
        claim_id="MGNREGA_TEST_2",
        question=query,
        candidate_claim="Rural households are entitled to 200 days of guaranteed wage employment.",
        retrieved_items=ret_items,
    )
    assert res2.predicted_verdict == Verdict.CONTRADICTED.value


def test_pmjay_claim_verification():
    store = build_flagship_scheme_evidence_store("PM_JAY")
    verifier = FieldGuardVerifier(evidence_store=store)
    retrievers = build_all_retrievers(store)

    query = "What is the annual health cover provided under Ayushman Bharat PM-JAY?"
    ret_items = [r.to_dict() for r in retrievers["hybrid"].retrieve(query, top_k=5)]
    res = verifier.verify_claim(
        claim_id="PMJAY_TEST_1",
        question=query,
        candidate_claim="Eligible families receive an annual health cover of Rs 500000.",
        retrieved_items=ret_items,
    )
    assert res.predicted_verdict == Verdict.SUPPORTED.value


def test_dynamic_document_ingestion_and_qa():
    sample_policy_text = """
    GOVERNMENT OF INDIA
    NATIONAL DRONE SUBSIDY SCHEME GUIDELINES 2026
    
    1. Financial Assistance:
    Individual farmers from SC/ST and women categories are eligible for financial assistance of 50 percent
    or up to Rs 500000 for purchasing agricultural drones.
    
    2. Operational Subsidy:
    Custom Hiring Centres (CHCs) shall receive a grant of 40 percent of drone cost up to Rs 400000.
    """
    file_bytes = sample_policy_text.encode("utf-8")
    store, units, rules = process_uploaded_document(file_bytes, "drone_guidelines_2026.txt")

    assert len(units) >= 1
    assert len(rules) >= 1

    retrievers = build_all_retrievers(store)
    qa_res = answer_question_from_uploaded_doc("What is the financial assistance for SC/ST and women?", store, retrievers)
    assert "answer" in qa_res
    assert len(qa_res["top_chunks"]) >= 1

    # Verify candidate numerical claim against uploaded document
    verifier = FieldGuardVerifier(evidence_store=store)
    ret_items = [r.to_dict() for r in retrievers["hybrid"].retrieve("subsidy assistance 50 percent", top_k=5)]
    res = verifier.verify_claim(
        claim_id="DYNAMIC_TEST_1",
        question="What is the subsidy percentage?",
        candidate_claim="Eligible farmers receive 50 percent assistance for purchasing drones.",
        retrieved_items=ret_items,
    )
    assert res.predicted_verdict == Verdict.SUPPORTED.value
