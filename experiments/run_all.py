"""Master CLI runner for all FieldGuard experiments (Experiments A through I)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fieldguard.benchmark_builder import build_and_save_benchmark
from fieldguard.data_acquisition import run_acquisition_pipeline
from fieldguard.document_extraction import run_extraction_pipeline
from fieldguard.evaluation.runner import run_complete_evaluation_pipeline


def main() -> None:
    if not (PROJECT_ROOT / "data" / "manifests" / "source_manifest.json").exists():
        run_acquisition_pipeline(PROJECT_ROOT)
    if not (PROJECT_ROOT / "data" / "processed" / "chunks.jsonl").exists():
        run_extraction_pipeline(PROJECT_ROOT)
    if not (PROJECT_ROOT / "data" / "benchmark" / "claims.jsonl").exists():
        build_and_save_benchmark(PROJECT_ROOT)

    master_log = run_complete_evaluation_pipeline(PROJECT_ROOT)
    print(
        json.dumps(
            {
                "executed_at_utc": master_log["executed_at_utc"],
                "experiment_statuses": master_log["experiment_statuses"],
                "retrieval_summary_test": master_log["retrieval_summary_test"],
                "verification_summary_test": master_log["verification_summary_test"],
                "ablation_summary_test": master_log["ablation_summary_test"],
                "parser_comparison_test": master_log["parser_comparison_test"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
