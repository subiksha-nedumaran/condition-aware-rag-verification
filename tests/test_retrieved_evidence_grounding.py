"""Tests for retrieved evidence grounding, provenance checks, and conflict detection (Phase 4, 6 & 11)."""

from __future__ import annotations

from pathlib import Path

import pytest

from fieldguard.evidence_schema import StructuredRuleRecord
from fieldguard.evidence_store import build_default_evidence_store
from fieldguard.source_manifest import load_source_manifest
from fieldguard.table_extraction import extract_table_units_from_page_tables
from fieldguard.verdicts import Verdict
from fieldguard.verifier import FieldGuardVerifier


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_untrusted_source_cannot_produce_supported() -> None:
    """Adversarial Case 20: Untrusted or unverified source document cannot enter trusted store or produce SUPPORTED."""
    store = build_default_evidence_store(PROJECT_ROOT)

    assert len(store.rejected_rules) >= 1
    for r in store.trusted_rules.values():
        assert r.verification_status == "trusted_official"

    untrusted_rule = StructuredRuleRecord(
        rule_id="RULE_FAKE_UNVERIFIED",
        evidence_id="EV_DOC_UNVERIFIED_PILOT_MEMO_P1_CHUNK_1",
        scheme="PMFBY",
        rule_parameter="farmer_premium_rate",
        season="kharif",
        crop_category="commercial_and_horticultural",
        geography="all_india",
        minimum_value=None,
        maximum_rate=1.0,
        allowed_values=None,
        numeric_operator="le",
        unit="percent",
        basis="sum_insured",
        qualifier="or_actuarial_rate_whichever_is_less",
        requires_qualifier_for_unconditional_claim=True,
        source_document_id="DOC_UNVERIFIED_PILOT_MEMO",
        document_version="unverified_draft_v0",
        policy_era="unverified_draft",
        publication_date=None,
        section="Draft Note",
        physical_pdf_page=1,
        printed_page="1",
        table_id=None,
        row_id=None,
        effective_from=None,
        effective_to=None,
        verification_status="unverified_source",
    )
    with pytest.raises(ValueError, match="Rejected malformed/untrusted rule"):
        store.add_structured_rule(untrusted_rule, strict=True)

    verifier = FieldGuardVerifier(evidence_store=store)
    unv_unit = store.evidence_units["EV_DOC_UNVERIFIED_PILOT_MEMO_P1_CHUNK_1"]
    ret_items = [
        {
            "evidence_id": unv_unit.evidence_id,
            "retrieval_score": 0.95,
            "rank": 1,
            "text": unv_unit.text,
        }
    ]
    pred = verifier.verify_claim(
        claim_id="TEST_UNVERIFIED",
        question="Based on the working group draft note, is the maximum farmer premium for Kharif perennial horticultural crops 3.5% of Sum Insured under PMFBY?",
        candidate_claim="Under PMFBY, the maximum farmer premium for Kharif perennial horticultural crops is 3.5% of Sum Insured.",
        retrieved_items=ret_items,
    )
    assert pred.predicted_verdict == Verdict.UNVERIFIABLE.value


def test_missing_retrieved_evidence_returns_unverifiable() -> None:
    """Adversarial Case 14: Missing retrieved evidence returns UNVERIFIABLE, never SUPPORTED or CONTRADICTED."""
    store = build_default_evidence_store(PROJECT_ROOT)
    verifier = FieldGuardVerifier(evidence_store=store)

    pred = verifier.verify_claim(
        claim_id="TEST_EMPTY_RET",
        question="Under the 2023 PMFBY operational guidelines, is the maximum farmer premium for Kharif food grains 2.0%?",
        candidate_claim="Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 2.0% of Sum Insured or actuarial rate, whichever is less.",
        retrieved_items=[],
    )
    assert pred.predicted_verdict == Verdict.UNVERIFIABLE.value


def test_conflicting_retrieved_evidence_returns_unverifiable() -> None:
    """Adversarial Case 15: Conflicting retrieved evidence on betelvine pilot addendum returns UNVERIFIABLE."""
    store = build_default_evidence_store(PROJECT_ROOT)
    verifier = FieldGuardVerifier(evidence_store=store)

    ev_a = store.evidence_units["EV_DOC_PMFBY_STATE_ADDENDUM_CONFLICT_P1_TBL_ADDENDUM_BETELVINE_CONFLICT_R1"]
    ev_b = store.evidence_units["EV_DOC_PMFBY_STATE_ADDENDUM_CONFLICT_P1_TBL_ADDENDUM_BETELVINE_CONFLICT_R2"]
    ret_items = [
        {"evidence_id": ev_a.evidence_id, "retrieval_score": 0.95, "rank": 1, "text": ev_a.text},
        {"evidence_id": ev_b.evidence_id, "retrieval_score": 0.92, "rank": 2, "text": ev_b.text},
    ]
    pred = verifier.verify_claim(
        claim_id="TEST_CONFLICT",
        question="Under the 2023 PMFBY pilot addendum for Kharif perennial betelvine, is the maximum farmer premium 3.0% of Sum Insured?",
        candidate_claim="Under the 2023 PMFBY guidelines, the maximum farmer premium for Kharif perennial betelvine is 3.0% of Sum Insured or actuarial rate, whichever is less.",
        retrieved_items=ret_items,
    )
    assert pred.predicted_verdict == Verdict.UNVERIFIABLE.value


def test_broken_table_extraction_where_headers_are_missing() -> None:
    """Adversarial Case 21: Broken table extraction where headers are missing is rejected with warning."""
    manifest = load_source_manifest(PROJECT_ROOT / "data" / "manifests" / "source_manifest.json")
    doc = manifest.get_document("DOC_PMFBY_OG_2023")
    assert doc is not None

    broken_tables = [
        {
            "table_id": "TBL_BROKEN",
            "section": "Broken Table Test",
            "headers": [],
            "rows": [["Kharif", "2.0%"]],
        }
    ]
    units, warnings = extract_table_units_from_page_tables(
        doc=doc,
        physical_pdf_page=1,
        printed_page="10",
        raw_tables=broken_tables,
        extraction_method="test_parser",
    )
    assert len(units) == 0
    assert len(warnings) == 1
    assert "missing headers" in warnings[0]["warning"].lower()


def test_duplicate_chunks_with_same_rule_do_not_cause_false_conflict() -> None:
    """Adversarial Case 22: Duplicate chunks with the same rule (2.0% Kharif) yield SUPPORTED."""
    store = build_default_evidence_store(PROJECT_ROOT)
    verifier = FieldGuardVerifier(evidence_store=store)

    ev_tbl = store.evidence_units["EV_DOC_PMFBY_OG_2023_P4_TBL_OG2023_PREMIUM_RATES_R1"]
    ev_prose = store.evidence_units["EV_DOC_PMFBY_OG_2023_P4_CHUNK_2"]
    ret_items = [
        {"evidence_id": ev_tbl.evidence_id, "retrieval_score": 0.98, "rank": 1, "text": ev_tbl.text},
        {"evidence_id": ev_prose.evidence_id, "retrieval_score": 0.95, "rank": 2, "text": ev_prose.text},
    ]
    pred = verifier.verify_claim(
        claim_id="TEST_DUP_CHUNKS",
        question="Under the 2023 PMFBY operational guidelines, is the maximum farmer premium for Kharif food grains 2.0%?",
        candidate_claim="Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 2.0% of Sum Insured or actuarial rate, whichever is less.",
        retrieved_items=ret_items,
    )
    assert pred.predicted_verdict == Verdict.SUPPORTED.value
