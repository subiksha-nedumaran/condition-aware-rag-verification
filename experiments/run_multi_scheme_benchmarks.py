"""Build held-out benchmarks for the 5 flagship schemes and run multi-scheme evaluations."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fieldguard.benchmarks import save_all_flagship_scheme_benchmarks
from fieldguard.evaluation.runner import run_multi_scheme_experiment

SCHEMES = ["MGNREGA", "PM_JAY", "PMAY_G", "PM_KUSUM", "PMMY", "PM_KISAN"]


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    saved = save_all_flagship_scheme_benchmarks(project_root=project_root)
    for scheme, path in saved.items():
        print(f"Saved {scheme} benchmark -> {path}")

    summary_rows: list[dict[str, object]] = []
    for scheme in SCHEMES:
        splits = ["dev", "test"] if scheme != "PM_KISAN" else ["test"]
        for split in splits:
            res = run_multi_scheme_experiment(
                scheme=scheme.lower(),
                split=split,
                project_root=project_root,
                bootstrap_iterations=300,
            )
            for row in res.get("verification", []):
                summary_rows.append(
                    {
                        "scheme": scheme,
                        "split": split,
                        "method_name": row["method_name"],
                        "sample_size": row["sample_size"],
                        "accuracy": row["accuracy"],
                        "false_support_rate": row["false_support_rate"],
                        "macro_f1": row["macro_f1"],
                        "decision_coverage": row["decision_coverage"],
                    }
                )

    out_dir = project_root / "results" / "multi_scheme"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "summary.csv"
    if summary_rows:
        with out_csv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(summary_rows)
        print(f"\nSaved combined summary -> {out_csv}")
        print("\n=== MULTI-SCHEME EVALUATION SUMMARY ===")
        for r in summary_rows:
            print(
                f"{r['scheme']:9s} | {r['split']:4s} | {r['method_name']:15s} | "
                f"acc={r['accuracy']:.4f} | fsr={r['false_support_rate']:.4f} | "
                f"f1={r['macro_f1']:.4f} | cov={r['decision_coverage']:.4f}"
            )


if __name__ == "__main__":
    main()
