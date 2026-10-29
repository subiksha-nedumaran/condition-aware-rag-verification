"""FieldGuard evaluation package."""

from fieldguard.evaluation.ablation import get_ablation_configurations, run_ablation_suite
from fieldguard.evaluation.bootstrap import compute_cluster_bootstrap_cis, compute_paired_cluster_bootstrap_diff
from fieldguard.evaluation.metrics import compute_verification_metrics
from fieldguard.evaluation.retrieval_metrics import (
    aggregate_retrieval_metrics,
    compute_hit_at_k,
    compute_item_recall_at_k,
    compute_reciprocal_rank,
    deduplicate_retrieved_ids,
    evaluate_single_query_retrieval,
)

__all__ = [
    "get_ablation_configurations",
    "run_ablation_suite",
    "compute_cluster_bootstrap_cis",
    "compute_paired_cluster_bootstrap_diff",
    "compute_verification_metrics",
    "aggregate_retrieval_metrics",
    "compute_hit_at_k",
    "compute_item_recall_at_k",
    "compute_reciprocal_rank",
    "deduplicate_retrieved_ids",
    "evaluate_single_query_retrieval",
]
