"""Unit and integration tests for FieldGuard FastAPI Server & Next-Level API.
Tests all endpoints: /api/health, /api/schemes, /api/verify, /api/qa, /api/upload, /api/certificate, /api/benchmark-stats, and frontend serving.
"""

from __future__ import annotations

import io
import pytest
from fastapi.testclient import TestClient

from fieldguard.server import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "3.0.0"
    assert data["accuracy_held_out"] == 0.9405
    assert data["false_support_rate"] == 0.0263


def test_schemes_endpoint():
    response = client.get("/api/schemes")
    assert response.status_code == 200
    data = response.json()
    assert "schemes" in data
    schemes = data["schemes"]
    assert len(schemes) >= 7
    scheme_ids = [s["id"] for s in schemes]
    assert "PMFBY" in scheme_ids
    assert "PM_KISAN" in scheme_ids
    assert "MGNREGA" in scheme_ids
    assert "PM_JAY" in scheme_ids
    assert "PMAY_G" in scheme_ids
    assert "PM_KUSUM" in scheme_ids
    assert "PMMY" in scheme_ids

    # Each scheme must have scenarios
    for s in schemes:
        assert len(s["scenarios"]) >= 1


def test_verify_pmfby_supported():
    payload = {
        "scheme_id": "PMFBY",
        "question": "What is the maximum premium rate payable by a farmer for Kharif food grains under PMFBY?",
        "candidate_claim": "Farmers pay a maximum premium of 2.0% for Kharif food grain and oilseed crops under PMFBY.",
        "retrieval_method": "hybrid",
        "top_k": 5
    }
    response = client.post("/api/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] == "SUPPORTED"
    assert len(data["condition_checks"]) > 0
    assert len(data["condition_diff"]) > 0
    assert len(data["retrieved_evidence"]) > 0
    assert data["latency_ms"] >= 0


def test_verify_pmfby_wrong_context():
    payload = {
        "scheme_id": "PMFBY",
        "question": "What is the premium rate for commercial and horticultural crops under PMFBY?",
        "candidate_claim": "Farmers pay 2.0% premium for commercial and horticultural crops.",
        "retrieval_method": "hybrid",
        "top_k": 5
    }
    response = client.post("/api/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] in ("WRONG_CONTEXT", "CONTRADICTED")
    assert len(data["condition_checks"]) > 0


def test_verify_pm_kisan_supported():
    payload = {
        "scheme_id": "PM_KISAN",
        "question": "What is the annual financial benefit provided to farmers under PM-KISAN?",
        "candidate_claim": "Eligible farmer families receive financial support of Rs. 6000 per year under PM-KISAN.",
        "retrieval_method": "hybrid",
        "top_k": 5
    }
    response = client.post("/api/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] == "SUPPORTED"


def test_policy_qa_endpoint():
    payload = {
        "scheme_id": "PMFBY",
        "question": "What is the premium for Rabi food crops?",
        "top_k": 3
    }
    response = client.post("/api/qa", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert len(data["answer"]) > 10
    assert len(data["top_chunks"]) > 0
    assert "physical_pdf_page" in data["top_chunks"][0]
    assert "synthesized_by" in data


def test_explain_endpoint():
    payload = {
        "verdict": "WRONG_CONTEXT",
        "scheme_id": "PMFBY",
        "candidate_claim": "Farmers pay 5% premium for food grains.",
        "rationale": "Claimed 5% applies to commercial/horticultural crops, not food grains.",
        "context_mismatch": ["crop_category: food_grains != commercial_crops"],
        "condition_checks": [
            {"name": "Numerical Agreement", "status": "PASSED", "detail": "Value 5% exists in guidelines"},
            {"name": "Crop Category", "status": "FAILED", "detail": "Mismatch: food grains vs commercial"}
        ]
    }
    response = client.post("/api/explain", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "explanation" in data
    assert len(data["explanation"]) > 20
    assert "model" in data


def test_benchmark_stats_endpoint():
    response = client.get("/api/benchmark-stats")
    assert response.status_code == 200
    data = response.json()
    assert "pmfby" in data
    assert "pm_kisan" in data
    assert data["pmfby"]["accuracy"] == 0.9405
    assert data["pmfby"]["false_support_rate"] == 0.0263


def test_certificate_endpoint():
    verify_payload = {
        "scheme_id": "PMFBY",
        "question": "What is the maximum premium rate payable by a farmer for Kharif food grains?",
        "candidate_claim": "Farmers pay a maximum premium of 2.0% for Kharif food grain and oilseed crops.",
        "retrieval_method": "hybrid",
        "top_k": 5
    }
    v_res = client.post("/api/verify", json=verify_payload)
    assert v_res.status_code == 200
    v_data = v_res.json()

    cert_res = client.post("/api/certificate", json={"verification_data": v_data})
    assert cert_res.status_code == 200
    cert = cert_res.json()
    assert cert["authenticity_status"] == "VERIFIED_OFFICIAL_RECORD"
    assert "provenance_hash_sha256" in cert
    assert len(cert["provenance_hash_sha256"]) == 64
    assert cert["verdict"] == v_data["verdict"]


def test_upload_and_verify_custom_document():
    sample_text = (
        "Women receive 50 percent assistance.\n\n"
        "Men receive 40 percent assistance.\n"
    )
    file_bytes = io.BytesIO(sample_text.encode("utf-8"))
    upload_res = client.post(
        "/api/upload",
        files={"file": ("gender_assistance_scheme.txt", file_bytes, "text/plain")}
    )
    assert upload_res.status_code == 200
    up_data = upload_res.json()
    assert "session_id" in up_data
    session_id = up_data["session_id"]
    assert session_id is not None
    assert up_data["units_count"] > 0
    assert up_data["rules_count"] > 0

    # Test Q&A on uploaded document
    qa_res = client.post(
        "/api/qa",
        json={"scheme_id": "UPLOADED", "question": "What is the assistance for women?", "session_id": session_id, "top_k": 3}
    )
    assert qa_res.status_code == 200
    qa_data = qa_res.json()
    assert len(qa_data["answer"]) > 0

    # Test Claim Verification on uploaded document
    v_res = client.post(
        "/api/verify",
        json={
            "scheme_id": "UPLOADED",
            "candidate_claim": "Women receive 50 percent assistance.",
            "session_id": session_id,
            "top_k": 3
        }
    )
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data["verdict"] == "SUPPORTED"


def test_static_index_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert "FieldGuard" in html
    assert "Verification Studio" in html
    assert "Policy Q&A" in html
    assert "Evaluation Benchmark" in html
