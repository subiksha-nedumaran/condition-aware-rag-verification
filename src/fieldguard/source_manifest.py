"""Source manifest management, SHA-256 verification, and temporal metadata integrity."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SourceDocumentRecord:
    """Metadata and provenance record for an official or candidate source document."""

    document_id: str
    document_title: str
    publisher: str
    source_url: str
    final_url: str | None
    local_path: str
    file_format: str
    document_version: str
    policy_era: str
    publication_date: str | None
    publication_date_status: str
    effective_from: str | None
    effective_to: str | None
    effective_date_status: str
    temporal_applicability_status: str
    retrieval_timestamp_utc: str
    acquisition_mode: str
    http_status_code: int | None
    content_type: str | None
    sha256: str
    file_size_bytes: int
    pdf_signature_valid: bool | None
    html_error_detected: bool
    verification_status: str
    license_and_reuse_notes: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SourceManifest:
    """Container for all acquired corpus documents and manifest-level metadata."""

    manifest_version: str
    created_at_utc: str
    domain: str
    documents: list[SourceDocumentRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "created_at_utc": self.created_at_utc,
            "domain": self.domain,
            "document_count": len(self.documents),
            "documents": [d.to_dict() for d in self.documents],
        }

    def get_document(self, document_id: str) -> SourceDocumentRecord | None:
        for doc in self.documents:
            if doc.document_id == document_id:
                return doc
        return None


def compute_file_sha256(file_path: Path) -> str:
    """Calculate the SHA-256 hex digest of a file."""
    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_html_masquerading_as_pdf(raw_bytes: bytes, content_type: str | None = None) -> bool:
    """
    Detect whether downloaded bytes are an HTML error/login page masquerading as a PDF
    or failing the PDF magic header check.
    """
    if not raw_bytes:
        return True
    prefix = raw_bytes[:512].lstrip().lower()
    if prefix.startswith(b"<!doctype html") or prefix.startswith(b"<html") or b"<head>" in prefix:
        return True
    if content_type and "text/html" in content_type.lower() and not raw_bytes.startswith(b"%PDF-"):
        return True
    return False


def validate_pdf_signature_and_structure(raw_bytes: bytes) -> tuple[bool, str]:
    """
    Validate that a byte buffer has a valid %PDF-1.x header, at least one /Page object,
    and an %%EOF marker.
    """
    if not raw_bytes or len(raw_bytes) < 64:
        return False, "File too small or empty"
    if not raw_bytes.startswith(b"%PDF-"):
        return False, "Missing %PDF- header signature"
    if b"/Type /Page" not in raw_bytes and b"/Type/Page" not in raw_bytes:
        return False, "Missing /Type /Page object in PDF structure"
    if b"%%EOF" not in raw_bytes[-1024:]:
        return False, "Missing %%EOF trailer marker"
    return True, "Valid PDF structure"


def validate_source_manifest(
    manifest: SourceManifest,
    project_root: Path,
) -> tuple[bool, list[str]]:
    """
    Verify integrity of all records in the source manifest:
    1. Local files exist and match recorded SHA-256 and byte sizes.
    2. Confirmed vs unknown metadata statuses are consistent with null/non-null dates.
    3. Effective dates are never inferred merely from publication dates.
    """
    errors: list[str] = []
    seen_ids: set[str] = set()

    for doc in manifest.documents:
        if doc.document_id in seen_ids:
            errors.append(f"Duplicate document_id: {doc.document_id}")
        seen_ids.add(doc.document_id)

        full_path = project_root / doc.local_path
        if not full_path.exists():
            errors.append(f"Missing local file for {doc.document_id}: {full_path}")
            continue

        actual_sha = compute_file_sha256(full_path)
        if actual_sha != doc.sha256:
            errors.append(
                f"SHA-256 mismatch for {doc.document_id}: expected {doc.sha256}, got {actual_sha}"
            )

        actual_size = full_path.stat().st_size
        if actual_size != doc.file_size_bytes:
            errors.append(
                f"File size mismatch for {doc.document_id}: expected {doc.file_size_bytes}, got {actual_size}"
            )

        if doc.publication_date_status == "unknown" and doc.publication_date is not None:
            errors.append(
                f"{doc.document_id}: publication_date_status is 'unknown' but publication_date is set"
            )
        if doc.effective_date_status == "unknown" and doc.effective_from is not None:
            errors.append(
                f"{doc.document_id}: effective_date_status is 'unknown' but effective_from is set"
            )
        if doc.effective_date_status == "inferred_from_publication":
            errors.append(
                f"{doc.document_id}: forbidden effective_date_status 'inferred_from_publication'"
            )

    return len(errors) == 0, errors


def save_source_manifest(
    manifest: SourceManifest,
    json_path: Path,
    csv_path: Path,
) -> None:
    """Write the source manifest to both JSON and CSV formats."""
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(SourceDocumentRecord.__dataclass_fields__.keys())
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for doc in manifest.documents:
            writer.writerow(doc.to_dict())


def load_source_manifest(json_path: Path) -> SourceManifest:
    """Load a SourceManifest from its JSON file."""
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    docs = [SourceDocumentRecord(**d) for d in data.get("documents", [])]
    return SourceManifest(
        manifest_version=data["manifest_version"],
        created_at_utc=data["created_at_utc"],
        domain=data["domain"],
        documents=docs,
    )
