"""Common retriever interface and provenance-preserving result schema (Section 9.5)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any

from fieldguard.metadata import ExtractedEvidenceUnit


@dataclass
class RetrievedEvidenceItem:
    """
    Standardized retrieval result item returned by all FieldGuard retrievers.
    Preserves complete provenance, pagination, table headers, and verification status.
    """

    evidence_id: str
    text: str
    rank: int
    retrieval_score: float
    source_document_id: str
    document_version: str
    section: str | None
    physical_pdf_page: int | None
    printed_page: str | None
    evidence_type: str
    table_id: str | None = None
    row_id: str | None = None
    headers: list[str] | None = None
    verification_status: str = "trusted_official"
    retriever_name: str = "base"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_unit(
        cls,
        unit: ExtractedEvidenceUnit,
        rank: int,
        score: float,
        retriever_name: str,
    ) -> RetrievedEvidenceItem:
        return cls(
            evidence_id=unit.evidence_id,
            text=unit.text,
            rank=int(rank),
            retrieval_score=round(float(score), 6),
            source_document_id=unit.document_id,
            document_version=unit.document_version,
            section=unit.section,
            physical_pdf_page=unit.physical_pdf_page,
            printed_page=unit.printed_page,
            evidence_type=unit.evidence_type,
            table_id=unit.table_id,
            row_id=unit.row_id,
            headers=unit.headers,
            verification_status=unit.verification_status,
            retriever_name=retriever_name,
        )


class BaseRetriever(ABC):
    """Abstract base class for all FieldGuard retrievers."""

    retriever_name: str = "base"

    def __init__(self, corpus_units: list[ExtractedEvidenceUnit]) -> None:
        self.corpus_units = list(corpus_units)
        self.unit_by_id: dict[str, ExtractedEvidenceUnit] = {
            u.evidence_id: u for u in self.corpus_units
        }

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedEvidenceItem]:
        """Return top_k Ranked RetrievedEvidenceItem objects for `query`."""
        raise NotImplementedError
