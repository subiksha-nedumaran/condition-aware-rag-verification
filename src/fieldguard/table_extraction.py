"""Structured table extraction and header-coupled row serialization."""

from __future__ import annotations

import re
from typing import Any

from fieldguard.metadata import ExtractedEvidenceUnit, build_provenance_kwargs
from fieldguard.source_manifest import SourceDocumentRecord


def format_table_row_with_headers(
    headers: list[str],
    cells: list[str],
    caption: str | None = None,
) -> str:
    """
    Serialize a table row paired explicitly with its column headers so that a numerical
    percentage or rate is never detached from its season, crop category, or qualification.
    """
    if not headers:
        raise ValueError("Cannot format a table row without column headers (header detachment forbidden).")
    if len(headers) != len(cells):
        raise ValueError(
            f"Column count mismatch between headers ({len(headers)}) and row cells ({len(cells)})."
        )

    pairs = [f"{h.strip()}: {c.strip()}" for h, c in zip(headers, cells)]
    prefix = f"[Table: {caption.strip()}] " if caption else ""
    return prefix + " | ".join(pairs)


def check_corrupted_percentage_in_text(text: str) -> tuple[bool, str | None]:
    """
    Detect common OCR / PDF extraction corruption patterns in numerical strings,
    such as broken percentage tokens ('2 . 0 %', '1,5%', '?%', 'NaN%').
    """
    if re.search(r"\b\d+\s+\.\s+\d+\s*%", text):
        return True, "Broken decimal spacing in percentage token"
    if re.search(r"(?:\?|NaN|null)\s*%", text, flags=re.IGNORECASE):
        return True, "Missing or corrupted numeric digits before '%'"
    if re.search(r"\b\d+\s+% of", text):
        return True, "Suspicious whitespace inside percentage token"
    return False, None


def extract_table_units_from_page_tables(
    doc: SourceDocumentRecord,
    physical_pdf_page: int,
    printed_page: str | None,
    raw_tables: list[dict[str, Any]],
    extraction_method: str,
) -> tuple[list[ExtractedEvidenceUnit], list[dict[str, Any]]]:
    """
    Convert raw page tables into header-coupled ExtractedEvidenceUnit records.
    Returns (extracted_row_units, extraction_warnings).
    """
    units: list[ExtractedEvidenceUnit] = []
    warnings: list[dict[str, Any]] = []
    prov = build_provenance_kwargs(doc)

    for tbl in raw_tables:
        table_id = tbl.get("table_id") or f"{doc.document_id}_P{physical_pdf_page}_TBL"
        section = tbl.get("section")
        caption = tbl.get("caption", "")
        headers = tbl.get("headers") or []
        rows = tbl.get("rows") or []

        if not headers:
            warnings.append(
                {
                    "document_id": doc.document_id,
                    "physical_pdf_page": physical_pdf_page,
                    "table_id": table_id,
                    "warning": "Table missing headers; skipped to prevent header-detached rows.",
                }
            )
            continue

        for r_idx, row_item in enumerate(rows, start=1):
            if isinstance(row_item, dict):
                row_id = row_item.get("row_id") or f"{table_id}_R{r_idx}"
                cells = row_item.get("cells") or []
            else:
                row_id = f"{table_id}_R{r_idx}"
                cells = list(row_item)

            if len(cells) != len(headers):
                warnings.append(
                    {
                        "document_id": doc.document_id,
                        "physical_pdf_page": physical_pdf_page,
                        "table_id": table_id,
                        "row_id": row_id,
                        "warning": f"Header/cell length mismatch ({len(headers)} vs {len(cells)})",
                    }
                )
                continue

            row_text = format_table_row_with_headers(headers=headers, cells=cells, caption=caption)
            is_corrupt, corrupt_reason = check_corrupted_percentage_in_text(row_text)
            quality = "suspicious_corrupted_number" if is_corrupt else "high_verified"
            if is_corrupt:
                warnings.append(
                    {
                        "document_id": doc.document_id,
                        "physical_pdf_page": physical_pdf_page,
                        "table_id": table_id,
                        "row_id": row_id,
                        "warning": corrupt_reason,
                    }
                )

            evidence_id = f"EV_{doc.document_id}_P{physical_pdf_page}_{row_id}"
            unit = ExtractedEvidenceUnit(
                evidence_id=evidence_id,
                physical_pdf_page=physical_pdf_page,
                printed_page=printed_page,
                section=section,
                table_id=table_id,
                row_id=row_id,
                headers=list(headers),
                text=row_text,
                extraction_method=extraction_method,
                extraction_quality=quality,
                evidence_type="table_row",
                cells=list(cells),
                **prov,
            )
            units.append(unit)

    return units, warnings
