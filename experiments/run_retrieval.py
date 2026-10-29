"""CLI entry point for Experiment A: Retrieval Quality Evaluation (Phase 8)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fieldguard.evaluation.runner import run_retrieval_experiment


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FieldGuard retrieval evaluation (Experiment A).")
    parser.add_argument("--split", type=str, default="test", choices=["dev", "test", "all"])
    args = parser.parse_args()

    split_arg = None if args.split == "all" else args.split
    summary = run_retrieval_experiment(PROJECT_ROOT, split=split_arg or "test")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
