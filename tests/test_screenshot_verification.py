"""User-reported failures, exercised through real retrieval and verification."""

import pytest

from fieldguard.evidence_store import build_pm_kisan_evidence_store
from fieldguard.flagship_schemes_data import build_flagship_scheme_evidence_store
from fieldguard.evaluation.runner import build_all_retrievers
from fieldguard.verifier import FieldGuardVerifier
from fieldguard.numeric_normalizer import extract_all_numeric_mentions
from fieldguard.uploaded_doc_engine import process_uploaded_document


CASES = [
    ("PM_KISAN", "What is the annual benefit provided to eligible farmers under PM-KISAN and how is the amount distributed?",
     "Under PM-KISAN, eligible farmers receive ₹6,000 annually in three equal instalments of ₹2,000 each, distributed every four months."),
    ("PM_JAY", "What is the annual health insurance coverage provided to an eligible family under PM-JAY?",
     "Under Ayushman Bharat PM-JAY, eligible families receive health coverage of ₹5,00,000 per year for secondary and tertiary hospitalisation."),
    ("PMAY_G", "What is the minimum floor area required for a rural house constructed under PMAY-G?",
     "Under PMAY-G, the minimum floor area of a rural house must be 25 square metres."),
    ("PM_KUSUM", "What is the maximum pump capacity supported for standalone solar agriculture pumps under PM-KUSUM?",
     "Under PM-KUSUM Component B, standalone solar agriculture pumps are supported up to a capacity of 7.5 HP."),
    ("PMMY", "What is the maximum loan amount available under the Shishu category of PMMY?",
     "Under PMMY, the Shishu loan category provides loans up to ₹50,000."),
]


@pytest.fixture(scope="module")
def backends():
    result = {}
    for scheme, _, _ in CASES:
        store = build_pm_kisan_evidence_store() if scheme == "PM_KISAN" else build_flagship_scheme_evidence_store(scheme)
        result[scheme] = (FieldGuardVerifier(store), build_all_retrievers(store)["hybrid"])
    return result


def check(backends, scheme, question, claim, top_k=9):
    verifier, retriever = backends[scheme]
    items = [r.to_dict() for r in retriever.retrieve(question + " " + claim, top_k=top_k)]
    return verifier.verify_claim("screenshot", question, claim, items)


@pytest.mark.parametrize("scheme,question,claim", CASES)
@pytest.mark.parametrize("top_k", [5, 9])
def test_screenshot_claims_supported(backends, scheme, question, claim, top_k):
    result = check(backends, scheme, question, claim, top_k)
    assert result.predicted_verdict == "SUPPORTED", result.verification_rationale
    assert result.supporting_evidence_ids
    if scheme == "PM_KISAN":
        assert len(result.component_results) == 4


@pytest.mark.parametrize("old,new", [("₹6,000", "₹7,000"), ("₹2,000", "₹3,000"),
                                         ("three equal", "four equal"), ("four months", "three months")])
def test_each_wrong_component_is_rejected(backends, old, new):
    scheme, question, claim = CASES[0]
    result = check(backends, scheme, question, claim.replace(old, new))
    assert result.predicted_verdict != "SUPPORTED"
    assert any(row["verdict"] != "SUPPORTED" for row in result.component_results)


@pytest.mark.parametrize("index,old,new", [(1, "₹5,00,000", "₹10,00,000"),
    (2, "25 square", "35 square"), (3, "7.5 HP", "10 HP"), (4, "₹50,000", "₹1,00,000")])
def test_wrong_amount_area_capacity_rejected(backends, index, old, new):
    scheme, question, claim = CASES[index]
    assert check(backends, scheme, question, claim.replace(old, new)).predicted_verdict != "SUPPORTED"


@pytest.mark.parametrize("text,value,unit", [("₹6,000", 6000, "rupees"), ("Rs. 1,30,000", 130000, "rupees"),
    ("₹5 lakh", 500000, "rupees"), ("25 sq. metres", 25, "square_metres"),
    ("25 m²", 25, "square_metres"), ("7.5 horsepower", 7.5, "horsepower"),
    ("three equal instalments", 3, "instalments")])
def test_numeric_formats(text, value, unit):
    mentions = extract_all_numeric_mentions(text)
    assert len(mentions) == 1
    assert (mentions[0].value, mentions[0].unit) == (value, unit)


UPLOAD_CLAIM = "Under PMFBY, Mid-Season Adversity coverage is applicable when the expected yield during the crop season is likely to be less than 50% of the normal yield."
UPLOAD_SOURCE = "Mid-Season Adversity: This cover applies when expected yield during the season is likely to be below 50 percent of normal yield."


def upload_check(source, claim, retrieved=True):
    store, units, _ = process_uploaded_document(source.encode(), "guidelines.txt")
    items = [{"evidence_id": u.evidence_id} for u in units] if retrieved else []
    return FieldGuardVerifier(store).verify_claim("upload", "", claim, items)


def test_uploaded_yield_paraphrase():
    result = upload_check(UPLOAD_SOURCE, UPLOAD_CLAIM)
    assert result.predicted_verdict == "SUPPORTED"
    assert result.verification_scope == "uploaded_document_only"


@pytest.mark.parametrize("source,claim", [
    (UPLOAD_SOURCE, UPLOAD_CLAIM.replace("50%", "75%")),
    (UPLOAD_SOURCE, UPLOAD_CLAIM.replace("less than", "more than")),
    (UPLOAD_SOURCE, UPLOAD_CLAIM.replace("normal yield", "threshold yield")),
    (UPLOAD_SOURCE.replace("This cover applies", "This cover applies only in irrigated districts"), UPLOAD_CLAIM),
    ("Mid-Season Adversity: relief is 50 percent of likely claims.", UPLOAD_CLAIM),
    (UPLOAD_SOURCE + "\n\n" + UPLOAD_SOURCE.replace("50 percent", "60 percent"), UPLOAD_CLAIM),
])
def test_uploaded_threshold_constraints(source, claim):
    assert upload_check(source, claim).predicted_verdict != "SUPPORTED"


def test_no_unretrieved_yield_support():
    assert upload_check(UPLOAD_SOURCE, UPLOAD_CLAIM, retrieved=False).predicted_verdict == "UNVERIFIABLE"


def test_nonnumeric_claim_gets_actionable_explanation():
    result = upload_check("Standing crops are covered against drought and floods.",
                          "PMFBY covers standing crops against drought and floods.")
    assert result.predicted_verdict == "UNVERIFIABLE"
    assert "No numerical quantity" in result.verification_rationale
    assert "Search Document Excerpts" in result.verification_rationale
