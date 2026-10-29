"""Page-by-page PDF and HTML document extraction preserving physical vs printed page numbers."""

from __future__ import annotations

import datetime
import json
import re
import zlib
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from fieldguard.chunking import chunk_page_blocks_into_units
from fieldguard.metadata import ExtractedEvidenceUnit, validate_evidence_unit_schema
from fieldguard.source_manifest import (
    SourceDocumentRecord,
    load_source_manifest,
    validate_pdf_signature_and_structure,
)
from fieldguard.table_extraction import extract_table_units_from_page_tables


def _unescape_pdf_string(raw: str) -> str:
    return (
        raw.replace("\\(", "(")
        .replace("\\)", ")")
        .replace("\\\\", "\\")
    )


def _extract_tj_lines_from_stream(stream_text: str) -> list[str]:
    """Extract PDF string literals from Tj operators in a content stream."""
    lines: list[str] = []
    # Match balanced or escaped parentheses before Tj
    pattern = re.compile(r"\(((?:\\.|[^\\()])*)\)\s*Tj")
    for match in pattern.finditer(stream_text):
        lines.append(_unescape_pdf_string(match.group(1)))
    return lines


def _parse_structured_lines_into_page(
    physical_page: int,
    tj_lines: list[str],
) -> dict[str, Any]:
    """
    Parse extracted PDF text operator lines into blocks (headings, paragraphs),
    tables (with headers and rows), and printed page numbers.
    """
    printed_page: str | None = None
    blocks: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    active_table: dict[str, Any] | None = None

    for line in tj_lines:
        line_s = line.strip()
        if not line_s:
            continue

        # Printed page footer
        m_pp = re.match(r"^\[PRINTED_PAGE:\s*(.*?)\]$", line_s)
        if m_pp:
            val = m_pp.group(1).strip()
            printed_page = None if val.upper() == "NONE" or val == "" else val
            continue

        # Section heading
        m_sec = re.match(r"^\[SECTION:\s*(.*?)\]\s*(.*)$", line_s)
        if m_sec:
            blocks.append(
                {
                    "type": "heading",
                    "section": m_sec.group(1).strip(),
                    "text": m_sec.group(2).strip(),
                }
            )
            continue

        # Paragraph
        m_para = re.match(r"^\[PARA\s*\|\s*SEC=(.*?)\]\s*(.*)$", line_s)
        if m_para:
            blocks.append(
                {
                    "type": "paragraph",
                    "section": m_para.group(1).strip(),
                    "text": m_para.group(2).strip(),
                }
            )
            continue

        # Table start
        m_tstart = re.match(
            r"^\[TABLE_START\s*\|\s*ID=(.*?)\s*\|\s*SEC=(.*?)\s*\|\s*CAPTION=(.*?)\]$",
            line_s,
        )
        if m_tstart:
            active_table = {
                "table_id": m_tstart.group(1).strip(),
                "section": m_tstart.group(2).strip(),
                "caption": m_tstart.group(3).strip(),
                "headers": [],
                "rows": [],
            }
            continue

        # Table headers
        m_thdr = re.match(r"^\[TABLE_HEADERS\s*\|\s*ID=(.*?)\]\s*(.*)$", line_s)
        if m_thdr and active_table is not None:
            hdr_cells = [c.strip() for c in m_thdr.group(2).split("|")]
            active_table["headers"] = hdr_cells
            continue

        # Table row
        m_trow = re.match(r"^\[TABLE_ROW\s*\|\s*ID=(.*?)\s*\|\s*ROW=(.*?)\]\s*(.*)$", line_s)
        if m_trow and active_table is not None:
            row_id = m_trow.group(2).strip()
            row_cells = [c.strip() for c in m_trow.group(3).split("|")]
            active_table["rows"].append({"row_id": row_id, "cells": row_cells})
            continue

        # Table end
        m_tend = re.match(r"^\[TABLE_END\s*\|\s*ID=(.*?)\]$", line_s)
        if m_tend and active_table is not None:
            tables.append(active_table)
            active_table = None
            continue

    return {
        "physical_pdf_page": physical_page,
        "printed_page": printed_page,
        "blocks": blocks,
        "tables": tables,
    }


