"""Evidence unit schema and provenance metadata propagation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from fieldguard.source_manifest import SourceDocumentRecord

REQUIRED_EVIDENCE_FIELDS: tuple[str, ...] = (
    "evidence_id",
    "document_id",
    "source_url",
    "document_title",
    "document_version",
    "publication_date",
    "effective_from",
    "effective_to",
    "physical_pdf_page",
    "printed_page",
    "section",
    "table_id",
    "row_id",
    "headers",
    "text",
    "extraction_method",
    "extraction_quality",
)


@dataclass
class ExtractedEvidenceUnit:
    """
    Standardized extracted evidence unit (paragraph chunk or table row)
    preserving complete provenance and physical vs printed pagination.
    """

    evidence_id: str
    document_id: str
    source_url: str
    document_title: str
    document_version: str
    publication_date: str | None
    effective_from: str | None
    effective_to: str | None
    physical_pdf_page: int | None
    printed_page: str | None
    section: str | None
    table_id: str | None
    row_id: str | None
    headers: list[str] | None
    text: str
    extraction_method: str
    extraction_quality: str
    evidence_type: str = "paragraph"
    verification_status: str = "trusted_official"
    policy_era: str = "guidelines_2023"
    cells: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_evidence_unit_schema(unit: dict[str, Any]) -> tuple[bool, list[str]]:
    """Verify that an extracted evidence unit dictionary has all required fields and valid provenance."""
    errors: list[str] = []
    for req in REQUIRED_EVIDENCE_FIELDS:
        if req not in unit:
            errors.append(f"Missing required field '{req}' in evidence_id={unit.get('evidence_id')}")

    if not unit.get("evidence_id"):
        errors.append("Empty evidence_id")
    if not unit.get("document_id"):
        errors.append(f"Empty document_id for {unit.get('evidence_id')}")
    if not unit.get("text") or not str(unit.get("text")).strip():
        errors.append(f"Empty text for {unit.get('evidence_id')}")

    if unit.get("table_id") is not None:
        headers = unit.get("headers")
        if not isinstance(headers, list) or len(headers) == 0:
            errors.append(
                f"Table row {unit.get('evidence_id')} is detached from its column headers (headers={headers})"
            )

    return len(errors) == 0, errors


def build_provenance_kwargs(doc: SourceDocumentRecord) -> dict[str, Any]:
    """Extract document-level provenance fields from a SourceDocumentRecord."""
    return {
        "document_id": doc.document_id,
        "source_url": doc.source_url,
        "document_title": doc.document_title,
        "document_version": doc.document_version,
        "publication_date": doc.publication_date,
        "effective_from": doc.effective_from,
        "effective_to": doc.effective_to,
        "verification_status": doc.verification_status,
        "policy_era": doc.policy_era,
    }
