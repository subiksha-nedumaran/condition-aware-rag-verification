"""Audit numeric fact coverage across all 7 curated government schemes.

For each scheme, inspects every trusted ExtractedEvidenceUnit (paragraph chunks and table rows),
extracts all numerical facts (both inline mentions and table-header-typed cell values), and checks
whether a StructuredRuleRecord covers each fact.

Saves the detailed audit table to results/tables/rule_coverage.csv and prints a per-scheme summary.
"""

from __future__ import annotations

import csv
import math
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fieldguard.evidence_schema import StructuredRuleRecord
from fieldguard.evidence_store import (
    EvidenceStore,
    build_default_evidence_store,
    build_pm_kisan_evidence_store,
)
from fieldguard.flagship_schemes_data import build_flagship_scheme_evidence_store
from fieldguard.metadata import ExtractedEvidenceUnit
from fieldguard.numeric_normalizer import (
    NormalizedNumericMention,
    compare_numeric_values,
    extract_all_numeric_mentions,
    normalize_unit_and_value,
)

SCHEMES: tuple[str, ...] = (
    "PMFBY",
    "PM_KISAN",
    "MGNREGA",
    "PM_JAY",
    "PMAY_G",
    "PM_KUSUM",
    "PMMY",
)


def load_scheme_store(scheme: str, project_root: Path = PROJECT_ROOT) -> EvidenceStore:
    s = scheme.upper()
    if s == "PMFBY":
        return build_default_evidence_store(project_root, scheme="pmfby")
    if s == "PM_KISAN":
        return build_pm_kisan_evidence_store(project_root)
    return build_flagship_scheme_evidence_store(s, project_root=project_root)


def extract_table_cell_mentions(unit: ExtractedEvidenceUnit) -> list[NormalizedNumericMention]:
    """Extract numeric facts from table cells where the unit is encoded in headers or a Unit column."""
    if unit.evidence_type != "table_row" or not unit.headers or not unit.cells:
        return []

    mentions: list[NormalizedNumericMention] = []
    header_map: dict[str, str] = {}
    for h, c in zip(unit.headers, unit.cells):
        header_map[h.strip()] = c.strip()

    explicit_unit_col = header_map.get("Unit") or header_map.get("Unit / Basis") or ""

    for h, c in zip(unit.headers, unit.cells):
        h_low = h.strip().lower()
        c_str = c.strip()
        if h_low in ("s.no.", "s.no", "sno", "sl.no", "row_id", "instalment_number"):
            continue

        # Check if cell is a pure number (possibly with commas)
        m_num = re.fullmatch(r"(\d(?:[\d,]*\d)?(?:\.\d+)?)", c_str)
        if not m_num:
            continue
        val = float(m_num.group(1).replace(",", ""))

        inferred_unit: str | None = None
        if any(k in h_low for k in ("_inr", "rupee", "amount", "benefit", "grant", "loan", "assistance", "cost", "salary", "wage", "pension")):
            inferred_unit = "rupees"
        elif any(k in h_low for k in ("_sqm", "sq_m", "area_sqm", "square_metre")):
            inferred_unit = "square_metres"
        elif any(k in h_low for k in ("_ha", "hectare")):
            inferred_unit = "hectares"
        elif any(k in h_low for k in ("_pct", "percent", "share", "rate", "ratio")):
            inferred_unit = "percent"
        elif any(k in h_low for k in ("_days", "days")):
            inferred_unit = "days"
        elif any(k in h_low for k in ("_hp", "horsepower")):
            inferred_unit = "horsepower"
        elif any(k in h_low for k in ("_mw", "megawatt")):
            inferred_unit = "megawatts"
        elif any(k in h_low for k in ("_kw", "kilowatt")):
            inferred_unit = "kilowatts"
        elif any(k in h_low for k in ("_km", "kilometre", "distance")):
            inferred_unit = "kilometres"
        elif any(k in h_low for k in ("_months", "months", "tenure")):
            inferred_unit = "months"
        elif any(k in h_low for k in ("_years", "years", "age")):
            inferred_unit = "years"
        elif explicit_unit_col:
            inferred_unit = explicit_unit_col.split()[0].strip()

        if inferred_unit:
            norm_v, norm_u, can_v, can_u = normalize_unit_and_value(val, inferred_unit)
            mentions.append(
                NormalizedNumericMention(
                    raw_text=f"{h}: {c_str}" + (f" ({explicit_unit_col})" if explicit_unit_col else ""),
                    value=norm_v,
                    unit=norm_u,
                    canonical_value=can_v,
                    canonical_unit=can_u,
                )
            )
    return mentions


def extract_unit_numeric_facts(unit: ExtractedEvidenceUnit) -> list[NormalizedNumericMention]:
    """Extract deduplicated substantive numeric facts from an evidence unit."""
    if unit.verification_status != "trusted_official":
        return []
    sec = (unit.section or "").upper()
    if sec in ("COVER", "TOC") or "METADATA NOTE" in sec:
        return []

    raw_mentions = list(extract_all_numeric_mentions(unit.text))
    raw_mentions.extend(extract_table_cell_mentions(unit))

    deduped: list[NormalizedNumericMention] = []
    for m in raw_mentions:
        # Check if already present in deduped for this unit
        already = False
        for existing in deduped:
            ok, _ = compare_numeric_values(
                m.canonical_value,
                m.canonical_unit,
                existing.canonical_value,
                existing.canonical_unit,
            )
            if ok:
                already = True
                break
        if not already:
            deduped.append(m)
    return deduped


