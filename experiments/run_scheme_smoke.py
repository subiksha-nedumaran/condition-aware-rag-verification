"""Evaluate all curated UI scenarios; this is a smoke check, not a generalization benchmark."""

import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from fieldguard.demo_scenarios import SCHEME_SCENARIOS
from fieldguard.evidence_store import build_default_evidence_store, build_pm_kisan_evidence_store
from fieldguard.flagship_schemes_data import build_flagship_scheme_evidence_store
from fieldguard.evaluation.runner import build_all_retrievers
from fieldguard.verifier import FieldGuardVerifier


def main():
    root = Path(__file__).resolve().parents[1]
    rows = []
    for scheme, scenarios in SCHEME_SCENARIOS.items():
        store = (build_default_evidence_store(root) if scheme == "PMFBY" else
                 build_pm_kisan_evidence_store(root) if scheme == "PM_KISAN" else
                 build_flagship_scheme_evidence_store(scheme, root))
        retriever = build_all_retrievers(store)["hybrid"]
        verifier = FieldGuardVerifier(store)
        for title, (question, claim) in scenarios.items():
            label = title.split(". ", 1)[1].split(":", 1)[0]
            expected = next(verdict for prefix, verdict in (
                ("Supported", "SUPPORTED"), ("Wrong Context", "WRONG_CONTEXT"),
                ("Contradicted", "CONTRADICTED"), ("Unverifiable", "UNVERIFIABLE"),
            ) if label.startswith(prefix))
            items = [r.to_dict() for r in retriever.retrieve(f"{question} {claim}", top_k=5)]
            pred = verifier.verify_claim(title, question, claim, items)
            rows.append(dict(scheme=scheme, scenario=title, expected=expected,
                             actual=pred.predicted_verdict, matched=expected == pred.predicted_verdict,
                             rationale=pred.verification_rationale))
    output = root / "results" / "tables" / "scheme_smoke.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Curated scenarios matched: {sum(r['matched'] for r in rows)}/{len(rows)} across {len(SCHEME_SCENARIOS)} schemes. Report: {output}")


if __name__ == "__main__":
    main()
