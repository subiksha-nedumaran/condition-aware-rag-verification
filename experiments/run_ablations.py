"""CLI entry point for Experiment G: Controlled Ablation Study (Phase 9)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fieldguard.benchmark_builder import load_benchmark_claims
from fieldguard.evaluation.ablation import run_ablation_suite
from fieldguard.evaluation.runner import build_all_retrievers
from fieldguard.evidence_store import build_default_evidence_store


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FieldGuard ablation study (Experiment G).")
    parser.add_argument("--split", type=str, default="test", choices=["dev", "test"])
    parser.add_argument("--bootstrap-iterations", type=int, default=500)
    args = parser.parse_args()

    store = build_default_evidence_store(PROJECT_ROOT)
    retrievers = build_all_retrievers(store)
    claims = load_benchmark_claims(PROJECT_ROOT, split=args.split)

    summary = run_ablation_suite(
        claims=claims,
        store=store,
        retrievers=retrievers,
        project_root=PROJECT_ROOT,
        bootstrap_iterations=args.bootstrap_iterations,
    )
    print(json.dumps({"ablation_comparison": summary["ablation_comparison"]}, indent=2))


if __name__ == "__main__":
    main()
