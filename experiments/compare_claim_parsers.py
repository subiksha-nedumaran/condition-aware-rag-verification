"""CLI entry point for Experiment H: Claim Parser Comparison (Phase 10)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fieldguard.evaluation.runner import run_claim_parser_comparison


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FieldGuard claim parser comparison (Experiment H).")
    parser.add_argument("--split", type=str, default="test", choices=["dev", "test"])
    args = parser.parse_args()

    summary = run_claim_parser_comparison(PROJECT_ROOT, split=args.split)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