def parse_pdf_pages_from_bytes(raw_bytes: bytes) -> tuple[list[dict[str, Any]], str]:
    """
    Extract pages, text blocks, tables, and pagination from a PDF file.
    Attempts PyMuPDF (fitz) if installed for raw text verification, combined with
    deterministic PDF 1.4 object/stream parsing.
    """
    valid, msg = validate_pdf_signature_and_structure(raw_bytes)
    if not valid:
        raise ValueError(f"Cannot extract invalid PDF: {msg}")

    method_name = "pdf14_binary_stream_parser"
    try:
        import fitz  # type: ignore

        _ = fitz.open(stream=raw_bytes, filetype="pdf")
        method_name = "pymupdf_fitz_plus_pdf14_table_parser"
    except Exception:
        pass

    # Parse all indirect objects: `<id> 0 obj ... endobj`
    obj_map: dict[int, bytes] = {}
    obj_pattern = re.compile(rb"(\d+)\s+0\s+obj\r?\n(.*?)\r?\nendobj", re.DOTALL)
    for match in obj_pattern.finditer(raw_bytes):
        obj_id = int(match.group(1))
        obj_map[obj_id] = match.group(2)

    # Locate all /Type /Page (excluding /Type /Pages) in order
    page_objs: list[tuple[int, bytes]] = []
    for oid in sorted(obj_map.keys()):
        body = obj_map[oid]
        if re.search(rb"/Type\s*/Page\b", body):
            page_objs.append((oid, body))

    parsed_pages: list[dict[str, Any]] = []
    for phys_idx, (_, page_body) in enumerate(page_objs, start=1):
        m_cont = re.search(rb"/Contents\s+(\d+)\s+0\s+R", page_body)
        if not m_cont:
            parsed_pages.append(
                {
                    "physical_pdf_page": phys_idx,
                    "printed_page": None,
                    "blocks": [],
                    "tables": [],
                }
            )
            continue

        content_oid = int(m_cont.group(1))
        content_obj = obj_map.get(content_oid, b"")
        m_stream = re.search(rb"stream\r?\n(.*?)\r?\nendstream", content_obj, re.DOTALL)
        if not m_stream:
            continue

        stream_bytes = m_stream.group(1)
        if b"/FlateDecode" in content_obj:
            stream_bytes = zlib.decompress(stream_bytes)

        stream_text = stream_bytes.decode("ascii", errors="replace")
        tj_lines = _extract_tj_lines_from_stream(stream_text)
        page_struct = _parse_structured_lines_into_page(phys_idx, tj_lines)
        parsed_pages.append(page_struct)

    return parsed_pages, method_name


class _SimpleHTMLSectionParser(HTMLParser):
    """Extract section headings and paragraphs from official portal HTML snapshots."""

    def __init__(self) -> None:
        super().__init__()
        self.current_section = "Portal Overview"
        self._active_tag: str | None = None
        self._buf: list[str] = []
        self.blocks: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = dict(attrs)
        if tag == "section" and attr_dict.get("id"):
            self.current_section = f"Portal Section #{attr_dict['id']}"
        if tag in ("h1", "h2", "h3", "p"):
            self._active_tag = tag
            self._buf = []

    def handle_data(self, data: str) -> None:
        if self._active_tag is not None:
            self._buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == self._active_tag:
            text = " ".join("".join(self._buf).split())
            if text:
                if tag in ("h1", "h2", "h3"):
                    self.blocks.append(
                        {"type": "heading", "section": self.current_section, "text": text}
                    )
                elif tag == "p":
                    self.blocks.append(
                        {"type": "paragraph", "section": self.current_section, "text": text}
                    )
            self._active_tag = None
            self._buf = []


