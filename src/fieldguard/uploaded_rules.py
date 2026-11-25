"""Lossless candidate records for uploads, separate from verified policy rules."""

from dataclasses import asdict, dataclass
import re
from typing import Any

from fieldguard.numeric_normalizer import extract_all_numeric_mentions


@dataclass
class UploadedCandidateRule:
    rule_id: str
    evidence_id: str
    source_document_id: str
    physical_pdf_page: int
    raw_mention: str
    mention_start: int
    mention_end: int
    value: float
    unit: str
    numeric_operator: str | None
    minimum_value: float | None
    maximum_value: float | None
    allowed_values: list[float] | None
    qualifier: str | None
    conditions: dict[str, Any]
    verification_status: str = "user_uploaded_unverified"
    publication_date: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_OPERATORS = (
    (r"(?:up to|at most|no more than|not more than|not exceeding|capped at|maximum(?: of)?|<=|≤)", "le"),
    (r"(?:at least|no less than|not less than|minimum(?: of)?|>=|≥)", "ge"),
    (r"(?:less than|below|<)", "lt"),
    (r"(?:more than|greater than|above|>)", "gt"),
    (r"(?:exactly|equal to|=)", "eq"),
)


def extract_uploaded_candidates(text: str, evidence_id: str, document_id: str,
                                page: int) -> list[UploadedCandidateRule]:
    """Attach only explicit local operators; preserve unresolved context verbatim.

    Offsets point into the original passage. Operators are never borrowed from a
    different numerical mention. Unknown operators and dates remain null.
    """
    spans = {}
    for mention in extract_all_numeric_mentions(text):
        for match in re.finditer(re.escape(mention.raw_text), text, re.IGNORECASE):
            spans[match.span()] = mention
    selected = []
    for (start, end), mention in sorted(spans.items(), key=lambda item: (item[0][0], -item[0][1])):
        if selected and start < selected[-1][1]:
            continue
        selected.append((start, end, mention))

    qualifiers = re.findall(r"\bwhichever\s+is\s+(?:less|lower|higher|greater)\b", text, re.I)
    frequencies = re.findall(r"\b(?:annually|monthly|quarterly|yearly|weekly|daily|per\s+(?:year|month|day|household|family|hectare))\b", text, re.I)
    candidates = []
    previous_end = 0
    for start, end, mention in selected:
        prefix = re.sub(r"\s+", " ", text[previous_end:start]).casefold().rstrip()
        operator = None
        for pattern, value in _OPERATORS:
            if re.search(r"(?<!\w)" + pattern + r"\s*$", prefix):
                operator = value
                break
        candidates.append(UploadedCandidateRule(
            rule_id=f"RULE_{evidence_id}_{len(candidates) + 1}",
            evidence_id=evidence_id, source_document_id=document_id, physical_pdf_page=page,
            raw_mention=text[start:end], mention_start=start, mention_end=end,
            value=mention.value, unit=mention.unit, numeric_operator=operator,
            minimum_value=mention.value if operator in ("ge", "gt", "eq") else None,
            maximum_value=mention.value if operator in ("le", "lt", "eq") else None,
            allowed_values=[mention.value] if operator == "eq" else None,
            qualifier="; ".join(qualifiers) or None,
            conditions={"source_passage": text, "interpretation_status": "unverified",
                        "frequency_and_basis_phrases": frequencies,
                        "qualifier_scope": "whole_passage" if qualifiers else None},
        ))
        previous_end = end
    return candidates
