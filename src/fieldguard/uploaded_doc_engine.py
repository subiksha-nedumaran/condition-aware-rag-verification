"""Dynamic document ingestion, evidence extraction, Q&A, and verification for user-uploaded scheme files."""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from fieldguard.evidence_store import EvidenceStore
from fieldguard.metadata import ExtractedEvidenceUnit
from fieldguard.retrieval.lexical import STOPWORDS
from fieldguard.uploaded_rules import UploadedCandidateRule, extract_uploaded_candidates


class UploadedDocumentError(ValueError):
    """An upload cannot be safely interpreted as text evidence."""


_COMPOUND_HYPHEN_PREFIXES = {
    "non", "pre", "post", "sub", "co", "re", "semi", "multi", "self", "agro",
    "inter", "intra", "micro", "short", "long", "one", "two", "three", "four",
    "five", "six", "first", "second", "third", "part", "full", "geo", "on",
    "off", "in", "out", "up", "low", "high", "mid", "ex", "bi", "tri", "anti",
    "pro", "pan", "socio", "eco", "bio", "grid", "day", "person", "man",
    "interest", "cost", "time", "state", "central", "district", "block",
    "village", "gram", "water", "solar", "wind", "crop", "weather", "yield",
    "area", "index", "bank", "aadhaar", "seed", "tax", "free", "based",
    "linked", "owned", "led", "scale", "term", "level", "wise", "type",
    "class", "group", "tier", "phase", "component", "cut", "and", "spread",
    "single", "double", "all", "cross", "over", "under", "well", "ill",
}


def clean_extracted_pdf_text(text: str) -> str:
    """
    Normalize raw PDF or TXT text to repair:
    1. Broken word hyphenation across line wraps (e.g. 'sub-\\nsidy' -> 'subsidy',
       while preserving compound prefixes like 'four-\\nmonthly' -> 'four-monthly').
    2. Broken Indian number formatting (e.g. '1, 20, 000' or '1,\\n20,000' -> '1,20,000').
    3. Broken currency / number-unit line wraps (e.g. 'Rs.\\n1,20,000' -> 'Rs. 1,20,000').
    """
    if not text:
        return ""

    out = text.replace("\r\n", "\n").replace("\r", "\n")

    # 1. Fix hyphenated line breaks
    def _replace_hyphen_wrap(match: re.Match[str]) -> str:
        prefix = match.group(1)
        suffix = match.group(2)
        if (
            prefix.lower() in _COMPOUND_HYPHEN_PREFIXES
            or suffix[0].isupper()
            or suffix[0].isdigit()
            or prefix.isupper()
        ):
            return f"{prefix}-{suffix}"
        return f"{prefix}{suffix}"

    out = re.sub(r"([A-Za-z]{2,})-\s*\n\s*([A-Za-z0-9]{2,})", _replace_hyphen_wrap, out)

    # 2. Fix spaces or line wraps inside Indian/standard comma-separated numbers (run 3 times for 1, 20, 000)
    for _ in range(3):
        out = re.sub(r"(\d),\s+(\d{2,3})(?!\d)", r"\1,\2", out)

    # 3. Fix currency symbol separated from digits by newline
    out = re.sub(r"\b(Rs\.?|INR|₹)\s*\n\s*(\d)", r"\1 \2", out, flags=re.IGNORECASE)

    # 4. Fix number separated from unit by single newline (when next line is not a bullet/table)
    out = re.sub(
        r"(\d(?:[\d,]*\d)?(?:\.\d+)?)\s*\n\s*(%|percent|per\s+cent|lakh|lakhs|crore|crores|"
        r"rupees?|days?|months?|years?|hours?|hectares?|ha|acres?|sq\.?\s*metres?|square\s+metres?|"
        r"hp|horsepower|kw|mw|kwh|km|kilometres?|instalments?|installments?|tonnes?|quintals?)\b",
        r"\1 \2",
        out,
        flags=re.IGNORECASE,
    )

    return out


