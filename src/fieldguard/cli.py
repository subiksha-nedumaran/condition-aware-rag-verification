"""FieldGuard unified command-line interface (CLI).

Supports all operational and experimental research commands specified in Section 18:
  - python -m fieldguard.cli sources validate
  - python -m fieldguard.cli ingest
  - python -m fieldguard.cli index build
  - python -m fieldguard.cli retrieve --query "..."
  - python -m fieldguard.cli verify --claim "..."
  - python -m fieldguard.cli evaluate retrieval
  - python -m fieldguard.cli evaluate verification
  - python -m fieldguard.cli evaluate ablations
  - python -m fieldguard.cli evaluate errors
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from fieldguard.benchmark_builder import load_benchmark_claims
from fieldguard.claim_parser import DeterministicClaimParser
from fieldguard.data_acquisition import run_acquisition_pipeline
from fieldguard.document_extraction import run_extraction_pipeline
from fieldguard.evaluation.ablation import run_ablation_suite
from fieldguard.evaluation.error_analysis import generate_error_analysis_report
from fieldguard.evaluation.runner import (
    build_all_retrievers,
    run_retrieval_experiment,
    run_verification_experiment,
)
from fieldguard.evidence_store import build_default_evidence_store
from fieldguard.source_manifest import load_source_manifest, validate_source_manifest
from fieldguard.verifier import FieldGuardVerifier, VerifierConfig


def _get_project_root() -> Path:
    # Works when invoked as python -m fieldguard.cli or via installed package
    curr = Path.cwd().resolve()
    if (curr / "data" / "manifests").exists():
        return curr
    for parent in Path(__file__).resolve().parents:
        if (parent / "data" / "manifests").exists():
            return parent
    return curr


def cmd_sources_validate(args: argparse.Namespace) -> int:
    root = _get_project_root()
    manifest_path = root / "data" / "manifests" / "source_manifest.json"
    if not manifest_path.exists():
        print(f"Error: source manifest not found at {manifest_path}", file=sys.stderr)
        return 1

    manifest = load_source_manifest(manifest_path)
    is_valid, errors = validate_source_manifest(manifest, root)
    official_count = sum(1 for d in manifest.documents if d.verification_status == "trusted_official")
    secondary_count = len(manifest.documents) - official_count

    print(f"=== FieldGuard Source Manifest Validation ===")
    print(f"Manifest Path : {manifest_path}")
    print(f"Total Sources : {len(manifest.documents)}")
    print(f"Official Auth : {official_count}")
    print(f"Secondary/Unv : {secondary_count}")
    print(f"Manifest Status: {'VALID' if is_valid else 'INVALID'}")

    if errors:
        print("\nValidation Errors / Warnings:")
        for err in errors:
            print(f"  - {err}")

    return 0 if is_valid else 1


def cmd_ingest(args: argparse.Namespace) -> int:
    root = _get_project_root()
    print("=== Step 1: Running Data Acquisition and Source Manifest Generation ===")
    acq_report = run_acquisition_pipeline(root)
    print(f"Acquisition completed: {acq_report['total_manifest_entries']} manifest entries verified.")

    print("\n=== Step 2: Running Document & Structured Table Extraction ===")
    ext_report = run_extraction_pipeline(root)
    print(
        f"Extraction completed: {ext_report.total_chunks} chunks, {ext_report.total_table_rows} table rows extracted."
    )
    print(f"Outputs saved to: {root / 'data' / 'processed'}")
    return 0


def cmd_index_build(args: argparse.Namespace) -> int:
    root = _get_project_root()
    print("=== Building / Refreshing FieldGuard Retrieval Indexes ===")
    store = build_default_evidence_store(root)
    print(f"Loaded evidence store: {len(store.evidence_units)} evidence units, {len(store.trusted_rules)} rules.")

    retrievers = build_all_retrievers(store)
    print("Indexes built successfully:")
    for name, r in retrievers.items():
        count = len(getattr(r, "corpus_units", []))
        print(f"  - {name.capitalize()} retriever: {count} indexed units")

    cache_file = root / "cache" / "embeddings" / "minilm_l6_v2_corpus_cache.npz"
    if cache_file.exists():
        print(f"Semantic embedding cache verified: {cache_file} ({cache_file.stat().st_size} bytes)")
    return 0


def cmd_retrieve(args: argparse.Namespace) -> int:
    root = _get_project_root()
    store = build_default_evidence_store(root)
    retrievers = build_all_retrievers(store)

    retriever = retrievers.get(args.method)
    if not retriever:
        print(f"Error: Unknown retrieval method '{args.method}'. Choose from: {list(retrievers.keys())}", file=sys.stderr)
        return 1

    results = retriever.retrieve(args.query, top_k=args.top_k)
    output = {
        "query": args.query,
        "method": args.method,
        "top_k": args.top_k,
        "results_count": len(results),
        "results": [
            {
                "rank": idx + 1,
                "evidence_id": r.evidence_id,
                "source_document_id": r.source_document_id,
                "page": r.physical_pdf_page,
                "score": round(r.retrieval_score, 4),
                "is_table_row": (r.evidence_type == "table_row"),
                "text": r.text,
            }
            for idx, r in enumerate(results)
        ],
    }

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(f"=== FieldGuard Retrieval Results (Method: {args.method}, Query: '{args.query}') ===")
        for res in output["results"]:
            print(f"\n[Rank {res['rank']}] Score: {res['score']} | ID: {res['evidence_id']} | Source: {res['source_document_id']} (Page {res['page']})")
            print(f"    {res['text']}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    root = _get_project_root()
    store = build_default_evidence_store(root)
    retrievers = build_all_retrievers(store)

    retriever = retrievers.get(args.method, retrievers["hybrid"])
    query = f"{args.question or ''} {args.claim}".strip()
    ret_items = [r.to_dict() for r in retriever.retrieve(query, top_k=args.top_k)]

    verifier = FieldGuardVerifier(evidence_store=store, config=VerifierConfig(retrieval_method=args.method))
    pred = verifier.verify_claim(
        claim_id=args.claim_id or "CLI_CLAIM_001",
        question=args.question or args.claim,
        candidate_claim=args.claim,
        retrieved_items=ret_items,
    )

    # Build standardized machine-readable output schema specified in Section 19
    checks: dict[str, str] = {
        "numeric_match": "unknown",
        "category_match": "unknown",
        "season_match": "unknown",
        "qualification_match": "unknown",
        "temporal_match": "unknown",
        "source_authority": "unknown",
    }
    warnings: list[str] = []

    if pred.predicted_verdict == "SUPPORTED":
        checks = {k: "passed" for k in checks}
    elif pred.predicted_verdict == "WRONG_CONTEXT":
        checks["numeric_match"] = "passed"
        checks["source_authority"] = "passed"
        mismatches = " ".join(pred.context_mismatch).lower()
        checks["category_match"] = "failed" if "crop" in mismatches else "passed"
        checks["season_match"] = "failed" if "season" in mismatches else "passed"
        checks["temporal_match"] = "failed" if ("temporal" in mismatches or "version" in mismatches) else "passed"
    elif pred.predicted_verdict == "CONTRADICTED":
        checks["numeric_match"] = "failed"
        checks["category_match"] = "passed"
        checks["season_match"] = "passed"
        checks["temporal_match"] = "passed"
        checks["source_authority"] = "passed"
    elif pred.predicted_verdict == "UNVERIFIABLE":
        checks["temporal_match"] = pred.temporal_status
        checks["numeric_match"] = "unknown (insufficient applicable evidence)"

    if pred.predicted_verdict == "UNVERIFIABLE":
        warnings.append(pred.abstention_reason or "Insufficient applicable evidence")
    if pred.context_mismatch:
        warnings.extend(pred.context_mismatch)

    formatted_output = {
        "claim_id": pred.claim_id,
        "claim": args.claim,
        "parsed_claim": pred.parsed_claim,
        "verdict": pred.predicted_verdict,
        "reason": pred.verification_rationale,
        "supporting_evidence_ids": pred.supporting_evidence_ids,
        "contradicting_evidence_ids": pred.contradicting_evidence_ids,
        "evidence": [
            {
                "evidence_id": item["evidence_id"],
                "source_document_id": item["source_document_id"],
                "page": item.get("physical_pdf_page"),
                "score": round(item.get("retrieval_score", 0.0), 4),
                "text": item.get("text"),
            }
            for item in ret_items[:args.top_k]
        ],
        "checks": checks,
        "warnings": warnings,
        "latency_ms": round(pred.latency_ms, 2),
    }

    if args.json:
        print(json.dumps(formatted_output, indent=2))
    else:
        print("=== FieldGuard Numerical Claim Verification ===")
        print(f"Claim   : {args.claim}")
        print(f"Verdict : {pred.predicted_verdict}")
        print(f"Reason  : {pred.verification_rationale}")
        print(f"Checks  :")
        for k, v in checks.items():
            print(f"  - {k:<20}: {v.upper()}")
        if warnings:
            print(f"Warnings: {'; '.join(warnings)}")
        print(f"Latency : {round(pred.latency_ms, 2)} ms")
        if pred.supporting_evidence_ids:
            print(f"Supporting Evidence IDs: {', '.join(pred.supporting_evidence_ids)}")
        elif pred.contradicting_evidence_ids:
            print(f"Contradicting Evidence IDs: {', '.join(pred.contradicting_evidence_ids)}")

    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    root = _get_project_root()
    target = args.eval_target

    if target == "retrieval":
        print(f"=== Evaluating Retrieval Quality (Split: {args.split}) ===")
        summary = run_retrieval_experiment(root, split=args.split)
        print(json.dumps(summary, indent=2))
        return 0

    elif target == "verification":
        print(f"=== Evaluating Verification Baselines (Split: {args.split}) ===")
        summary = run_verification_experiment(
            root, split=args.split, bootstrap_iterations=args.bootstrap_iterations
        )
        print(
            json.dumps(
                {
                    "status": summary["status"],
                    "split": summary["split"],
                    "summary_rows": summary["summary_rows"],
                    "fsr_breakdown": summary["fsr_breakdown"],
                },
                indent=2,
            )
        )
        return 0

    elif target == "ablations":
        print(f"=== Evaluating Controlled Ablations (Split: {args.split}) ===")
        store = build_default_evidence_store(root)
        retrievers = build_all_retrievers(store)
        claims = load_benchmark_claims(root, split=args.split)
        summary = run_ablation_suite(
            claims=claims,
            store=store,
            retrievers=retrievers,
            project_root=root,
            bootstrap_iterations=args.bootstrap_iterations,
        )
        print(json.dumps({"ablation_comparison": summary["ablation_comparison"]}, indent=2))
        return 0

    elif target == "errors":
        print(f"=== Generating Comprehensive Error Analysis (Split: {args.split}) ===")
        claims = load_benchmark_claims(root, split=args.split)
        preds_path = root / "results" / "predictions" / "verification_predictions.jsonl"
        if not preds_path.exists():
            print("Running verification first to generate predictions...")
            run_verification_experiment(root, split=args.split, bootstrap_iterations=100)

        predictions_by_method: dict[str, list[dict[str, Any]]] = {}
        with preds_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    m = item.get("config_name", "fieldguard_full")
                    predictions_by_method.setdefault(m, []).append(item)

        out_doc = root / "docs" / "error_analysis.md"
        report = generate_error_analysis_report(claims, predictions_by_method, out_doc)
        print(f"Error analysis report generated at {out_doc}")
        print(
            json.dumps(
                {
                    "total_claims": len(claims),
                    "fieldguard_residual_errors_count": report["fg_residual_errors_count"],
                    "wrong_context_false_support_prevented": report["wrong_context_caught_count"],
                    "qualification_violations_caught": report["qualification_caught_count"],
                    "temporal_inapplicability_caught": report["temporal_caught_count"],
                    "correct_abstentions_count": report["correct_abstentions_count"],
                },
                indent=2,
            )
        )
        return 0

    else:
        print(f"Unknown evaluation target '{target}'. Choose from: retrieval, verification, ablations, errors", file=sys.stderr)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="fieldguard",
        description="FieldGuard: Condition-Aware Verification of Numerical Claims in Government-Scheme Question Answering Using RAG",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # sources validate
    p_sources = subparsers.add_parser("sources", help="Source provenance commands")
    p_sources_sub = p_sources.add_subparsers(dest="sources_action", required=True)
    p_sources_val = p_sources_sub.add_parser("validate", help="Validate source manifest and file checksums")

    # ingest
    p_ingest = subparsers.add_parser("ingest", help="Run acquisition and document/table extraction pipelines")

    # index build
    p_index = subparsers.add_parser("index", help="Index management")
    p_index_sub = p_index.add_subparsers(dest="index_action", required=True)
    p_index_build = p_index_sub.add_parser("build", help="Build/refresh retrieval indexes")

    # retrieve
    p_retrieve = subparsers.add_parser("retrieve", help="Retrieve evidence for a query")
    p_retrieve.add_argument("--query", "-q", type=str, required=True, help="Query text")
    p_retrieve.add_argument("--method", "-m", type=str, default="hybrid", choices=["hybrid", "semantic", "lexical", "table"])
    p_retrieve.add_argument("--top-k", "-k", type=int, default=5, help="Number of retrieved results")
    p_retrieve.add_argument("--json", action="store_true", help="Output raw JSON")

    # verify
    p_verify = subparsers.add_parser("verify", help="Verify a numerical claim end-to-end")
    p_verify.add_argument("--claim", "-c", type=str, required=True, help="Numerical claim to verify")
    p_verify.add_argument("--question", type=str, default=None, help="Optional natural-language question")
    p_verify.add_argument("--claim-id", type=str, default=None, help="Optional claim ID")
    p_verify.add_argument("--method", "-m", type=str, default="hybrid", choices=["hybrid", "semantic", "lexical", "table"])
    p_verify.add_argument("--top-k", "-k", type=int, default=5, help="Number of evidence chunks to retrieve")
    p_verify.add_argument("--json", action="store_true", help="Output raw JSON")

    # evaluate
    p_eval = subparsers.add_parser("evaluate", help="Run reproducible research experiments")
    p_eval.add_argument(
        "eval_target",
        choices=["retrieval", "verification", "ablations", "errors"],
        help="Evaluation experiment to run",
    )
    p_eval.add_argument("--split", type=str, default="test", choices=["dev", "test", "all"])
    p_eval.add_argument("--bootstrap-iterations", type=int, default=500, help="Number of cluster bootstrap iterations")

    args = parser.parse_args()

    if args.command == "sources" and args.sources_action == "validate":
        sys.exit(cmd_sources_validate(args))
    elif args.command == "ingest":
        sys.exit(cmd_ingest(args))
    elif args.command == "index" and args.index_action == "build":
        sys.exit(cmd_index_build(args))
    elif args.command == "retrieve":
        sys.exit(cmd_retrieve(args))
    elif args.command == "verify":
        sys.exit(cmd_verify(args))
    elif args.command == "evaluate":
        sys.exit(cmd_evaluate(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
