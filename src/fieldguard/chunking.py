"""Paragraph and section-aware chunking with provenance preservation."""

from __future__ import annotations

from typing import Any

from fieldguard.metadata import ExtractedEvidenceUnit, build_provenance_kwargs
from fieldguard.source_manifest import SourceDocumentRecord
from fieldguard.table_extraction import check_corrupted_percentage_in_text


def chunk_page_blocks_into_units(
    doc: SourceDocumentRecord,
    physical_pdf_page: int | None,
    printed_page: str | None,
    blocks: list[dict[str, Any]],
    extraction_method: str,
) -> tuple[list[ExtractedEvidenceUnit], list[dict[str, Any]]]:
    """
    Convert extracted page headings and paragraphs into section-aware evidence chunks
    while preserving physical and printed page provenance.
    """
    units: list[ExtractedEvidenceUnit] = []
    warnings: list[dict[str, Any]] = []
    prov = build_provenance_kwargs(doc)

    current_heading = ""
    current_section: str | None = None
    para_counter = 0

    for blk in blocks:
        btype = blk.get("type", "paragraph")
        sec = blk.get("section") or current_section
        txt = (blk.get("text") or "").strip()
        if not txt:
            continue

        if btype == "heading":
            current_heading = txt
            current_section = sec
            continue

        if btype == "paragraph":
            para_counter += 1
            full_text = f"[{current_heading}] {txt}" if current_heading else txt
            is_corrupt, corrupt_reason = check_corrupted_percentage_in_text(full_text)
            quality = "suspicious_corrupted_number" if is_corrupt else "high_verified"
            if is_corrupt:
                warnings.append(
                    {
                        "document_id": doc.document_id,
                        "physical_pdf_page": physical_pdf_page,
                        "section": sec,
                        "warning": corrupt_reason,
                    }
                )

            page_tag = f"P{physical_pdf_page}" if physical_pdf_page is not None else "HTML"
            evidence_id = f"EV_{doc.document_id}_{page_tag}_CHUNK_{para_counter}"

            unit = ExtractedEvidenceUnit(
                evidence_id=evidence_id,
                physical_pdf_page=physical_pdf_page,
                printed_page=printed_page,
                section=sec,
                table_id=None,
                row_id=None,
                headers=None,
                text=full_text,
                extraction_method=extraction_method,
                extraction_quality=quality,
                evidence_type="paragraph",
                cells=None,
                **prov,
            )
            units.append(unit)

    return units, warnings
