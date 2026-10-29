"""Retrieval evaluation metrics: Recall@k (query-level hit rate), MRR, and corpus eligibility auditing (Phase 8)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class QueryRetrievalEvalRecord:
    """Per-query retrieval evaluation result with eligibility and provenance diagnostics."""

    claim_id: str
    claim_family_id: str
    claim_type: str
    retriever_name: str
    is_eligible: bool
    ineligibility_reason: str | None
    gold_evidence_ids: list[str]
    valid_corpus_gold_ids: list[str]
    invalid_annotation_gold_ids: list[str]
    deduplicated_retrieved_ids: list[str]
    hit_at_1: int | None
    hit_at_3: int | None
    hit_at_5: int | None
    hit_at_10: int | None
    item_recall_at_5: float | None
    reciprocal_rank: float | None
    first_hit_rank: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def deduplicate_retrieved_ids(retrieved_ids: list[str]) -> list[str]:
    """Deduplicate a ranking of evidence IDs while preserving first-seen rank order."""
    seen: set[str] = set()
    out: list[str] = []
    for eid in retrieved_ids:
        if not eid or not isinstance(eid, str):
            continue
        if eid not in seen:
            seen.add(eid)
            out.append(eid)
    return out


def compute_hit_at_k(
    retrieved_ids: list[str],
    gold_ids: set[str],
    k: int,
) -> int:
    """
    Query-level evidence hit rate at k:
    Returns 1 if at least one gold evidence ID appears in the top k deduplicated retrieved IDs, else 0.
    Handles empty rankings and k > len(retrieved_ids) safely.
    """
    if k <= 0 or not retrieved_ids or not gold_ids:
        return 0
    dedup = deduplicate_retrieved_ids(retrieved_ids)
    top_slice = dedup[:k]
    return 1 if any(eid in gold_ids for eid in top_slice) else 0


def compute_item_recall_at_k(
    retrieved_ids: list[str],
    gold_ids: set[str],
    k: int,
) -> float:
    """
    Evidence-item recall at k: fraction of all valid gold evidence IDs for the query
    that appear in the top k deduplicated retrieved IDs.
    """
    if not gold_ids:
        return 0.0
    if k <= 0 or not retrieved_ids:
        return 0.0
    dedup = deduplicate_retrieved_ids(retrieved_ids)
    top_set = set(dedup[:k])
    hits = sum(1 for gid in gold_ids if gid in top_set)
    return float(hits) / float(len(gold_ids))


def compute_reciprocal_rank(
    retrieved_ids: list[str],
    gold_ids: set[str],
) -> tuple[float, int | None]:
    """
    Return (reciprocal_rank, first_hit_rank) over deduplicated retrieved IDs.
    If no gold ID is retrieved, returns (0.0, None).
    """
    if not retrieved_ids or not gold_ids:
        return 0.0, None
    dedup = deduplicate_retrieved_ids(retrieved_ids)
    for rank_idx, eid in enumerate(dedup, start=1):
        if eid in gold_ids:
            return 1.0 / float(rank_idx), rank_idx
    return 0.0, None


def evaluate_single_query_retrieval(
    claim_id: str,
    claim_family_id: str,
    claim_type: str,
    retriever_name: str,
    retrieved_ids: list[str],
    gold_evidence_ids: list[str] | None,
    indexed_corpus_ids: set[str],
) -> QueryRetrievalEvalRecord:
    """
    Evaluate retrieval for a single query, distinguishing:
      1. Queries with genuinely unavailable gold evidence (`gold_evidence_ids == []`).
      2. Queries whose annotated gold IDs are invalid or absent from the indexed corpus.
      3. Eligible queries whose valid gold evidence exists in the indexed corpus.
    """
    raw_gold = list(gold_evidence_ids or [])
    dedup_ret = deduplicate_retrieved_ids(retrieved_ids or [])

    if not raw_gold:
        return QueryRetrievalEvalRecord(
            claim_id=claim_id,
            claim_family_id=claim_family_id,
            claim_type=claim_type,
            retriever_name=retriever_name,
            is_eligible=False,
            ineligibility_reason="genuinely_unavailable_gold_evidence",
            gold_evidence_ids=[],
            valid_corpus_gold_ids=[],
            invalid_annotation_gold_ids=[],
            deduplicated_retrieved_ids=dedup_ret,
            hit_at_1=None,
            hit_at_3=None,
            hit_at_5=None,
            hit_at_10=None,
            item_recall_at_5=None,
            reciprocal_rank=None,
            first_hit_rank=None,
        )

    valid_gold: list[str] = []
    invalid_gold: list[str] = []
    for gid in raw_gold:
        if not gid or not isinstance(gid, str) or gid not in indexed_corpus_ids:
            invalid_gold.append(str(gid))
        else:
            if gid not in valid_gold:
                valid_gold.append(gid)

    if not valid_gold:
        return QueryRetrievalEvalRecord(
            claim_id=claim_id,
            claim_family_id=claim_family_id,
            claim_type=claim_type,
            retriever_name=retriever_name,
            is_eligible=False,
            ineligibility_reason="gold_evidence_absent_from_indexed_corpus",
            gold_evidence_ids=raw_gold,
            valid_corpus_gold_ids=[],
            invalid_annotation_gold_ids=invalid_gold,
            deduplicated_retrieved_ids=dedup_ret,
            hit_at_1=None,
            hit_at_3=None,
            hit_at_5=None,
            hit_at_10=None,
            item_recall_at_5=None,
            reciprocal_rank=None,
            first_hit_rank=None,
        )

    gold_set = set(valid_gold)
    h1 = compute_hit_at_k(dedup_ret, gold_set, k=1)
    h3 = compute_hit_at_k(dedup_ret, gold_set, k=3)
    h5 = compute_hit_at_k(dedup_ret, gold_set, k=5)
    h10 = compute_hit_at_k(dedup_ret, gold_set, k=10)
    irec5 = compute_item_recall_at_k(dedup_ret, gold_set, k=5)
    rr, first_rank = compute_reciprocal_rank(dedup_ret, gold_set)

    return QueryRetrievalEvalRecord(
        claim_id=claim_id,
        claim_family_id=claim_family_id,
        claim_type=claim_type,
        retriever_name=retriever_name,
        is_eligible=True,
        ineligibility_reason=None,
        gold_evidence_ids=raw_gold,
        valid_corpus_gold_ids=valid_gold,
        invalid_annotation_gold_ids=invalid_gold,
        deduplicated_retrieved_ids=dedup_ret,
        hit_at_1=h1,
        hit_at_3=h3,
        hit_at_5=h5,
        hit_at_10=h10,
        item_recall_at_5=round(irec5, 6),
        reciprocal_rank=round(rr, 6),
        first_hit_rank=first_rank,
    )


def aggregate_retrieval_metrics(
    records: list[QueryRetrievalEvalRecord],
    retriever_name: str,
) -> dict[str, Any]:
    """
    Aggregate Recall@1, Recall@3, Recall@5, Recall@10, MRR, and eligibility counts
    across a set of QueryRetrievalEvalRecord objects.
    """
    total_queries = len(records)
    eligible = [r for r in records if r.is_eligible]
    unavailable_gold = [
        r for r in records if r.ineligibility_reason == "genuinely_unavailable_gold_evidence"
    ]
    absent_from_corpus = [
        r for r in records if r.ineligibility_reason == "gold_evidence_absent_from_indexed_corpus"
    ]
    invalid_annot_count = sum(1 for r in records if len(r.invalid_annotation_gold_ids) > 0)

    n_elig = len(eligible)
    if n_elig == 0:
        return {
            "retriever_name": retriever_name,
            "total_queries": total_queries,
            "eligible_query_count": 0,
            "unavailable_gold_query_count": len(unavailable_gold),
            "absent_from_corpus_query_count": len(absent_from_corpus),
            "invalid_annotation_count": invalid_annot_count,
            "recall_at_1": 0.0,
            "recall_at_3": 0.0,
            "recall_at_5": 0.0,
            "recall_at_10": 0.0,
            "item_recall_at_5": 0.0,
            "mrr": 0.0,
        }

    r1 = sum(int(r.hit_at_1 or 0) for r in eligible) / n_elig
    r3 = sum(int(r.hit_at_3 or 0) for r in eligible) / n_elig
    r5 = sum(int(r.hit_at_5 or 0) for r in eligible) / n_elig
    r10 = sum(int(r.hit_at_10 or 0) for r in eligible) / n_elig
    ir5 = sum(float(r.item_recall_at_5 or 0.0) for r in eligible) / n_elig
    mrr = sum(float(r.reciprocal_rank or 0.0) for r in eligible) / n_elig

    # Breakdown by claim_type
    by_type: dict[str, dict[str, Any]] = {}
    type_groups: dict[str, list[QueryRetrievalEvalRecord]] = {}
    for r in eligible:
        type_groups.setdefault(r.claim_type, []).append(r)

    for ctype, grp in sorted(type_groups.items()):
        ng = len(grp)
        by_type[ctype] = {
            "eligible_count": ng,
            "recall_at_1": round(sum(int(x.hit_at_1 or 0) for x in grp) / ng, 4),
            "recall_at_3": round(sum(int(x.hit_at_3 or 0) for x in grp) / ng, 4),
            "recall_at_5": round(sum(int(x.hit_at_5 or 0) for x in grp) / ng, 4),
            "recall_at_10": round(sum(int(x.hit_at_10 or 0) for x in grp) / ng, 4),
            "mrr": round(sum(float(x.reciprocal_rank or 0.0) for x in grp) / ng, 4),
        }

    return {
        "retriever_name": retriever_name,
        "total_queries": total_queries,
        "eligible_query_count": n_elig,
        "unavailable_gold_query_count": len(unavailable_gold),
        "absent_from_corpus_query_count": len(absent_from_corpus),
        "invalid_annotation_count": invalid_annot_count,
        "hits_at_1": sum(int(r.hit_at_1 or 0) for r in eligible),
        "hits_at_3": sum(int(r.hit_at_3 or 0) for r in eligible),
        "hits_at_5": sum(int(r.hit_at_5 or 0) for r in eligible),
        "hits_at_10": sum(int(r.hit_at_10 or 0) for r in eligible),
        "recall_at_1": round(r1, 4),
        "recall_at_3": round(r3, 4),
        "recall_at_5": round(r5, 4),
        "recall_at_10": round(r10, 4),
        "item_recall_at_5": round(ir5, 4),
        "mrr": round(mrr, 4),
        "by_claim_type": by_type,
    }