def _extract_pdf_pages_with_fallback(file_bytes: bytes) -> list[tuple[int, str]]:
    """Extract page text via pypdf, with fallback to pdfplumber or PyMuPDF (fitz) when pypdf yields little text."""
    pages_text: list[tuple[int, str]] = []
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        if reader.is_encrypted:
            raise UploadedDocumentError("This PDF is encrypted. Upload a decrypted copy.")
        for p_idx, page in enumerate(reader.pages):
            txt = clean_extracted_pdf_text(page.extract_text() or "")
            if txt.strip():
                pages_text.append((p_idx + 1, txt))
    except UploadedDocumentError:
        raise
    except Exception as exc:
        # Try fallback extractors before raising
        pages_text = []
        fallback_ok = False
        try:
            import pdfplumber  # type: ignore

            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for p_idx, page in enumerate(pdf.pages):
                    txt = clean_extracted_pdf_text(page.extract_text() or "")
                    if txt.strip():
                        pages_text.append((p_idx + 1, txt))
                fallback_ok = True
        except Exception:
            pass

        if not fallback_ok:
            try:
                import fitz  # type: ignore

                doc = fitz.open(stream=file_bytes, filetype="pdf")
                for p_idx, page in enumerate(doc):
                    txt = clean_extracted_pdf_text(page.get_text("text") or "")
                    if txt.strip():
                        pages_text.append((p_idx + 1, txt))
                fallback_ok = True
            except Exception:
                pass

        if not fallback_ok and not pages_text:
            raise UploadedDocumentError(
                "This PDF could not be read. Upload a valid, readable PDF or UTF-8 TXT file."
            ) from exc

    total_chars = sum(len(t.strip()) for _, t in pages_text)
    if total_chars < 20:
        # Attempt fallback extractors if pypdf returned little or no text
        try:
            import pdfplumber  # type: ignore

            alt_pages: list[tuple[int, str]] = []
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for p_idx, page in enumerate(pdf.pages):
                    txt = clean_extracted_pdf_text(page.extract_text() or "")
                    if txt.strip():
                        alt_pages.append((p_idx + 1, txt))
            if sum(len(t.strip()) for _, t in alt_pages) > total_chars:
                pages_text = alt_pages
                total_chars = sum(len(t.strip()) for _, t in pages_text)
        except Exception:
            pass

    if total_chars < 20:
        try:
            import fitz  # type: ignore

            alt_pages = []
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for p_idx, page in enumerate(doc):
                txt = clean_extracted_pdf_text(page.get_text("text") or "")
                if txt.strip():
                    alt_pages.append((p_idx + 1, txt))
            if sum(len(t.strip()) for _, t in alt_pages) > total_chars:
                pages_text = alt_pages
        except Exception:
            pass

    if not pages_text:
        raise UploadedDocumentError(
            "No extractable text found in this PDF. Scanned or image-only PDFs require OCR before upload."
        )
    return pages_text