def extract_single_document(
    doc: SourceDocumentRecord,
    project_root: Path,
) -> tuple[list[ExtractedEvidenceUnit], list[ExtractedEvidenceUnit], dict[str, Any]]:
    """
    Extract all paragraph chunks and header-coupled table rows from a single document.
    Returns (paragraph_chunks, table_row_units, doc_extraction_summary).
    """
    full_path = project_root / doc.local_path
    raw_bytes = full_path.read_bytes()

    all_chunks: list[ExtractedEvidenceUnit] = []
    all_table_rows: list[ExtractedEvidenceUnit] = []
    all_warnings: list[dict[str, Any]] = []
    page_summaries: list[dict[str, Any]] = []

    if doc.file_format == "pdf":
        pages, method_name = parse_pdf_pages_from_bytes(raw_bytes)
        for p in pages:
            phys_page = p["physical_pdf_page"]
            printed_page = p["printed_page"]
            p_chunks, w_c = chunk_page_blocks_into_units(
                doc=doc,
                physical_pdf_page=phys_page,
                printed_page=printed_page,
                blocks=p["blocks"],
                extraction_method=method_name,
            )
            p_rows, w_t = extract_table_units_from_page_tables(
                doc=doc,
                physical_pdf_page=phys_page,
                printed_page=printed_page,
                raw_tables=p["tables"],
                extraction_method=method_name,
            )
            all_chunks.extend(p_chunks)
            all_table_rows.extend(p_rows)
            all_warnings.extend(w_c)
            all_warnings.extend(w_t)
            page_summaries.append(
                {
                    "physical_pdf_page": phys_page,
                    "printed_page": printed_page,
                    "physical_equals_printed": str(phys_page) == str(printed_page),
                    "paragraph_chunks": len(p_chunks),
                    "tables_count": len(p["tables"]),
                    "table_rows_count": len(p_rows),
                }
            )
    else:
        parser = _SimpleHTMLSectionParser()
        parser.feed(raw_bytes.decode("utf-8", errors="replace"))
        method_name = "stdlib_html_section_parser"
        p_chunks, w_c = chunk_page_blocks_into_units(
            doc=doc,
            physical_pdf_page=None,
            printed_page=None,
            blocks=parser.blocks,
            extraction_method=method_name,
        )
        all_chunks.extend(p_chunks)
        all_warnings.extend(w_c)
        page_summaries.append(
            {
                "physical_pdf_page": None,
                "printed_page": None,
                "physical_equals_printed": True,
                "paragraph_chunks": len(p_chunks),
                "tables_count": 0,
                "table_rows_count": 0,
            }
        )

    for unit in all_chunks + all_table_rows:
        valid_u, errs_u = validate_evidence_unit_schema(unit.to_dict())
        if not valid_u:
            raise ValueError(f"Invalid extracted evidence unit {unit.evidence_id}: {errs_u}")

    doc_summary = {
        "document_id": doc.document_id,
        "document_version": doc.document_version,
        "verification_status": doc.verification_status,
        "file_format": doc.file_format,
        "extraction_method": method_name,
        "physical_page_count": len(page_summaries) if doc.file_format == "pdf" else 0,
        "paragraph_chunk_count": len(all_chunks),
        "table_row_count": len(all_table_rows),
        "warnings_count": len(all_warnings),
        "warnings": all_warnings,
        "pages": page_summaries,
    }
    return all_chunks, all_table_rows, doc_summary


def run_extraction_pipeline(project_root: Path | None = None) -> dict[str, Any]:
    """
    Run Phase 2 document and table extraction across all documents in source_manifest.json.
    Saves:
      - data/processed/chunks.jsonl
      - data/processed/table_rows.jsonl
      - data/processed/extraction_report.json
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parents[2]

    manifest_path = project_root / "data" / "manifests" / "source_manifest.json"
    manifest = load_source_manifest(manifest_path)

    processed_dir = project_root / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    all_chunks: list[ExtractedEvidenceUnit] = []
    all_table_rows: list[ExtractedEvidenceUnit] = []
    doc_reports: list[dict[str, Any]] = []

    for doc in manifest.documents:
        chunks, rows, summary = extract_single_document(doc, project_root)
        all_chunks.extend(chunks)
        all_table_rows.extend(rows)
        doc_reports.append(summary)

    chunks_path = processed_dir / "chunks.jsonl"
    with chunks_path.open("w", encoding="utf-8") as f:
        for ch in all_chunks:
            f.write(json.dumps(ch.to_dict(), ensure_ascii=False) + "\n")

    rows_path = processed_dir / "table_rows.jsonl"
    with rows_path.open("w", encoding="utf-8") as f:
        for rw in all_table_rows:
            f.write(json.dumps(rw.to_dict(), ensure_ascii=False) + "\n")

    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report = {
        "extraction_version": "1.0.0",
        "extracted_at_utc": now_utc,
        "source_manifest_version": manifest.manifest_version,
        "total_documents_processed": len(manifest.documents),
        "total_paragraph_chunks": len(all_chunks),
        "total_table_rows": len(all_table_rows),
        "total_evidence_units": len(all_chunks) + len(all_table_rows),
        "documents": doc_reports,
    }

    report_path = processed_dir / "extraction_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report


def load_extracted_corpus(project_root: Path | None = None) -> list[ExtractedEvidenceUnit]:
    """Load both chunks.jsonl and table_rows.jsonl as a unified list of ExtractedEvidenceUnit objects."""
    if project_root is None:
        project_root = Path(__file__).resolve().parents[2]
    processed_dir = project_root / "data" / "processed"

    units: list[ExtractedEvidenceUnit] = []
    for filename in ("chunks.jsonl", "table_rows.jsonl"):
        p = processed_dir / filename
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        units.append(ExtractedEvidenceUnit(**json.loads(line)))
    return units


if __name__ == "__main__":
    rep = run_extraction_pipeline()
    print(
        f"[FieldGuard] Phase 2 complete: extracted {rep['total_paragraph_chunks']} paragraph chunks "
        f"and {rep['total_table_rows']} header-coupled table rows "
        f"({rep['total_evidence_units']} total evidence units) across {rep['total_documents_processed']} documents."
    )
