import io
from unittest.mock import patch

import pytest
from pypdf import PdfWriter

from fieldguard.uploaded_doc_engine import UploadedDocumentError, process_uploaded_document, answer_question_from_uploaded_doc
from fieldguard.uploaded_backend import load_uploaded_backend
from fieldguard.retrieval.lexical import LexicalBM25Retriever
from fieldguard.model_setup import ensure_model, MODEL_FILES, MODEL_REVISION


def pdf_bytes(encrypted=False):
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    if encrypted:
        writer.encrypt("secret")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.mark.parametrize("data,name,message", [
    (b"", "empty.txt", "empty"),
    (b"   ", "blank.txt", "no readable text"),
    (b"\xff\xfe", "bad.txt", "UTF-8"),
    (b"%PDF-broken", "bad.pdf", "could not be read"),
    (pdf_bytes(), "scan.pdf", "OCR"),
    (pdf_bytes(True), "locked.pdf", "encrypted"),
])
def test_unreadable_uploads_fail_clearly(data, name, message):
    with pytest.raises(UploadedDocumentError, match=message):
        process_uploaded_document(data, name)


def test_upload_cache_is_per_session_and_invalidated_by_content_or_name():
    first, second = {}, {}
    with patch("fieldguard.evaluation.runner.build_all_retrievers", return_value={}) as build:
        original = load_uploaded_backend(first, b"Women receive 50 percent assistance.", "a.txt")
        assert load_uploaded_backend(first, b"Women receive 50 percent assistance.", "a.txt") is original
        assert build.call_count == 1
        load_uploaded_backend(first, b"Women receive 40 percent assistance.", "a.txt")
        load_uploaded_backend(first, b"Women receive 40 percent assistance.", "b.txt")
        load_uploaded_backend(second, b"Women receive 40 percent assistance.", "b.txt")
        assert build.call_count == 4
        with pytest.raises(UploadedDocumentError):
            load_uploaded_backend(first, b"", "bad.txt")
        assert "fieldguard_upload_backend" not in first


@pytest.mark.parametrize("question,status", [
    ("What assistance do women receive?", "retrieved_excerpts"),
    ("What are the passport renewal fees?", "insufficient_evidence"),
    ("What is the policy?", "insufficient_evidence"),
    ("", "insufficient_evidence"),
])
def test_excerpt_relevance_and_abstention(question, status):
    store, units, _ = process_uploaded_document(b"Women receive 50 percent assistance.", "a.txt")
    result = answer_question_from_uploaded_doc(question, store, {"lexical": LexicalBM25Retriever(units)})
    assert result["status"] == status
    if status == "insufficient_evidence":
        assert not result["citations"] and not result["top_chunks"]
    else:
        assert "not a synthesized answer" in result["answer"]
        assert "Page 1" in result["citations"][0]


def test_missing_model_has_actionable_offline_error():
    with patch("huggingface_hub.snapshot_download", side_effect=OSError("not cached")) as download:
        with pytest.raises(RuntimeError, match="model_setup --download"):
            ensure_model()
        assert download.call_args.kwargs["local_files_only"] is True
        assert download.call_args.kwargs["revision"] == MODEL_REVISION


def test_model_download_is_explicit_and_checks_completeness(tmp_path):
    with patch("huggingface_hub.snapshot_download", return_value=str(tmp_path)) as download:
        with pytest.raises(RuntimeError, match="incomplete"):
            ensure_model(download=True)
        assert download.call_args.kwargs["local_files_only"] is False
        for name in MODEL_FILES:
            (tmp_path / name).write_text("fixture")
        assert ensure_model() == tmp_path