def _split_block_into_units(block: str) -> list[tuple[str, str, list[str] | None, list[str] | None]]:
    """
    Split a raw page block into (evidence_type, normalized_text, headers, cells) items.
    Handles:
      - Multi-line pipe tables (with header row)
      - Single-line pipe rows (kept verbatim)
      - Multi-column tab / multi-space tables (with header row)
      - Multi-column side-by-side prose blocks (Left Col || Right Col)
      - Bullet / numbered lists
      - Wrapped prose paragraphs
    """
    lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
    if not lines:
        return []

    # 1. Single-line block
    if len(lines) == 1:
        single = lines[0]
        is_table = ("|" in single) or bool(re.search(r"^\s*\[Table:", single))
        return [("table_row" if is_table else "paragraph", single, None, None)]

    # 2. Multi-line pipe table (at least 2 lines containing '|')
    pipe_lines = [ln for ln in lines if "|" in ln]
    if len(pipe_lines) >= 2:
        # Check if there is a title/caption line before the pipe lines
        non_pipe_prefix = [ln for ln in lines if "|" not in ln]
        caption_prefix = (" ".join(non_pipe_prefix) + " — ") if non_pipe_prefix else ""

        # Filter out markdown separator lines like |---|---|
        data_pipe_lines = [
            ln for ln in pipe_lines if not re.fullmatch(r"[\s|:\-]+", ln)
        ]
        if len(data_pipe_lines) >= 2:
            first_cells = [c.strip() for c in data_pipe_lines[0].strip("|").split("|") if c.strip()]
            # Check if first line is a header row (no standalone digits or has header-like labels)
            first_has_digits = bool(re.search(r"\b\d+(?:\.\d+)?\s*(?:%|rs|inr|₹|days|months|years|hp|kw|mw|ha|sqm|lakh)\b", data_pipe_lines[0], re.I))
            if first_cells and not first_has_digits:
                headers = first_cells
                out_rows: list[tuple[str, str, list[str] | None, list[str] | None]] = []
                for row_ln in data_pipe_lines[1:]:
                    cells = [c.strip() for c in row_ln.strip("|").split("|") if c.strip()]
                    if not cells:
                        continue
                    paired = [
                        f"{headers[i]}: {cells[i]}" if i < len(headers) else cells[i]
                        for i in range(len(cells))
                    ]
                    row_text = f"{caption_prefix}{' | '.join(paired)}"
                    out_rows.append(("table_row", row_text, headers, cells))
                if out_rows:
                    return out_rows
        # Fallback: each pipe line is its own table row
        return [("table_row", f"{caption_prefix}{ln}", None, None) for ln in data_pipe_lines]

    # 3. Multi-column tabular block separated by tabs or 2+ spaces (with header row)
    col_split_lines = [re.split(r"\t+|\s{2,}", ln) for ln in lines]
    if len(lines) >= 3 and all(len(cols) >= 2 for cols in col_split_lines):
        col_counts = {len(cols) for cols in col_split_lines}
        if len(col_counts) == 1:
            headers = [c.strip() for c in col_split_lines[0]]
            first_has_num = bool(re.search(r"\b\d+\b", lines[0]))
            if not first_has_num:
                out_rows = []
                for cols in col_split_lines[1:]:
                    cells = [c.strip() for c in cols]
                    paired = [f"{headers[i]}: {cells[i]}" for i in range(len(cells))]
                    out_rows.append(("table_row", " | ".join(paired), headers, cells))
                return out_rows
            else:
                # Two-column side-by-side layout where each column is an independent clause/field
                out_units: list[tuple[str, str, list[str] | None, list[str] | None]] = []
                num_cols = len(col_split_lines[0])
                for c_idx in range(num_cols):
                    col_text = " ".join(cols[c_idx].strip() for cols in col_split_lines if c_idx < len(cols))
                    if col_text.strip():
                        out_units.append(("paragraph", col_text.strip(), None, None))
                if out_units:
                    return out_units

    # 4. Bullet / numbered list block
    bullet_re = re.compile(r"^\s*(?:[-•*]|\(\d+\)|\([a-zA-Z]\)|\d+[.)])\s+")
    bullet_indices = [i for i, ln in enumerate(lines) if bullet_re.match(ln)]
    if len(bullet_indices) >= 2:
        header_lines = lines[: bullet_indices[0]]
        header_prefix = (" ".join(header_lines).rstrip(":") + ": ") if header_lines else ""
        items: list[str] = []
        for idx_pos, line_idx in enumerate(bullet_indices):
            next_line_idx = bullet_indices[idx_pos + 1] if idx_pos + 1 < len(bullet_indices) else len(lines)
            item_text = " ".join(lines[line_idx:next_line_idx])
            item_clean = bullet_re.sub("", item_text, count=1).strip()
            items.append(f"{header_prefix}{item_clean}")
        return [("paragraph", it, None, None) for it in items if it.strip()]

    # 5. Standard wrapped prose paragraph: join single newlines into spaces
    joined = re.sub(r"\s+", " ", " ".join(lines)).strip()
    is_table = ("|" in joined) or bool(re.search(r"^\s*\[Table:", joined))
    return [("table_row" if is_table else "paragraph", joined, None, None)]


