"""CLI entry point for Experiments B, C, D, E, F: Verification & Error Analysis (Phase 7 & 12)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fieldguard.evaluation.runner import run_verification_experiment


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FieldGuard verification evaluation (Experiments B-F).")
    parser.add_argument("--split", type=str, default="test", choices=["dev", "test"])
    parser.add_argument("--bootstrap-iterations", type=int, default=1000)
    args = parser.parse_args()

    summary = run_verification_experiment(
        PROJECT_ROOT,
        split=args.split,
        bootstrap_iterations=args.bootstrap_iterations,
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


if __name__ == "__main__":
    main()
