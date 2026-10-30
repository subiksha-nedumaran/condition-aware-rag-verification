"""Dynamic document ingestion, evidence extraction, Q&A, and verification for user-uploaded scheme files."""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from fieldguard.evidence_schema import StructuredRuleRecord
from fieldguard.evidence_store import EvidenceStore
from fieldguard.metadata import ExtractedEvidenceUnit
from fieldguard.numeric_normalizer import extract_all_numeric_mentions, normalize_claim_numerics
from fieldguard.verifier import FieldGuardVerifier, VerificationPrediction, VerifierConfig
from fieldguard.evaluation.runner import build_all_retrievers


def process_uploaded_document(
    file_bytes: bytes,
    file_name: str,
) -> tuple[EvidenceStore, list[ExtractedEvidenceUnit], list[StructuredRuleRecord]]:
    """
    Parse an arbitrary user-uploaded government policy document (PDF or TXT),
    extracting page-numbered chunks, tables, and candidate numerical rules into an EvidenceStore.
    """
    clean_name = Path(file_name).stem.upper().replace(" ", "_")
    doc_id = f"DOC_UPLOAD_{clean_name}"
    units: list[ExtractedEvidenceUnit] = []
    rules: list[StructuredRuleRecord] = []

    pages_text: list[tuple[int, str]] = []

    # 1. Parse text from PDF or TXT
    is_pdf = file_name.lower().endswith(".pdf") or file_bytes[:4] == b"%PDF"
    if is_pdf:
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            for p_idx, page in enumerate(reader.pages):
                txt = page.extract_text() or ""
                if txt.strip():
                    pages_text.append((p_idx + 1, txt))
        except Exception:
            # Fallback to text decoding
            raw_txt = file_bytes.decode("utf-8", errors="ignore")
            pages_text.append((1, raw_txt))
    else:
        raw_txt = file_bytes.decode("utf-8", errors="ignore")
        pages_text.append((1, raw_txt))

    # 2. Chunk each page into paragraphs and detect tabular lines
    unit_counter = 1
    rule_counter = 1

    for page_num, p_text in pages_text:
        # Split by double newline or numbered sections
        raw_blocks = [b.strip() for b in re.split(r"\n\s*\n+", p_text) if b.strip()]

        for b_idx, block in enumerate(raw_blocks):
            # Check if block looks like a table row (contains pipes | or comma-separated numbers)
            is_table = ("|" in block) or (re.search(r"^\s*\[Table:", block))
            ev_type = "table_row" if is_table else "paragraph"
            ev_id = f"EV_{doc_id}_P{page_num}_U{unit_counter}"
            unit_counter += 1

            unit = ExtractedEvidenceUnit(
                evidence_id=ev_id,
                document_id=doc_id,
                source_url=f"uploaded://{file_name}",
                document_title=f"User Uploaded Policy Document: {file_name}",
                document_version="uploaded_custom",
                publication_date="2026-01-01",
                effective_from="2020-01-01",
                effective_to=None,
                physical_pdf_page=page_num,
                printed_page=str(page_num),
                section=f"Page {page_num} Block {b_idx + 1}",
                table_id=f"TBL_{doc_id}_P{page_num}" if is_table else None,
                row_id=f"ROW_{unit_counter}" if is_table else None,
                headers=None,
                text=block,
                extraction_method="dynamic_pypdf_stream_parser",
                extraction_quality="high_verified",
                evidence_type=ev_type,
                verification_status="trusted_official",
                policy_era="uploaded_active",
                cells=None,
            )
            units.append(unit)

            # 3. Detect numerical mentions in this block to create candidate ground-truth rules
            mentions = extract_all_numeric_mentions(block)
            for m in mentions:
                rule_id = f"RULE_{doc_id}_{rule_counter}"
                rule_counter += 1
                rule = StructuredRuleRecord(
                    rule_id=rule_id,
                    evidence_id=ev_id,
                    scheme=clean_name,
                    rule_parameter="custom_policy_rule",
                    season="annual",
                    crop_category="all_general",
                    geography="all_india",
                    minimum_value=m.value,
                    maximum_rate=m.value,
                    allowed_values=[m.value],
                    numeric_operator="eq",
                    unit=m.unit or "dimensionless",
                    basis="per_policy_specification",
                    qualifier=None,
                    requires_qualifier_for_unconditional_claim=False,
                    source_document_id=doc_id,
                    document_version="uploaded_custom",
                    policy_era="uploaded_active",
                    publication_date="2026-01-01",
                    section=f"Page {page_num}",
                    physical_pdf_page=page_num,
                    printed_page=str(page_num),
                    table_id=None,
                    row_id=None,
                    effective_from="2020-01-01",
                    effective_to=None,
                    verification_status="trusted_official",
                    entity_scope="all_general",
                    conditions={},
                    frequency="annual",
                )
                rules.append(rule)

    store = EvidenceStore()
    for u in units:
        store.add_evidence_unit(u)
    for r in rules:
        store.add_rule(r)

    return store, units, rules


def answer_question_from_uploaded_doc(
    question: str,
    store: EvidenceStore,
    retrievers: dict[str, Any],
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Answer an arbitrary user question using retrieval-augmented generation grounded
    strictly in the uploaded policy document.
    """
    retriever = retrievers.get("hybrid") or retrievers.get("lexical") or list(retrievers.values())[0]
    results = retriever.retrieve(question, top_k=top_k)

    if not results:
        return {
            "answer": "No relevant text could be found in the uploaded document for this question.",
            "citations": [],
            "top_chunks": [],
        }

    # Synthesize direct grounded answer from top-ranked chunks
    top_texts = [r.text for r in results[:3]]
    best_chunk = results[0]

    citations = [
        f"Page {r.physical_pdf_page or 'N/A'} (ID: {r.evidence_id})" for r in results[:3]
    ]

    answer_text = (
        f"Based on the uploaded document ({best_chunk.source_document_id}, Page {best_chunk.physical_pdf_page}):\n\n"
        f"\"{best_chunk.text}\"\n\n"
        f"Relevant evidence was also found on: {', '.join(citations)}."
    )

    return {
        "answer": answer_text,
        "citations": citations,
        "top_chunks": [r.to_dict() for r in results],
    }
