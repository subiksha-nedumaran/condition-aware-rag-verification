"""End-to-end experimental evaluation runner covering Experiments A through I (Phase 8, 9, 10, 12)."""

from __future__ import annotations

import csv
import datetime
import json
import platform
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from fieldguard.benchmark_builder import BenchmarkClaimRecord, load_benchmark_claims
from fieldguard.claim_parser import DeterministicClaimParser, ParsedClaim, validate_parsed_claim_schema
from fieldguard.claim_parser_llm import LLMClaimParser, LLMParserConfig
from fieldguard.evaluation.ablation import _resolve_retrieved_items_for_claim, run_ablation_suite
from fieldguard.evaluation.bootstrap import compute_cluster_bootstrap_cis, compute_paired_cluster_bootstrap_diff
from fieldguard.evaluation.error_analysis import generate_error_analysis_report
from fieldguard.evaluation.metrics import compute_verification_metrics
from fieldguard.evaluation.retrieval_metrics import aggregate_retrieval_metrics, evaluate_single_query_retrieval
from fieldguard.evidence_store import EvidenceStore, build_default_evidence_store
from fieldguard.retrieval.base import BaseRetriever
from fieldguard.retrieval.hybrid import HybridRetriever
from fieldguard.retrieval.lexical import LexicalBM25Retriever
from fieldguard.retrieval.semantic import SemanticRetriever
from fieldguard.retrieval.table_retrieval import TableAwareRetriever
from fieldguard.verifier import FieldGuardVerifier, VerifierConfig


def build_all_retrievers(store: EvidenceStore) -> dict[str, BaseRetriever]:
    """Instantiate all four retrieval baselines over the same extracted evidence corpus."""
    units = list(store.evidence_units.values())
    sem = SemanticRetriever(units)
    lex = LexicalBM25Retriever(units)
    tbl = TableAwareRetriever(units)
    hyb = HybridRetriever(
        units,
        semantic_retriever=sem,
        lexical_retriever=lex,
        table_retriever=tbl,
    )
    return {
        "semantic": sem,
        "lexical": lex,
        "table": tbl,
        "hybrid": hyb,
    }


