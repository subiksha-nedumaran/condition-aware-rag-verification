"""Unit tests for retrieval evaluation metrics (Phase 8)."""

from __future__ import annotations

import pytest

from fieldguard.evaluation.retrieval_metrics import (
    aggregate_retrieval_metrics,
    deduplicate_retrieved_ids,
    evaluate_single_query_retrieval,
)


def test_deduplicate_retrieved_ids() -> None:
    items = ["EV_1", "EV_2", "EV_1", "EV_3", "EV_2"]
    assert deduplicate_retrieved_ids(items) == ["EV_1", "EV_2", "EV_3"]


def test_single_query_recall_and_mrr_known_toy_rankings() -> None:
    corpus = {"EV_1", "EV_2", "EV_3", "EV_4", "EV_5"}

    r1 = evaluate_single_query_retrieval(
        claim_id="C1",
        claim_family_id="F1",
        claim_type="cat01_supported_exact",
        retriever_name="hybrid",
        retrieved_ids=["EV_2", "EV_1", "EV_3"],
        gold_evidence_ids=["EV_2"],
        indexed_corpus_ids=corpus,
    )
    assert r1.is_eligible is True
    assert r1.hit_at_1 == 1
    assert r1.hit_at_3 == 1
    assert r1.reciprocal_rank == pytest.approx(1.0)

    r2 = evaluate_single_query_retrieval(
        claim_id="C2",
        claim_family_id="F2",
        claim_type="cat01_supported_exact",
        retriever_name="hybrid",
        retrieved_ids=["EV_1", "EV_1", "EV_3", "EV_4", "EV_5"],
        gold_evidence_ids=["EV_4", "EV_5"],
        indexed_corpus_ids=corpus,
    )
    assert r2.is_eligible is True
    assert r2.hit_at_1 == 0
    assert r2.hit_at_3 == 1
    assert r2.first_hit_rank == 3
    assert r2.reciprocal_rank == pytest.approx(1.0 / 3.0)
    assert r2.item_recall_at_5 == pytest.approx(1.0)


def test_queries_with_no_available_gold_evidence_excluded_from_denominator() -> None:
    corpus = {"EV_1", "EV_2", "EV_3"}

    q_elig = evaluate_single_query_retrieval(
        claim_id="C_ELIG",
        claim_family_id="F1",
        claim_type="cat01_supported_exact",
        retriever_name="lexical",
        retrieved_ids=["EV_1", "EV_2"],
        gold_evidence_ids=["EV_1"],
        indexed_corpus_ids=corpus,
    )
    q_unavail = evaluate_single_query_retrieval(
        claim_id="C_UNAVAIL",
        claim_family_id="F2",
        claim_type="cat06_missing_corpus_evidence",
        retriever_name="lexical",
        retrieved_ids=["EV_1", "EV_2"],
        gold_evidence_ids=[],
        indexed_corpus_ids=corpus,
    )
    q_invalid = evaluate_single_query_retrieval(
        claim_id="C_INVALID",
        claim_family_id="F3",
        claim_type="cat01_supported_exact",
        retriever_name="lexical",
        retrieved_ids=["EV_1", "EV_2"],
        gold_evidence_ids=["EV_NON_EXISTENT_999"],
        indexed_corpus_ids=corpus,
    )

    assert q_unavail.is_eligible is False
    assert q_unavail.ineligibility_reason == "genuinely_unavailable_gold_evidence"
    assert q_invalid.is_eligible is False
    assert q_invalid.ineligibility_reason == "gold_evidence_absent_from_indexed_corpus"

    agg = aggregate_retrieval_metrics([q_elig, q_unavail, q_invalid], retriever_name="lexical")
    assert agg["total_queries"] == 3
    assert agg["eligible_query_count"] == 1
    assert agg["unavailable_gold_query_count"] == 1
    assert agg["absent_from_corpus_query_count"] == 1
    assert agg["invalid_annotation_count"] == 1
    assert agg["recall_at_1"] == pytest.approx(1.0)
    assert agg["mrr"] == pytest.approx(1.0)