def find_covering_rule(
    mention: NormalizedNumericMention,
    rules: list[StructuredRuleRecord],
) -> StructuredRuleRecord | None:
    """Return the first StructuredRuleRecord that covers this numeric mention."""
    for rule in rules:
        ok, _ = compare_numeric_values(
            claimed_value=mention.canonical_value,
            claimed_unit=mention.canonical_unit,
            rule_value=rule.maximum_rate,
            rule_unit=rule.unit,
            allowed_values=rule.allowed_values,
        )
        if ok:
            return rule
        if rule.minimum_value is not None:
            ok_min, _ = compare_numeric_values(
                claimed_value=mention.canonical_value,
                claimed_unit=mention.canonical_unit,
                rule_value=rule.minimum_value,
                rule_unit=rule.unit,
            )
            if ok_min:
                return rule
    return None


def audit_all_schemes(
    project_root: Path = PROJECT_ROOT,
    output_csv: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if output_csv is None:
        output_csv = project_root / "results" / "tables" / "rule_coverage.csv"

    rows: list[dict[str, Any]] = []
    summary: dict[str, dict[str, Any]] = {}

    for scheme in SCHEMES:
        store = load_scheme_store(scheme, project_root=project_root)
        all_scheme_rules = list(store.trusted_rules.values())
        total_facts = 0
        covered_exact = 0
        covered_scheme = 0

        for unit in store.evidence_units.values():
            if unit.verification_status != "trusted_official":
                continue
            facts = extract_unit_numeric_facts(unit)
            unit_rules = store.get_rules_for_evidence(unit.evidence_id)

            for fact in facts:
                total_facts += 1
                exact_rule = find_covering_rule(fact, unit_rules)
                scheme_rule = exact_rule or find_covering_rule(fact, all_scheme_rules)

                is_covered_exact = exact_rule is not None
                is_covered_scheme = scheme_rule is not None
                if is_covered_exact:
                    covered_exact += 1
                if is_covered_scheme:
                    covered_scheme += 1

                matched_rule = exact_rule or scheme_rule
                rows.append(
                    {
                        "scheme": scheme,
                        "evidence_id": unit.evidence_id,
                        "document_id": unit.document_id,
                        "evidence_type": unit.evidence_type,
                        "physical_pdf_page": unit.physical_pdf_page,
                        "section": unit.section or "",
                        "raw_mention": fact.raw_text,
                        "canonical_value": fact.canonical_value,
                        "canonical_unit": fact.canonical_unit,
                        "covered": is_covered_exact,
                        "covered_in_scheme": is_covered_scheme,
                        "rule_id": matched_rule.rule_id if matched_rule else "",
                        "rule_parameter": matched_rule.rule_parameter if matched_rule else "",
                    }
                )

        summary[scheme] = {
            "evidence_units": sum(
                1 for u in store.evidence_units.values() if u.verification_status == "trusted_official"
            ),
            "total_rules": len(all_scheme_rules),
            "distinct_parameters": len({r.rule_parameter for r in all_scheme_rules}),
            "numeric_facts": total_facts,
            "covered_exact": covered_exact,
            "covered_in_scheme": covered_scheme,
            "exact_coverage_pct": round(100.0 * covered_exact / total_facts, 2) if total_facts else 100.0,
            "scheme_coverage_pct": round(100.0 * covered_scheme / total_facts, 2) if total_facts else 100.0,
        }

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "scheme",
        "evidence_id",
        "document_id",
        "evidence_type",
        "physical_pdf_page",
        "section",
        "raw_mention",
        "canonical_value",
        "canonical_unit",
        "covered",
        "covered_in_scheme",
        "rule_id",
        "rule_parameter",
    ]
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return rows, summary


def main() -> None:
    rows, summary = audit_all_schemes()
    print("=== Rule Coverage Audit Summary ===")
    print(
        f"{'Scheme':<10} | {'Units':>5} | {'Rules':>5} | {'Params':>6} | "
        f"{'Facts':>5} | {'Cov(Unit)':>9} | {'Cov(Scheme)':>11}"
    )
    print("-" * 72)
    for scheme, stats in summary.items():
        print(
            f"{scheme:<10} | {stats['evidence_units']:>5} | {stats['total_rules']:>5} | "
            f"{stats['distinct_parameters']:>6} | {stats['numeric_facts']:>5} | "
            f"{stats['covered_exact']:>3}/{stats['numeric_facts']:<3} ({stats['exact_coverage_pct']:>5.1f}%) | "
            f"{stats['covered_in_scheme']:>3}/{stats['numeric_facts']:<3} ({stats['scheme_coverage_pct']:>5.1f}%)"
        )
    print(f"\nSaved {len(rows)} rows to results/tables/rule_coverage.csv")


if __name__ == "__main__":
    main()