def process_uploaded_document(
    file_bytes: bytes,
    file_name: str,
) -> tuple[EvidenceStore, list[ExtractedEvidenceUnit], list[UploadedCandidateRule]]:
    """
    Parse an arbitrary user-uploaded government policy document (PDF or TXT),
    extracting page-numbered chunks, tables, and candidate numerical rules into an EvidenceStore.
    """
    if not file_bytes:
        raise UploadedDocumentError("The uploaded file is empty.")
    clean_name = Path(file_name).stem.upper().replace(" ", "_")
    doc_id = f"DOC_UPLOAD_{clean_name}"
    units: list[ExtractedEvidenceUnit] = []
    rules: list[UploadedCandidateRule] = []

    pages_text: list[tuple[int, str]] = []

    # 1. Parse text from PDF or TXT
    is_pdf = file_name.lower().endswith(".pdf") or file_bytes[:4] == b"%PDF"
    if is_pdf:
        pages_text = _extract_pdf_pages_with_fallback(file_bytes)
    else:
        try:
            raw_txt = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise UploadedDocumentError("The TXT file must use UTF-8 encoding.") from exc
        if not raw_txt.strip():
            raise UploadedDocumentError("The uploaded file contains no readable text.")
        pages_text.append((1, clean_extracted_pdf_text(raw_txt)))

    # 2. Chunk each page into paragraphs, bullet items, and table rows
    unit_counter = 1

    for page_num, p_text in pages_text:
        raw_blocks = [b.strip() for b in re.split(r"\n\s*\n+", p_text) if b.strip()]

        for b_idx, block in enumerate(raw_blocks):
            sub_units = _split_block_into_units(block)
            for ev_type, norm_text, headers, cells in sub_units:
                ev_id = f"EV_{doc_id}_P{page_num}_U{unit_counter}"
                unit_counter += 1

                unit = ExtractedEvidenceUnit(
                    evidence_id=ev_id,
                    document_id=doc_id,
                    source_url=f"uploaded://{file_name}",
                    document_title=f"User Uploaded Policy Document: {file_name}",
                    document_version="uploaded_custom",
                    publication_date=None,
                    effective_from=None,
                    effective_to=None,
                    physical_pdf_page=page_num,
                    printed_page=str(page_num),
                    section=f"Page {page_num} Block {b_idx + 1}",
                    table_id=f"TBL_{doc_id}_P{page_num}" if ev_type == "table_row" else None,
                    row_id=f"ROW_{unit_counter}" if ev_type == "table_row" else None,
                    headers=headers,
                    text=norm_text,
                    extraction_method="dynamic_pypdf_stream_parser",
                    extraction_quality="unverified",
                    evidence_type=ev_type,
                    verification_status="user_uploaded_unverified",
                    policy_era="uploaded_unknown",
                    cells=cells,
                )
                units.append(unit)

                # Preserve bounds and full conditions without manufacturing trusted policy rules.
                rules.extend(extract_uploaded_candidates(norm_text, ev_id, doc_id, page_num))

    store = EvidenceStore()
    for u in units:
        store.register_evidence_unit(u)
    # Candidate mentions are attached for candidate-rule verification, never inserted as trusted_rules.
    store.uploaded_candidates = list(rules)

    return store, units, rules