def run_retrieval_experiment(
    project_root: Path | None = None,
    split: str = "test",
) -> dict[str, Any]:
    """
    Experiment A (Phase 8): Evaluate semantic, lexical, table-aware, and hybrid retrieval.
    Computes Recall@1, Recall@3, Recall@5, Recall@10, item-level Recall@5, and MRR.
    Saves:
      - results/metrics/recall_at_k.csv
      - results/metrics/mrr.csv
      - results/predictions/retrieval_rankings.jsonl
      - results/tables/retrieval_comparison.csv
      - results/figures/retrieval_comparison.png
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parents[3]

    results_dir = project_root / "results"
    for sub in ("metrics", "tables", "predictions", "figures", "logs"):
        (results_dir / sub).mkdir(parents=True, exist_ok=True)

    store = build_default_evidence_store(project_root)
    retrievers = build_all_retrievers(store)
    claims = load_benchmark_claims(project_root, split=split)
    corpus_ids = set(store.evidence_units.keys())

    recall_rows: list[dict[str, Any]] = []
    mrr_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    ranking_records: list[dict[str, Any]] = []

    for r_name in ("semantic", "lexical", "table", "hybrid"):
        ret = retrievers[r_name]
        eval_records = []
        latencies_ms: list[float] = []

        for clm in claims:
            query_text = f"{clm.question} {clm.candidate_claim}".strip()
            t0 = time.perf_counter()
            ranked_items = ret.retrieve(query_text, top_k=10)
            lat_ms = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(lat_ms)

            ret_ids = [item.evidence_id for item in ranked_items]
            ev_rec = evaluate_single_query_retrieval(
                claim_id=clm.claim_id,
                claim_family_id=clm.claim_family_id,
                claim_type=clm.claim_type,
                retriever_name=r_name,
                retrieved_ids=ret_ids,
                gold_evidence_ids=clm.gold_evidence_ids,
                indexed_corpus_ids=corpus_ids,
            )
            eval_records.append(ev_rec)

            ranking_records.append(
                {
                    "claim_id": clm.claim_id,
                    "claim_family_id": clm.claim_family_id,
                    "split": clm.split,
                    "retriever_name": r_name,
                    "is_eligible": ev_rec.is_eligible,
                    "ineligibility_reason": ev_rec.ineligibility_reason,
                    "gold_evidence_ids": clm.gold_evidence_ids,
                    "hit_at_1": ev_rec.hit_at_1,
                    "hit_at_3": ev_rec.hit_at_3,
                    "hit_at_5": ev_rec.hit_at_5,
                    "hit_at_10": ev_rec.hit_at_10,
                    "reciprocal_rank": ev_rec.reciprocal_rank,
                    "latency_ms": round(lat_ms, 4),
                    "rankings": [item.to_dict() for item in ranked_items],
                }
            )

        agg = aggregate_retrieval_metrics(eval_records, r_name)
        mean_lat = round(float(np.mean(latencies_ms)), 4)

        recall_rows.append(
            {
                "retriever_name": r_name,
                "split": split,
                "total_queries": agg["total_queries"],
                "eligible_query_count": agg["eligible_query_count"],
                "unavailable_gold_query_count": agg["unavailable_gold_query_count"],
                "absent_from_corpus_query_count": agg["absent_from_corpus_query_count"],
                "invalid_annotation_count": agg["invalid_annotation_count"],
                "recall_at_1": agg["recall_at_1"],
                "recall_at_3": agg["recall_at_3"],
                "recall_at_5": agg["recall_at_5"],
                "recall_at_10": agg["recall_at_10"],
                "item_recall_at_5": agg["item_recall_at_5"],
            }
        )
        mrr_rows.append(
            {
                "retriever_name": r_name,
                "split": split,
                "eligible_query_count": agg["eligible_query_count"],
                "mrr": agg["mrr"],
                "mean_latency_ms": mean_lat,
            }
        )
        comparison_rows.append(
            {
                "retriever_name": r_name,
                "split": split,
                "total_queries": agg["total_queries"],
                "eligible_query_count": agg["eligible_query_count"],
                "unavailable_gold_query_count": agg["unavailable_gold_query_count"],
                "invalid_annotation_count": agg["invalid_annotation_count"],
                "hits_at_1": agg["hits_at_1"],
                "hits_at_3": agg["hits_at_3"],
                "hits_at_5": agg["hits_at_5"],
                "hits_at_10": agg["hits_at_10"],
                "recall_at_1": agg["recall_at_1"],
                "recall_at_3": agg["recall_at_3"],
                "recall_at_5": agg["recall_at_5"],
                "recall_at_10": agg["recall_at_10"],
                "item_recall_at_5": agg["item_recall_at_5"],
                "mrr": agg["mrr"],
                "mean_latency_ms": mean_lat,
            }
        )

    # Save CSVs and JSONL
    with (results_dir / "metrics" / "recall_at_k.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(recall_rows[0].keys()))
        writer.writeheader()
        writer.writerows(recall_rows)

    with (results_dir / "metrics" / "mrr.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(mrr_rows[0].keys()))
        writer.writeheader()
        writer.writerows(mrr_rows)

    with (results_dir / "tables" / "retrieval_comparison.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(comparison_rows[0].keys()))
        writer.writeheader()
        writer.writerows(comparison_rows)

    with (results_dir / "predictions" / "retrieval_rankings.jsonl").open("w", encoding="utf-8") as f:
        for rec in ranking_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    _plot_retrieval_figure(comparison_rows, results_dir / "figures" / "retrieval_comparison.png")

    return {
        "status": "SUCCESS",
        "split": split,
        "comparison": comparison_rows,
    }


def _plot_retrieval_figure(rows: list[dict[str, Any]], output_path: Path) -> None:
    names = [r["retriever_name"].capitalize() for r in rows]
    r1 = [r["recall_at_1"] for r in rows]
    r3 = [r["recall_at_3"] for r in rows]
    r5 = [r["recall_at_5"] for r in rows]
    r10 = [r["recall_at_10"] for r in rows]
    mrr = [r["mrr"] for r in rows]

    x = np.arange(len(names))
    w = 0.16

    fig, ax = plt.subplots(figsize=(9.5, 5.2), dpi=150)
    ax.bar(x - 2 * w, r1, w, label="Recall@1", color="#4c78a8")
    ax.bar(x - w, r3, w, label="Recall@3", color="#72b7b2")
    ax.bar(x, r5, w, label="Recall@5", color="#54a24b")
    ax.bar(x + w, r10, w, label="Recall@10", color="#eeca3b")
    ax.bar(x + 2 * w, mrr, w, label="MRR", color="#f58518")

    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=10)
    ax.set_ylim(0.0, 1.12)
    ax.set_ylabel("Score (0.0 to 1.0)")
    ax.set_title("FieldGuard Experiment A: Retrieval Recall@k and MRR by Method")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.legend(loc="lower right", ncol=3, fontsize=9)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output_path))
    plt.close(fig)


def get_comparison_baseline_configs() -> list[VerifierConfig]:
    """Return the 4 primary comparison methods defined in Phase 7 (Section 11)."""
    return [
        VerifierConfig(
            config_name="baseline_a_retrieval_only",
            mode="retrieval_only",
            enable_structured_condition_matching=False,
            enable_crop_category_matching=False,
            enable_season_matching=False,
            enable_qualification_matching=False,
            enable_temporal_checks=False,
            enable_provenance_validation=False,
            enable_evidence_sufficiency=True,
            retrieval_method="hybrid",
        ),
        VerifierConfig(
            config_name="baseline_b_numeric_only",
            mode="numeric_only",
            enable_structured_condition_matching=False,
            enable_crop_category_matching=False,
            enable_season_matching=False,
            enable_qualification_matching=False,
            enable_temporal_checks=False,
            enable_provenance_validation=False,
            enable_evidence_sufficiency=True,
            retrieval_method="hybrid",
        ),
        VerifierConfig(
            config_name="baseline_c_numeric_basic_context",
            mode="fieldguard",
            enable_structured_condition_matching=True,
            enable_crop_category_matching=True,
            enable_season_matching=True,
            enable_qualification_matching=False,
            enable_temporal_checks=False,
            enable_provenance_validation=True,
            enable_evidence_sufficiency=True,
            retrieval_method="hybrid",
        ),
        VerifierConfig(
            config_name="fieldguard_full",
            mode="fieldguard",
            enable_structured_condition_matching=True,
            enable_crop_category_matching=True,
            enable_season_matching=True,
            enable_qualification_matching=True,
            enable_temporal_checks=True,
            enable_provenance_validation=True,
            enable_evidence_sufficiency=True,
            retrieval_method="hybrid",
        ),
    ]


def run_verification_experiment(
    project_root: Path | None = None,
    split: str = "test",
    bootstrap_iterations: int = 1000,
) -> dict[str, Any]:
    """
    Experiments B, C, D, E, F (Phase 7 & 12):
    Evaluate Baseline A, Baseline B, Baseline C, and Full FieldGuard on `split`,
    plus controlled breakdowns by context perturbation (Exp D), evidence regime (Exp E),
    and temporal category (Exp F), and generate `docs/error_analysis.md`.
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parents[3]

    results_dir = project_root / "results"
    for sub in ("metrics", "tables", "predictions", "figures", "logs"):
        (results_dir / sub).mkdir(parents=True, exist_ok=True)

    store = build_default_evidence_store(project_root)
    retrievers = build_all_retrievers(store)
    claims = load_benchmark_claims(project_root, split=split)

    configs = get_comparison_baseline_configs()
    gold_verdicts = [c.gold_verdict for c in claims]
    family_ids = [c.claim_family_id for c in claims]

    summary_rows: list[dict[str, Any]] = []
    fsr_breakdown_rows: list[dict[str, Any]] = []
    all_predictions: list[dict[str, Any]] = []
    preds_by_method: dict[str, list[dict[str, Any]]] = {}
    verdict_lists_by_method: dict[str, list[str]] = {}

    for cfg in configs:
        verifier = FieldGuardVerifier(evidence_store=store, config=cfg)
        ret_engine = retrievers[cfg.retrieval_method]

        m_preds_str: list[str] = []
        m_preds_dicts: list[dict[str, Any]] = []
        ver_lats: list[float] = []
        e2e_lats: list[float] = []

        for clm in claims:
            ret_items, ret_lat = _resolve_retrieved_items_for_claim(
                claim=clm,
                retriever=ret_engine,
                store=store,
                top_k=cfg.top_k,
            )
            pred = verifier.verify_claim(
                claim_id=clm.claim_id,
                question=clm.question,
                candidate_claim=clm.candidate_claim,
                retrieved_items=ret_items,
                retrieval_method=cfg.retrieval_method,
                retrieval_latency_ms=ret_lat,
            )
            m_preds_str.append(pred.predicted_verdict)
            ver_lats.append(pred.verification_latency_ms)
            e2e_lats.append(pred.latency_ms)

            p_dict = pred.to_dict()
            p_dict["gold_verdict"] = clm.gold_verdict
            p_dict["claim_type"] = clm.claim_type
            p_dict["claim_family_id"] = clm.claim_family_id
            p_dict["perturbation_dimension"] = clm.perturbation_dimension
            p_dict["evidence_regime"] = clm.evidence_regime
            p_dict["temporal_category"] = clm.temporal_category
            m_preds_dicts.append(p_dict)
            all_predictions.append(p_dict)

        preds_by_method[cfg.config_name] = m_preds_dicts
        verdict_lists_by_method[cfg.config_name] = m_preds_str

        vm = compute_verification_metrics(
            gold_verdicts=gold_verdicts,
            predicted_verdicts=m_preds_str,
            verification_latencies_ms=ver_lats,
            e2e_latencies_ms=e2e_lats,
            config_name=cfg.config_name,
        )
        cis = compute_cluster_bootstrap_cis(
            claim_family_ids=family_ids,
            gold_verdicts=gold_verdicts,
            predicted_verdicts=m_preds_str,
            n_iterations=bootstrap_iterations,
        )

        summary_rows.append(
            {
                "method": cfg.config_name,
                "split": split,
                "n_claims": vm["n_claims"],
                "accuracy": vm["accuracy"],
                "accuracy_ci_95": f"[{cis['accuracy']['ci_lower']:.4f}, {cis['accuracy']['ci_upper']:.4f}]",
                "macro_f1": vm["macro_f1"],
                "macro_f1_ci_95": f"[{cis['macro_f1']['ci_lower']:.4f}, {cis['macro_f1']['ci_upper']:.4f}]",
                "false_support_rate": vm["false_support_rate"],
                "false_support_counts": f"{vm['false_support_num']}/{vm['false_support_den']}",
                "fsr_ci_95": f"[{cis['false_support_rate']['ci_lower']:.4f}, {cis['false_support_rate']['ci_upper']:.4f}]",
                "wrong_context_fsr": vm["wrong_context_false_support_rate"],
                "wrong_context_fsr_counts": f"{vm['wrong_context_false_support_num']}/{vm['wrong_context_false_support_den']}",
                "unverifiable_fsr": vm["unverifiable_false_support_rate"],
                "unverifiable_fsr_counts": f"{vm['unverifiable_false_support_num']}/{vm['unverifiable_false_support_den']}",
                "contradicted_fsr": vm["contradicted_false_support_rate"],
                "contradicted_fsr_counts": f"{vm['contradicted_false_support_num']}/{vm['contradicted_false_support_den']}",
                "false_discovery_among_supported": vm["false_discovery_among_supported"],
                "coverage": vm["coverage"],
                "abstention_rate": vm["abstention_rate"],
                "supported_f1": vm["supported_f1"],
                "contradicted_f1": vm["contradicted_f1"],
                "wrong_context_f1": vm["wrong_context_f1"],
                "unverifiable_f1": vm["unverifiable_f1"],
                "verification_latency_mean_ms": vm["verification_latency_mean_ms"],
                "e2e_latency_mean_ms": vm["e2e_latency_mean_ms"],
                "confusion_matrix_json": json.dumps(vm["confusion_matrix"]),
            }
        )

        fsr_breakdown_rows.append(
            {
                "method": cfg.config_name,
                "overall_fsr": vm["false_support_rate"],
                "overall_num": vm["false_support_num"],
                "overall_den": vm["false_support_den"],
                "wrong_context_fsr": vm["wrong_context_false_support_rate"],
                "wrong_context_num": vm["wrong_context_false_support_num"],
                "wrong_context_den": vm["wrong_context_false_support_den"],
                "unverifiable_fsr": vm["unverifiable_false_support_rate"],
                "unverifiable_num": vm["unverifiable_false_support_num"],
                "unverifiable_den": vm["unverifiable_false_support_den"],
                "contradicted_fsr": vm["contradicted_false_support_rate"],
                "contradicted_num": vm["contradicted_false_support_num"],
                "contradicted_den": vm["contradicted_false_support_den"],
            }
        )

    # Save primary verification CSVs & JSONL
    with (results_dir / "metrics" / "verification_results.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    with (results_dir / "tables" / "verification_comparison.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    with (results_dir / "tables" / "false_support_breakdown.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fsr_breakdown_rows[0].keys()))
        writer.writeheader()
        writer.writerows(fsr_breakdown_rows)

    with (results_dir / "predictions" / "verification_predictions.jsonl").open("w", encoding="utf-8") as f:
        for p in all_predictions:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    # Experiment D: Controlled Context Perturbations breakdown
    pert_rows = _compute_subgroup_breakdown(
        claims=claims,
        verdict_lists_by_method=verdict_lists_by_method,
        attr_name="perturbation_dimension",
    )
    with (results_dir / "tables" / "context_perturbations.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(pert_rows[0].keys()))
        writer.writeheader()
        writer.writerows(pert_rows)

    # Experiment E: Missing and Misleading Evidence Regimes breakdown
    regime_rows = _compute_subgroup_breakdown(
        claims=claims,
        verdict_lists_by_method=verdict_lists_by_method,
        attr_name="evidence_regime",
    )
    with (results_dir / "tables" / "evidence_regimes.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(regime_rows[0].keys()))
        writer.writeheader()
        writer.writerows(regime_rows)

    # Experiment F: Temporal Grounding breakdown
    temp_rows = _compute_subgroup_breakdown(
        claims=claims,
        verdict_lists_by_method=verdict_lists_by_method,
        attr_name="temporal_category",
    )
    with (results_dir / "tables" / "temporal_grounding.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(temp_rows[0].keys()))
        writer.writeheader()
        writer.writerows(temp_rows)

    # Paired statistical comparisons vs FieldGuard Full
    fg_verdicts = verdict_lists_by_method["fieldguard_full"]
    paired_stats: dict[str, Any] = {}
    for m_name, m_verdicts in verdict_lists_by_method.items():
        if m_name == "fieldguard_full":
            continue
        paired_stats[m_name] = compute_paired_cluster_bootstrap_diff(
            claim_family_ids=family_ids,
            gold_verdicts=gold_verdicts,
            preds_method_a=fg_verdicts,
            preds_method_b=m_verdicts,
            n_iterations=bootstrap_iterations,
        )

    _plot_verification_figure(summary_rows, results_dir / "figures" / "verification_comparison.png")
    err_summary = generate_error_analysis_report(
        claims=claims,
        predictions_by_method=preds_by_method,
        output_doc_path=project_root / "docs" / "error_analysis.md",
    )

    return {
        "status": "SUCCESS",
        "split": split,
        "summary_rows": summary_rows,
        "fsr_breakdown": fsr_breakdown_rows,
        "perturbation_breakdown": pert_rows,
        "regime_breakdown": regime_rows,
        "temporal_breakdown": temp_rows,
        "paired_statistical_tests": paired_stats,
        "error_analysis_summary": err_summary,
    }


def _compute_subgroup_breakdown(
    claims: list[BenchmarkClaimRecord],
    verdict_lists_by_method: dict[str, list[str]],
    attr_name: str,
) -> list[dict[str, Any]]:
    groups: dict[str, list[int]] = {}
    for idx, clm in enumerate(claims):
        val = str(getattr(clm, attr_name, "unknown"))
        groups.setdefault(val, []).append(idx)

    rows: list[dict[str, Any]] = []
    for g_val in sorted(groups.keys()):
        idxs = groups[g_val]
        sub_gold = [claims[i].gold_verdict for i in idxs]
        for m_name, full_preds in verdict_lists_by_method.items():
            sub_preds = [full_preds[i] for i in idxs]
            vm = compute_verification_metrics(sub_gold, sub_preds, config_name=m_name)
            rows.append(
                {
                    attr_name: g_val,
                    "method": m_name,
                    "n_claims": len(idxs),
                    "accuracy": vm["accuracy"],
                    "macro_f1": vm["macro_f1"],
                    "false_support_rate": vm["false_support_rate"],
                    "false_support_num": vm["false_support_num"],
                    "false_support_den": vm["false_support_den"],
                    "coverage": vm["coverage"],
                    "abstention_rate": vm["abstention_rate"],
                }
            )
    return rows


def _plot_verification_figure(rows: list[dict[str, Any]], output_path: Path) -> None:
    labels = [r["method"] for r in rows]
    acc = [r["accuracy"] for r in rows]
    f1 = [r["macro_f1"] for r in rows]
    fsr = [r["false_support_rate"] for r in rows]
    wc_fsr = [r["wrong_context_fsr"] for r in rows]

    x = np.arange(len(labels))
    w = 0.20

    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150)
    ax.bar(x - 1.5 * w, acc, w, label="Accuracy", color="#2b5c8f")
    ax.bar(x - 0.5 * w, f1, w, label="Macro-F1", color="#388e3c")
    ax.bar(x + 0.5 * w, fsr, w, label="Overall False-Support Rate", color="#d32f2f")
    ax.bar(x + 1.5 * w, wc_fsr, w, label="WRONG_CONTEXT False-Support Rate", color="#f57c00")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=12, ha="right", fontsize=9.5)
    ax.set_ylim(0.0, 1.12)
    ax.set_ylabel("Score / Rate (0.0 to 1.0)")
    ax.set_title("FieldGuard Experiments B & C: Verification Accuracy, Macro-F1, and False-Support Reduction")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output_path))
    plt.close(fig)


def run_claim_parser_comparison(
    project_root: Path | None = None,
    split: str = "test",
) -> dict[str, Any]:
    """
    Experiment H (Phase 10): Compare Parser A (Deterministic Rule-Based Parser) and
    Parser B (Optional LLM-Based Parser) on both:
      1. Parser-only field extraction accuracy against gold structured claim fields.
      2. End-to-end verification performance through the unchanged FieldGuardVerifier.
    If no live LLM API provider is configured in environment variables, records live
    API status as SKIPPED with an explicit reason and runs all offline parser checks.
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parents[3]

    results_dir = project_root / "results"
    for sub in ("metrics", "tables", "predictions"):
        (results_dir / sub).mkdir(parents=True, exist_ok=True)

    store = build_default_evidence_store(project_root)
    retrievers = build_all_retrievers(store)
    ret_hybrid = retrievers["hybrid"]
    claims = load_benchmark_claims(project_root, split=split)

    det_parser = DeterministicClaimParser()
    llm_parser = LLMClaimParser(LLMParserConfig.from_env(project_root))
    llm_available, llm_status_msg = llm_parser.is_available()

    eval_fields = (
        "scheme",
        "claimed_value",
        "claimed_unit",
        "numeric_operator",
        "crop_category",
        "season",
        "qualification",
        "requested_policy_version",
        "requested_effective_date",
    )

    # Evaluate Parser A (Deterministic)
    det_field_matches: dict[str, int] = {f: 0 for f in eval_fields}
    det_exact_all = 0
    det_schema_valid = 0
    det_missing_fields = 0
    det_parse_failures = 0
    det_lats: list[float] = []
    det_e2e_verdicts: list[str] = []
    det_e2e_lats: list[float] = []
    parser_predictions_log: list[dict[str, Any]] = []

    verifier = FieldGuardVerifier(evidence_store=store, config=VerifierConfig(config_name="fieldguard_full"))

    for clm in claims:
        t0 = time.perf_counter()
        parsed_a = det_parser.parse(clm.question, clm.candidate_claim)
        p_lat = (time.perf_counter() - t0) * 1000.0
        det_lats.append(p_lat)

        p_dict = parsed_a.to_dict()
        s_valid, _ = validate_parsed_claim_schema(p_dict)
        if s_valid:
            det_schema_valid += 1
        if parsed_a.parse_status == "failed_malformed":
            det_parse_failures += 1
        if len(parsed_a.uncertain_fields) > 0:
            det_missing_fields += 1

        all_f_match = True
        clm_dict = clm.to_dict()
        for ef in eval_fields:
            g_val = clm_dict.get(ef)
            p_val = p_dict.get(ef)
            if ef == "claimed_value" and g_val is not None and p_val is not None:
                match = abs(float(g_val) - float(p_val)) < 1e-6
            else:
                match = g_val == p_val
            if match:
                det_field_matches[ef] += 1
            else:
                all_f_match = False
        if all_f_match:
            det_exact_all += 1

        ret_items, ret_lat = _resolve_retrieved_items_for_claim(clm, ret_hybrid, store, top_k=5)
        e2e_pred = verifier.verify_claim(
            claim_id=clm.claim_id,
            question=clm.question,
            candidate_claim=clm.candidate_claim,
            retrieved_items=ret_items,
            retrieval_method="hybrid",
            retrieval_latency_ms=ret_lat + p_lat,
            pre_parsed_claim=parsed_a,
        )
        det_e2e_verdicts.append(e2e_pred.predicted_verdict)
        det_e2e_lats.append(e2e_pred.latency_ms)

        parser_predictions_log.append(
            {
                "parser": "Parser_A_Deterministic_Rule_Based",
                "status": "SUCCESS",
                "claim_id": clm.claim_id,
                "parsed_claim": p_dict,
                "gold_verdict": clm.gold_verdict,
                "predicted_verdict": e2e_pred.predicted_verdict,
                "parse_latency_ms": round(p_lat, 4),
            }
        )

    n = len(claims)
    gold_verdicts = [c.gold_verdict for c in claims]
    det_vm = compute_verification_metrics(
        gold_verdicts=gold_verdicts,
        predicted_verdicts=det_e2e_verdicts,
        e2e_latencies_ms=det_e2e_lats,
        config_name="Parser_A_Deterministic_Rule_Based",
    )

    field_rows: list[dict[str, Any]] = []
    for ef in eval_fields:
        field_rows.append(
            {
                "parser": "Parser_A_Deterministic_Rule_Based",
                "status": "SUCCESS",
                "field_name": ef,
                "n_claims": n,
                "exact_match_count": det_field_matches[ef],
                "exact_match_accuracy": round(det_field_matches[ef] / float(n), 4),
            }
        )

    comparison_rows: list[dict[str, Any]] = [
        {
            "parser_name": "Parser_A_Deterministic_Rule_Based",
            "experiment_status": "SUCCESS",
            "status_reason": "Executed offline deterministic rule-based parser on all benchmark claims.",
            "n_claims": n,
            "all_fields_exact_match_rate": round(det_exact_all / float(n), 4),
            "claimed_value_accuracy": round(det_field_matches["claimed_value"] / float(n), 4),
            "claimed_unit_accuracy": round(det_field_matches["claimed_unit"] / float(n), 4),
            "crop_category_accuracy": round(det_field_matches["crop_category"] / float(n), 4),
            "season_accuracy": round(det_field_matches["season"] / float(n), 4),
            "qualification_accuracy": round(det_field_matches["qualification"] / float(n), 4),
            "temporal_scope_accuracy": round(det_field_matches["requested_policy_version"] / float(n), 4),
            "schema_valid_rate": round(det_schema_valid / float(n), 4),
            "missing_field_rate": round(det_missing_fields / float(n), 4),
            "unsupported_inference_rate": 0.0,
            "parse_failure_rate": round(det_parse_failures / float(n), 4),
            "parser_mean_latency_ms": round(float(np.mean(det_lats)), 4),
            "estimated_cost_usd": 0.0,
            "e2e_verdict_accuracy": det_vm["accuracy"],
            "e2e_macro_f1": det_vm["macro_f1"],
            "e2e_false_support_rate": det_vm["false_support_rate"],
            "e2e_wrong_context_error_rate": round(1.0 - det_vm["wrong_context_recall"], 4),
            "e2e_unverifiable_error_rate": round(1.0 - det_vm["unverifiable_recall"], 4),
            "e2e_coverage": det_vm["coverage"],
            "e2e_abstention_rate": det_vm["abstention_rate"],
            "e2e_mean_latency_ms": det_vm["e2e_latency_mean_ms"],
        }
    ]

    if not llm_available:
        comparison_rows.append(
            {
                "parser_name": "Parser_B_Optional_LLM",
                "experiment_status": "SKIPPED",
                "status_reason": llm_status_msg,
                "n_claims": n,
                "all_fields_exact_match_rate": None,
                "claimed_value_accuracy": None,
                "claimed_unit_accuracy": None,
                "crop_category_accuracy": None,
                "season_accuracy": None,
                "qualification_accuracy": None,
                "temporal_scope_accuracy": None,
                "schema_valid_rate": None,
                "missing_field_rate": None,
                "unsupported_inference_rate": None,
                "parse_failure_rate": None,
                "parser_mean_latency_ms": None,
                "estimated_cost_usd": None,
                "e2e_verdict_accuracy": None,
                "e2e_macro_f1": None,
                "e2e_false_support_rate": None,
                "e2e_wrong_context_error_rate": None,
                "e2e_unverifiable_error_rate": None,
                "e2e_coverage": None,
                "e2e_abstention_rate": None,
                "e2e_mean_latency_ms": None,
            }
        )

    with (results_dir / "metrics" / "claim_parser_comparison.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(comparison_rows[0].keys()))
        writer.writeheader()
        writer.writerows(comparison_rows)

    with (results_dir / "tables" / "claim_parser_field_metrics.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(field_rows[0].keys()))
        writer.writeheader()
        writer.writerows(field_rows)

    with (results_dir / "predictions" / "claim_parser_predictions.jsonl").open("w", encoding="utf-8") as f:
        for p in parser_predictions_log:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    _write_claim_parser_analysis_doc(
        comparison_rows=comparison_rows,
        field_rows=field_rows,
        doc_path=project_root / "docs" / "claim_parser_analysis.md",
    )

    return {
        "status": "SUCCESS_OFFLINE_LLM_SKIPPED" if not llm_available else "SUCCESS",
        "llm_available": llm_available,
        "llm_status_reason": llm_status_msg,
        "comparison_rows": comparison_rows,
        "field_rows": field_rows,
    }


def _write_claim_parser_analysis_doc(
    comparison_rows: list[dict[str, Any]],
    field_rows: list[dict[str, Any]],
    doc_path: Path,
) -> None:
    r_det = comparison_rows[0]
    r_llm = comparison_rows[1] if len(comparison_rows) > 1 else None

    lines = [
        "# FieldGuard — Claim Parser Comparison Analysis (Phase 10)",
        "",
        "## 1. Experimental Setup",
        "",
        "Phase 10 compares two structured claim parsers that map `(question, candidate_claim)` into the validated `ParsedClaim` schema before passing the structured claim into the unchanged `FieldGuardVerifier`:",
        "",
        "- **Parser A (`DeterministicClaimParser`):** Offline deterministic regex and rule-based normalizer (`src/fieldguard/claim_parser.py`).",
        "- **Parser B (`LLMClaimParser`):** Optional LLM-based JSON extractor with strict schema validation and unsupported-inference rejection (`src/fieldguard/claim_parser_llm.py`).",
        "",
        "## 2. Parser-Only Field Extraction Metrics (Parser A on Test Split)",
        "",
        "| Structured Claim Field | Evaluated Claims ($n$) | Exact Matches | Exact-Match Accuracy |",
        "| :--- | :---: | :---: | :---: |",
    ]
    for fr in field_rows:
        lines.append(
            f"| `{fr['field_name']}` | {fr['n_claims']} | {fr['exact_match_count']} | {fr['exact_match_accuracy']:.4f} |"
        )

    lines.extend(
        [
            "",
            "## 3. End-to-End Verification & Parser Comparison Summary",
            "",
            f"- **Parser A (`DeterministicClaimParser`):** Status = `{r_det['experiment_status']}` | All-Fields Exact Match = `{r_det['all_fields_exact_match_rate']:.4f}` | Schema-Valid Rate = `{r_det['schema_valid_rate']:.4f}` | Unsupported-Inference Rate = `{r_det['unsupported_inference_rate']:.4f}` | Mean Parse Latency = `{r_det['parser_mean_latency_ms']:.4f} ms` | End-to-End Verdict Accuracy = `{r_det['e2e_verdict_accuracy']:.4f}` | End-to-End Macro-F1 = `{r_det['e2e_macro_f1']:.4f}` | End-to-End False-Support Rate = `{r_det['e2e_false_support_rate']:.4f}`.",
        ]
    )
    if r_llm is not None:
        lines.append(
            f"- **Parser B (`LLMClaimParser`):** Status = `{r_llm['experiment_status']}` | Reason = {r_llm['status_reason']}"
        )

    lines.extend(
        [
            "",
            "## 4. Safety Guarantees Verified in `tests/test_claim_parser_llm.py`",
            "",
            "1. **No Verdict Bypass:** `LLMClaimParser` extracts only structured claim fields (`ParsedClaim`); any injected `predicted_verdict` or `gold_verdict` key in the LLM JSON is ignored and cannot bypass `FieldGuardVerifier`.",
            "2. **Malformed JSON Rejection:** Truncated or non-JSON responses are caught and converted to `parse_status='failed_malformed'`, causing `FieldGuardVerifier` to abstain (`UNVERIFIABLE`) rather than emit a false support.",
            "3. **Unsupported Inference Rejection:** `detect_unsupported_llm_inferences` strips hallucinated crop categories, seasons, or effective dates that do not appear in the user's question or claim, preserving `uncertain_fields`.",
        ]
    )
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_computational_performance_benchmark(
    project_root: Path | None = None,
    split: str = "test",
    n_runs: int = 3,
) -> dict[str, Any]:
    """
    Experiment I (Phase 12): Measure retrieval latency, verification latency, end-to-end latency,
    and approximate peak memory footprint across `n_runs` after warm-up.
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parents[3]

    results_dir = project_root / "results" / "metrics"
    results_dir.mkdir(parents=True, exist_ok=True)

    tracemalloc.start()
    store = build_default_evidence_store(project_root)
    retrievers = build_all_retrievers(store)
    claims = load_benchmark_claims(project_root, split=split)
    verifier = FieldGuardVerifier(evidence_store=store)

    # Warm-up pass on 5 claims
    for clm in claims[:5]:
        q = f"{clm.question} {clm.candidate_claim}"
        for r in retrievers.values():
            _ = r.retrieve(q, top_k=5)

    rows: list[dict[str, Any]] = []
    for r_name in ("semantic", "lexical", "table", "hybrid"):
        ret = retrievers[r_name]
        ret_lats: list[float] = []
        ver_lats: list[float] = []
        e2e_lats: list[float] = []

        for _ in range(n_runs):
            for clm in claims:
                ret_items, r_lat = _resolve_retrieved_items_for_claim(clm, ret, store, top_k=5)
                pred = verifier.verify_claim(
                    claim_id=clm.claim_id,
                    question=clm.question,
                    candidate_claim=clm.candidate_claim,
                    retrieved_items=ret_items,
                    retrieval_method=r_name,
                    retrieval_latency_ms=r_lat,
                )
                ret_lats.append(r_lat)
                ver_lats.append(pred.verification_latency_ms)
                e2e_lats.append(pred.latency_ms)

        _, peak_bytes = tracemalloc.get_traced_memory()
        peak_mb = peak_bytes / (1024.0 * 1024.0)

        rows.append(
            {
                "pipeline_configuration": f"fieldguard_with_{r_name}_retrieval",
                "n_runs": n_runs,
                "queries_per_run": len(claims),
                "total_evaluations": len(ret_lats),
                "retrieval_latency_mean_ms": round(float(np.mean(ret_lats)), 4),
                "retrieval_latency_median_ms": round(float(np.median(ret_lats)), 4),
                "retrieval_latency_p95_ms": round(float(np.percentile(ret_lats, 95)), 4),
                "verification_latency_mean_ms": round(float(np.mean(ver_lats)), 4),
                "verification_latency_median_ms": round(float(np.median(ver_lats)), 4),
                "verification_latency_p95_ms": round(float(np.percentile(ver_lats, 95)), 4),
                "e2e_latency_mean_ms": round(float(np.mean(e2e_lats)), 4),
                "e2e_latency_median_ms": round(float(np.median(e2e_lats)), 4),
                "e2e_latency_p95_ms": round(float(np.percentile(e2e_lats, 95)), 4),
                "traced_peak_memory_mb": round(peak_mb, 2),
                "python_version": sys.version.split()[0],
                "platform": platform.platform(),
                "processor": platform.processor() or "x86_64_cpu",
                "embedding_model_id": "sentence-transformers/all-MiniLM-L6-v2",
                "warmup_queries": 5,
            }
        )

    tracemalloc.stop()

    comp_csv = results_dir / "computational_performance.csv"
    with comp_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return {
        "status": "SUCCESS",
        "rows": rows,
    }


def run_complete_evaluation_pipeline(project_root: Path | None = None) -> dict[str, Any]:
    """
    Orchestrate all experiments (Experiments A through I), save structured logs,
    and return the complete empirical summary.
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parents[3]

    store = build_default_evidence_store(project_root)
    retrievers = build_all_retrievers(store)
    test_claims = load_benchmark_claims(project_root, split="test")
    dev_claims = load_benchmark_claims(project_root, split="dev")

    exp_a = run_retrieval_experiment(project_root, split="test")
    exp_b_f = run_verification_experiment(project_root, split="test", bootstrap_iterations=1000)
    exp_b_dev = run_verification_experiment(project_root, split="dev", bootstrap_iterations=500)
    # Re-run test so primary CSVs in results/ reflect the frozen test split
    exp_b_f = run_verification_experiment(project_root, split="test", bootstrap_iterations=1000)
    exp_g = run_ablation_suite(
        claims=test_claims,
        store=store,
        retrievers=retrievers,
        project_root=project_root,
        bootstrap_iterations=500,
    )
    exp_h = run_claim_parser_comparison(project_root, split="test")
    exp_i = run_computational_performance_benchmark(project_root, split="test", n_runs=3)

    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    master_log = {
        "executed_at_utc": now_utc,
        "random_seed": 42,
        "test_split_claims": len(test_claims),
        "dev_split_claims": len(dev_claims),
        "experiment_statuses": {
            "Experiment_A_Retrieval_Quality": exp_a["status"],
            "Experiment_B_Verification_Performance": exp_b_f["status"],
            "Experiment_C_False_Support_Reduction": exp_b_f["status"],
            "Experiment_D_Context_Perturbations": exp_b_f["status"],
            "Experiment_E_Missing_Misleading_Evidence": exp_b_f["status"],
            "Experiment_F_Temporal_Grounding": exp_b_f["status"],
            "Experiment_G_Ablation_Study": "SUCCESS",
            "Experiment_H_Claim_Parser_Comparison": exp_h["status"],
            "Experiment_I_Computational_Performance": exp_i["status"],
        },
        "retrieval_summary_test": exp_a["comparison"],
        "verification_summary_test": exp_b_f["summary_rows"],
        "verification_summary_dev": exp_b_dev["summary_rows"],
        "fsr_breakdown_test": exp_b_f["fsr_breakdown"],
        "perturbation_breakdown_test": exp_b_f["perturbation_breakdown"],
        "regime_breakdown_test": exp_b_f["regime_breakdown"],
        "temporal_breakdown_test": exp_b_f["temporal_breakdown"],
        "paired_statistical_tests_test": exp_b_f["paired_statistical_tests"],
        "ablation_summary_test": exp_g["ablation_comparison"],
        "parser_comparison_test": exp_h["comparison_rows"],
        "computational_performance_test": exp_i["rows"],
    }

    log_path = project_root / "results" / "logs" / "experiment_master_log.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as f:
        json.dump(master_log, f, indent=2, ensure_ascii=False)

    return master_log


def _plot_multi_scheme_verification_figure(
    rows: list[dict[str, Any]],
    output_path: Path,
    scheme_title: str = "PM-KISAN",
) -> None:
    labels = [
        r["method_name"]
        .replace("baseline_a_retrieval_only", "Baseline A\n(Retrieval-Only)")
        .replace("baseline_b_numeric_only", "Baseline B\n(Numeric-Only)")
        .replace("baseline_c_numeric_basic_context", "Baseline C\n(Basic Context)")
        .replace("fieldguard_full", "FieldGuard\n(Condition-Aware)")
        for r in rows
    ]
    acc = [r["accuracy"] * 100.0 for r in rows]
    fsr = [r["false_support_rate"] * 100.0 for r in rows]
    cov = [r["decision_coverage"] * 100.0 for r in rows]

    x = np.arange(len(labels))
    w = 0.25

    fig, ax = plt.subplots(figsize=(9.2, 5.2), dpi=150)
    b1 = ax.bar(x - w, acc, w, label="Accuracy (%)", color="#2b5c8f")
    b2 = ax.bar(x, fsr, w, label="False Support Rate (%)", color="#d95f02")
    b3 = ax.bar(x + w, cov, w, label="Decision Coverage (%)", color="#7570b3")

    for bar in list(b1) + list(b2) + list(b3):
        h = bar.get_height()
        if h > 0.0:
            ax.annotate(
                f"{h:.1f}%",
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8.5,
            )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_ylim(0, 115)
    ax.set_ylabel("Percentage (%)")
    ax.set_title(f"FieldGuard Stage 2: {scheme_title} Multi-Scheme Verification Performance")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.legend(loc="upper right", fontsize=9.5)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output_path))
    plt.close(fig)


def _plot_multi_scheme_ablation_figure(
    rows: list[dict[str, Any]],
    output_path: Path,
    scheme_title: str = "PM-KISAN",
) -> None:
    labels = [r["ablation_label"] for r in rows][::-1]
    acc = [r["accuracy"] * 100.0 for r in rows][::-1]
    fsr = [r["false_support_rate"] * 100.0 for r in rows][::-1]

    y = np.arange(len(labels))
    h = 0.35

    fig, ax = plt.subplots(figsize=(10.0, 5.8), dpi=150)
    ax.barh(y + h / 2, acc, h, label="Accuracy (%)", color="#2b5c8f")
    ax.barh(y - h / 2, fsr, h, label="False Support Rate (%)", color="#d95f02")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlim(0, 115)
    ax.set_xlabel("Percentage (%)")
    ax.set_title(f"FieldGuard Stage 2: {scheme_title} Component Ablation Study")
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.legend(loc="lower right", fontsize=9.5)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output_path))
    plt.close(fig)


def run_multi_scheme_experiment(
    scheme: str = "pm_kisan",
    split: str = "test",
    project_root: Path | None = None,
    bootstrap_iterations: int = 500,
) -> dict[str, Any]:
    """
    Run the end-to-end multi-scheme evaluation pipeline on the specified government scheme.
    Evaluates:
      1. Retrieval Recall and MRR across semantic, lexical, table-aware, and hybrid retrieval.
      2. Verification performance across Baselines A, B, C, and Full FieldGuard with cluster bootstrap CIs.
      3. Component ablation study (IR, condition matching, entity scope, frequency, exclusions, temporal, sufficiency).
    Saves tables, metrics, predictions, and figures to results/{scheme}/.
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parents[3]

    clean_scheme = scheme.lower().replace("-", "_")
    results_dir = project_root / "results" / clean_scheme
    for sub in ("metrics", "tables", "predictions", "figures", "logs"):
        (results_dir / sub).mkdir(parents=True, exist_ok=True)

    # 1. Load appropriate scheme store and benchmark claims
    if clean_scheme in ("pm_kisan", "pmkisan"):
        from fieldguard.evidence_store import build_pm_kisan_evidence_store
        from fieldguard.pm_kisan_benchmark import load_pm_kisan_benchmark_claims

        store = build_pm_kisan_evidence_store(project_root)
        claims = load_pm_kisan_benchmark_claims(project_root, split=split)
    else:
        store = build_default_evidence_store(project_root)
        claims = load_benchmark_claims(project_root, split=split)

    retrievers = build_all_retrievers(store)
    corpus_ids = set(store.evidence_units.keys())

    # 2. Retrieval Evaluation
    retrieval_comparison_rows: list[dict[str, Any]] = []
    for r_name in ("semantic", "lexical", "table", "hybrid"):
        ret = retrievers[r_name]
        eval_records = []
        latencies_ms: list[float] = []

        for clm in claims:
            q_text = f"{clm.question} {clm.candidate_claim}".strip()
            t0 = time.perf_counter()
            ranked = ret.retrieve(q_text, top_k=10)
            lat_ms = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(lat_ms)

            ret_ids = [it.evidence_id for it in ranked]
            rec = evaluate_single_query_retrieval(
                claim_id=clm.claim_id,
                claim_family_id=clm.claim_family_id,
                claim_type=clm.claim_type,
                retriever_name=r_name,
                retrieved_ids=ret_ids,
                gold_evidence_ids=clm.gold_evidence_ids,
                indexed_corpus_ids=corpus_ids,
            )
            eval_records.append(rec)

        agg = aggregate_retrieval_metrics(eval_records, retriever_name=r_name)
        mean_lat = float(np.mean(latencies_ms)) if latencies_ms else 0.0
        retrieval_comparison_rows.append(
            {
                "scheme": clean_scheme,
                "retriever_name": r_name,
                "split": split,
                "total_queries": agg["total_queries"],
                "eligible_query_count": agg["eligible_query_count"],
                "hits_at_1": agg["hits_at_1"],
                "hits_at_3": agg["hits_at_3"],
                "hits_at_5": agg["hits_at_5"],
                "hits_at_10": agg.get("hits_at_10", 0),
                "recall_at_1": agg["recall_at_1"],
                "recall_at_3": agg["recall_at_3"],
                "recall_at_5": agg["recall_at_5"],
                "recall_at_10": agg["recall_at_10"],
                "item_recall_at_5": agg["item_recall_at_5"],
                "mrr": agg["mrr"],
                "mean_latency_ms": round(mean_lat, 4),
            }
        )

    with (results_dir / "tables" / "retrieval_comparison.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(retrieval_comparison_rows[0].keys()))
        w.writeheader()
        w.writerows(retrieval_comparison_rows)

    _plot_retrieval_figure(retrieval_comparison_rows, results_dir / "figures" / "retrieval_comparison.png")

    # 3. Verification Evaluation across Baselines A, B, C, D
    configs = get_comparison_baseline_configs()
    gold_verdicts = [c.gold_verdict for c in claims]
    family_ids = [c.claim_family_id for c in claims]
    summary_rows: list[dict[str, Any]] = []
    preds_by_method: dict[str, list[dict[str, Any]]] = {}

    for cfg in configs:
        verifier = FieldGuardVerifier(evidence_store=store, config=cfg)
        ret_engine = retrievers[cfg.retrieval_method]
        m_preds_str: list[str] = []
        m_preds_dicts: list[dict[str, Any]] = []
        lats: list[float] = []

        for clm in claims:
            ret_items, ret_lat = _resolve_retrieved_items_for_claim(
                claim=clm,
                retriever=ret_engine,
                store=store,
                top_k=cfg.top_k,
            )
            pred = verifier.verify_claim(
                claim_id=clm.claim_id,
                question=clm.question,
                candidate_claim=clm.candidate_claim,
                retrieved_items=ret_items,
                retrieval_method=cfg.retrieval_method,
                retrieval_latency_ms=ret_lat,
            )
            m_preds_str.append(pred.predicted_verdict)
            m_preds_dicts.append(pred.to_dict())
            lats.append(pred.latency_ms)

        preds_by_method[cfg.config_name] = m_preds_dicts

        # Compute metrics
        m = compute_verification_metrics(gold_verdicts, m_preds_str)
        cis = compute_cluster_bootstrap_cis(
            claim_family_ids=family_ids,
            gold_verdicts=gold_verdicts,
            predicted_verdicts=m_preds_str,
            n_iterations=bootstrap_iterations,
        )
        row = {
            "scheme": clean_scheme,
            "method_name": cfg.config_name,
            "split": split,
            "sample_size": len(claims),
            "accuracy": m["accuracy"],
            "accuracy_ci_lower": cis["accuracy"]["ci_lower"],
            "accuracy_ci_upper": cis["accuracy"]["ci_upper"],
            "false_support_rate": m["false_support_rate"],
            "fsr_ci_lower": cis["false_support_rate"]["ci_lower"],
            "fsr_ci_upper": cis["false_support_rate"]["ci_upper"],
            "decision_coverage": m["coverage"],
            "macro_f1": m["macro_f1"],
            "supported_f1": m["supported_f1"],
            "contradicted_f1": m["contradicted_f1"],
            "wrong_context_f1": m["wrong_context_f1"],
            "unverifiable_f1": m["unverifiable_f1"],
            "mean_latency_ms": round(float(np.mean(lats)), 4) if lats else 0.0,
        }
        summary_rows.append(row)

    with (results_dir / "tables" / "verification_comparison.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)

    with (results_dir / "predictions" / "verification_predictions.jsonl").open("w", encoding="utf-8") as f:
        for m_name, p_list in preds_by_method.items():
            for p in p_list:
                p_copy = dict(p)
                p_copy["method_name"] = m_name
                p_copy["scheme"] = clean_scheme
                f.write(json.dumps(p_copy, ensure_ascii=False) + "\n")

    _plot_multi_scheme_verification_figure(
        summary_rows,
        results_dir / "figures" / "verification_comparison.png",
        scheme_title="PM-KISAN" if clean_scheme in ("pm_kisan", "pmkisan") else clean_scheme.upper(),
    )

    # 4. Multi-Scheme Ablation Study
    ablation_configs = [
        ("Full FieldGuard", VerifierConfig(config_name="fieldguard_full", mode="fieldguard")),
        ("Ablation 1: Semantic IR Only", VerifierConfig(config_name="ablation_semantic_only", mode="fieldguard", retrieval_method="semantic")),
        ("Ablation 2: Without Condition Matching", VerifierConfig(config_name="ablation_no_condition_matching", mode="fieldguard", enable_structured_condition_matching=False)),
        ("Ablation 3: Without Entity Scope Matching", VerifierConfig(config_name="ablation_no_entity_scope", mode="fieldguard", enable_crop_category_matching=False)),
        ("Ablation 4: Without Frequency Matching", VerifierConfig(config_name="ablation_no_frequency", mode="fieldguard", enable_season_matching=False)),
        ("Ablation 5: Without Exclusion Matching", VerifierConfig(config_name="ablation_no_exclusions", mode="fieldguard", enable_qualification_matching=False)),
        ("Ablation 6: Without Temporal Checks", VerifierConfig(config_name="ablation_no_temporal", mode="fieldguard", enable_temporal_checks=False)),
        ("Ablation 7: Without Sufficiency Gate", VerifierConfig(config_name="ablation_no_sufficiency", mode="fieldguard", enable_evidence_sufficiency=False)),
    ]
    ablation_rows: list[dict[str, Any]] = []
    for ab_label, ab_cfg in ablation_configs:
        v = FieldGuardVerifier(evidence_store=store, config=ab_cfg)
        ret_engine = retrievers[ab_cfg.retrieval_method]
        ab_preds = []
        for clm in claims:
            r_items, r_lat = _resolve_retrieved_items_for_claim(clm, ret_engine, store, top_k=ab_cfg.top_k)
            p = v.verify_claim(clm.claim_id, clm.question, clm.candidate_claim, r_items, ab_cfg.retrieval_method, r_lat)
            ab_preds.append(p.predicted_verdict)
        ab_m = compute_verification_metrics(gold_verdicts, ab_preds)
        ablation_rows.append(
            {
                "ablation_label": ab_label,
                "config_name": ab_cfg.config_name,
                "accuracy": ab_m["accuracy"],
                "false_support_rate": ab_m["false_support_rate"],
                "decision_coverage": ab_m["coverage"],
                "macro_f1": ab_m["macro_f1"],
            }
        )

    with (results_dir / "tables" / "ablation_comparison.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ablation_rows[0].keys()))
        w.writeheader()
        w.writerows(ablation_rows)

    _plot_multi_scheme_ablation_figure(
        ablation_rows,
        results_dir / "figures" / "ablation_study.png",
        scheme_title="PM-KISAN" if clean_scheme in ("pm_kisan", "pmkisan") else clean_scheme.upper(),
    )

    return {
        "status": "SUCCESS",
        "scheme": clean_scheme,
        "split": split,
        "retrieval": retrieval_comparison_rows,
        "verification": summary_rows,
        "ablation": ablation_rows,
    }
