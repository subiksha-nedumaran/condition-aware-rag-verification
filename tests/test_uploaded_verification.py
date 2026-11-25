"""Regression coverage for document-only verification and its trust boundary."""

import pytest

from fieldguard.uploaded_doc_engine import process_uploaded_document
from fieldguard.verifier import FieldGuardVerifier, VerifierConfig


def verify(document, claim, *, selected=None, config=None):
    store, units, rules = process_uploaded_document(document.encode(), "policy.txt")
    items = [{"evidence_id": u.evidence_id, "retrieval_score": 1.0}
             for i, u in enumerate(units) if selected is None or i in selected]
    prediction = FieldGuardVerifier(store, config).verify_claim("test", "", claim, items)
    return prediction, store, units, rules


@pytest.mark.parametrize("claim,verdict", [
    ("Women receive 50 percent assistance.", "SUPPORTED"),
    ("Men receive 40 percent assistance.", "SUPPORTED"),
    ("Men receive 50 percent assistance.", "CONTRADICTED"),
    ("Women receive 40 percent assistance.", "CONTRADICTED"),
    ("Beneficiaries receive 50 percent assistance.", "UNVERIFIABLE"),
    ("Women do not receive 50 percent assistance.", "UNVERIFIABLE"),
])
def test_beneficiary_conditions(claim, verdict):
    pred, _, _, _ = verify(
        "Women receive 50 percent assistance.\n\nMen receive 40 percent assistance.", claim)
    assert pred.predicted_verdict == verdict
    assert pred.verification_scope == "uploaded_document_only"
    assert "provenance" in pred.verification_rationale


@pytest.mark.parametrize("document,claim", [
    ("Women receive up to 50 percent assistance.", "Women receive 50 percent assistance."),
    ("Women receive 50 percent assistance annually.", "Women receive 50 percent assistance monthly."),
    ("Women in Rajasthan receive 50 percent assistance.", "Women in Kerala receive 50 percent assistance."),
    ("Women receive 50 percent assistance. Only landowners qualify.", "Women receive 50 percent assistance."),
    ("Women receive 50 percent assistance or up to Rs 500000.", "Women receive 50 percent assistance."),
    ("Women | 50 percent", "Women receive 50 percent assistance."),
])
def test_unestablished_conditions_abstain(document, claim):
    pred, _, _, _ = verify(document, claim)
    assert pred.predicted_verdict == "UNVERIFIABLE"
    assert not pred.supporting_evidence_ids


def test_uploads_never_become_trusted_rules_or_invent_dates():
    pred, store, units, rules = verify("Women receive 50 percent assistance.", "Women receive 50 percent assistance.")
    assert pred.predicted_verdict == "SUPPORTED"
    assert not store.trusted_rules
    for record in units + rules:
        assert record.verification_status == "user_uploaded_unverified"
        assert record.publication_date is None
        assert record.effective_from is None
    assert rules[0].conditions["source_passage"] == units[0].text


def test_unretrieved_passage_cannot_establish_support():
    pred, _, _, _ = verify("Women receive 50 percent assistance.\n\nMen receive 40 percent assistance.",
                           "Women receive 50 percent assistance.", selected=[1])
    assert pred.predicted_verdict == "UNVERIFIABLE"


def test_conflict_even_outside_retrieval_abstains():
    pred, _, _, _ = verify("Women receive 50 percent assistance.\n\nWomen receive 40 percent assistance.",
                           "Women receive 50 percent assistance.", selected=[0])
    assert pred.predicted_verdict == "UNVERIFIABLE"


def test_ablation_cannot_bypass_upload_guard():
    pred, _, _, _ = verify("Women receive 50 percent assistance.", "Men receive 50 percent assistance.",
                           config=VerifierConfig(mode="numeric_only", enable_evidence_sufficiency=False,
                                                 enable_provenance_validation=False))
    assert pred.predicted_verdict == "UNVERIFIABLE"


def test_empty_retrieval_retains_document_scope():
    pred, _, _, _ = verify("Women receive 50 percent assistance.",
                           "Women receive 50 percent assistance.", selected=[])
    assert pred.predicted_verdict == "UNVERIFIABLE"
    assert pred.verification_scope == "uploaded_document_only"


@pytest.mark.parametrize("document,claim", [
    ("Farmers receive 3 quarterly instalments.", "Farmers receive 3 equal instalments."),
    ("Farmers receive 3 subsidized solar pumps.", "Farmers receive 3 pumps."),
    ("Women receive at least 50 percent assistance.", "Women receive at most 50 percent assistance."),
    ("Women receive 50 percent assistance or the actual cost, whichever is less.",
     "Women receive 50 percent assistance or the actual cost, whichever is higher."),
    ("Registered women receive 50 percent assistance.", "Women receive 50 percent assistance."),
    ("Women receive Rs 5000 per household annually.", "Women receive Rs 5000 per person annually."),
])
def test_condition_changes_inside_and_outside_numeric_mentions(document, claim):
    pred, _, _, _ = verify(document, claim)
    assert pred.predicted_verdict == "UNVERIFIABLE"


@pytest.mark.parametrize("text", [
    "Women receive up to 50 percent assistance.",
    "Women receive at least 50 percent assistance.",
    "Women receive 50 percent assistance or the actual cost, whichever is less.",
    "Registered women in Rajasthan receive Rs 5000 per household annually.",
    "Farmers receive 3 quarterly instalments.",
])
def test_complete_qualified_passages_remain_supported(text):
    pred, _, _, _ = verify(text, text)
    assert pred.predicted_verdict == "SUPPORTED"
    assert pred.supporting_evidence_ids