def answer_question_from_uploaded_doc(
    question: str,
    store: EvidenceStore,
    retrievers: dict[str, Any],
    top_k: int = 5,
) -> dict[str, Any]:
    """Return relevant source excerpts, not a generated or verified policy answer.

    RRF scores are ranks, not relevance probabilities. Require lexical coverage
    independently and resolve returned IDs against the actual evidence store.
    """
    retriever = retrievers.get("hybrid") or retrievers.get("lexical") or next(iter(retrievers.values()), None)
    ignored = STOPWORDS | {"how", "many", "much", "and", "or", "please", "tell", "me", "document", "policy"}
    terms = set(re.findall(r"[a-z0-9]+", question.casefold())) - ignored
    ranked = retriever.retrieve(question, top_k=top_k) if retriever and terms and top_k > 0 else []
    results = []
    seen = set()
    for item in ranked:
        unit = store.get_evidence_unit(item.evidence_id)
        if unit is None or unit.evidence_id in seen:
            continue
        words = set(re.findall(r"[a-z0-9]+", unit.text.casefold()))
        if len(terms & words) / len(terms) < 0.5:
            continue
        # Never display text supplied by a retriever in place of stored evidence.
        results.append(type(item).from_unit(unit, len(results) + 1, item.retrieval_score, item.retriever_name))
        seen.add(unit.evidence_id)

    if not results:
        return {
            "answer": "No relevant text could be found in the uploaded document for this question.",
            "citations": [],
            "top_chunks": [],
            "status": "insufficient_evidence",
        }

    # Quote source text without presenting retrieval as answer generation.
    best_chunk = results[0]

    citations = [
        f"Page {r.physical_pdf_page or 'N/A'} (ID: {r.evidence_id})" for r in results[:3]
    ]

    answer_text = (
        f"Retrieved excerpt ({best_chunk.source_document_id}, Page {best_chunk.physical_pdf_page}):\n\n"
        f"\"{best_chunk.text}\"\n\n"
        "This is a source excerpt, not a synthesized answer or verification of official policy."
    )

    return {
        "answer": answer_text,
        "citations": citations,
        "top_chunks": [r.to_dict() for r in results],
        "status": "retrieved_excerpts",
    }


def build_valid_pdf_bytes(pages: list[list[str]] | list[str]) -> bytes:
    """Build a valid single-page or multi-page PDF byte stream readable by pypdf."""
    if not pages:
        page_lists: list[list[str]] = [[""]]
    elif isinstance(pages[0], str):
        page_lists = [list(pages)]  # type: ignore[arg-type]
    else:
        page_lists = [list(p) for p in pages]  # type: ignore[arg-type]

    def _escape_pdf_str(s: str) -> str:
        return (
            s.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )

    objects: list[bytes] = []
    # Obj 1: Catalog
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    # Obj 2: Pages placeholder (filled after creating page objects)
    objects.append(b"")
    # Obj 3: Font
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_obj_nums: list[int] = []
    for p_lines in page_lists:
        stream_cmds = ["BT", "/F1 10 Tf", "50 760 Td"]
        for idx, line in enumerate(p_lines):
            if idx > 0:
                stream_cmds.append("0 -14 Td")
            stream_cmds.append(f"({_escape_pdf_str(line)}) Tj")
        stream_cmds.append("ET")
        stream_bytes = "\n".join(stream_cmds).encode("latin-1", errors="replace")

        content_obj_num = len(objects) + 1
        objects.append(
            f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
            + stream_bytes
            + b"\nendstream"
        )

        page_obj_num = len(objects) + 1
        page_obj_nums.append(page_obj_num)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_obj_num} 0 R >>".encode("ascii")
        )

    kids_str = " ".join(f"{n} 0 R" for n in page_obj_nums)
    objects[1] = f"<< /Type /Pages /Kids [{kids_str}] /Count {len(page_obj_nums)} >>".encode("ascii")

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = [0]
    for idx, obj_body in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{idx} 0 obj\n".encode("ascii"))
        out.extend(obj_body)
        out.extend(b"\nendobj\n")

    xref_offset = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    out.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(out)

