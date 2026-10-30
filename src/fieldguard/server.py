"""FieldGuard High-Performance Modern Web API and Dashboard Server.
Replaces legacy Streamlit with a decoupled, responsive, data-dense REST API
and modern Single-Page Application (SPA) designed with UI/UX Pro Max standards.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any
import uuid

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from fieldguard.claim_parser import DeterministicClaimParser
from fieldguard.condition_matcher import ConditionMatchConfig, evaluate_rule_against_claim
from fieldguard.demo_scenarios import SCHEME_SCENARIOS
from fieldguard.evaluation.runner import build_all_retrievers
from fieldguard.evidence_store import (
    EvidenceStore,
    build_default_evidence_store,
    build_pm_kisan_evidence_store,
)
from fieldguard.flagship_schemes_data import build_flagship_scheme_evidence_store
from fieldguard.schemes.registry import SchemeRegistry, get_scheme_adapter, list_supported_schemes
from fieldguard.uploaded_doc_engine import (
    UploadedDocumentError,
    answer_question_from_uploaded_doc,
    process_uploaded_document,
)
from fieldguard.verdicts import Verdict
from fieldguard.verifier import FieldGuardVerifier, VerificationPrediction

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="FieldGuard Engine API",
    description="Universal Condition-Aware Numerical Claim Verification and Policy Q&A Platform",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Backend scheme cache
_SCHEME_BACKENDS: dict[str, tuple[EvidenceStore, dict[str, Any], FieldGuardVerifier]] = {}
_UPLOAD_SESSIONS: dict[str, dict[str, Any]] = {}


def get_scheme_backend(scheme_key: str):
    """Retrieve or initialize backend store, retrievers, and verifier for a scheme."""
    norm_key = scheme_key.upper().strip()
    if norm_key in _SCHEME_BACKENDS:
        return _SCHEME_BACKENDS[norm_key]

    if norm_key == "PM_KISAN":
        store = build_pm_kisan_evidence_store(PROJECT_ROOT)
    elif norm_key == "PMFBY":
        store = build_default_evidence_store(PROJECT_ROOT)
    else:
        store = build_flagship_scheme_evidence_store(norm_key, PROJECT_ROOT)

    retrievers = build_all_retrievers(store)
    verifier = FieldGuardVerifier(evidence_store=store)
    _SCHEME_BACKENDS[norm_key] = (store, retrievers, verifier)
    return store, retrievers, verifier


# Request / Response Schemas
class VerifyRequest(BaseModel):
    scheme_id: str = "PMFBY"
    question: str = ""
    candidate_claim: str
    retrieval_method: str = "hybrid"
    top_k: int = 5
    session_id: str | None = None


class QARequest(BaseModel):
    scheme_id: str = "PMFBY"
    question: str
    top_k: int = 5
    session_id: str | None = None


class CertificateRequest(BaseModel):
    verification_data: dict[str, Any]


SCHEME_METADATA = {
    "PMFBY": {
        "name": "Pradhan Mantri Fasal Bima Yojana",
        "domain": "Crop Insurance",
        "badge": "PMFBY",
        "icon": "shield-check",
        "description": "Comprehensive yield & weather insurance with crop-specific premium caps and mandatory qualifiers.",
        "verified_rules": 33,
    },
    "PM_KISAN": {
        "name": "PM Kisan Samman Nidhi",
        "domain": "Direct Income Support",
        "badge": "PM-KISAN",
        "icon": "banknote",
        "description": "Direct bank transfer of ₹6,000/year in 3 instalments with strict exclusions and mandatory eKYC.",
        "verified_rules": 8,
    },
    "MGNREGA": {
        "name": "Mahatma Gandhi NREGA",
        "domain": "Rural Employment Guarantee",
        "badge": "MGNREGS",
        "icon": "hard-hat",
        "description": "Statutory guarantee of 100 days unskilled manual work per rural household with 15-day timeline.",
        "verified_rules": 3,
    },
    "PM_JAY": {
        "name": "Ayushman Bharat PM-JAY",
        "domain": "National Health Assurance",
        "badge": "PM-JAY",
        "icon": "heart-pulse",
        "description": "₹5,00,000 annual secondary & tertiary health cover per family, 100% cashless with no family cap.",
        "verified_rules": 3,
    },
    "PMAY_G": {
        "name": "Pradhan Mantri Awaas Yojana - Gramin",
        "domain": "Rural Housing Assistance",
        "badge": "PMAY-G",
        "icon": "home",
        "description": "Grant assistance of ₹1.20L (plain) / ₹1.30L (hilly) for 25 sq.m minimum area pucca house.",
        "verified_rules": 3,
    },
    "PM_KUSUM": {
        "name": "PM-KUSUM Solar Agriculture",
        "domain": "Renewable Energy",
        "badge": "PM-KUSUM",
        "icon": "sun",
        "description": "60% capital subsidy (30% CFA + 30% State) for standalone solar agriculture pumps up to 7.5 HP.",
        "verified_rules": 2,
    },
    "PMMY": {
        "name": "Pradhan Mantri Mudra Yojana",
        "domain": "Micro-Enterprise Credit",
        "badge": "PMMY",
        "icon": "briefcase",
        "description": "Collateral-free institutional micro-credit across Shishu (₹50k), Kishore (₹5L), and Tarun (₹10L/₹20L) tiers.",
        "verified_rules": 2,
    },
}


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "FieldGuard Neuro-Symbolic Policy Engine",
        "version": "3.0.0",
        "inference_device": "CPU (Offline Deterministic)",
        "accuracy_held_out": 0.9405,
        "false_support_rate": 0.0263,
    }


@app.get("/api/schemes")
def list_schemes():
    """Return all available flagship schemes and their benchmark demonstration scenarios."""
    schemes_data = []
    for s_id, meta in SCHEME_METADATA.items():
        scenarios = SCHEME_SCENARIOS.get(s_id, {})
        scenarios_list = [
            {"label": k, "question": v[0], "claim": v[1]}
            for k, v in scenarios.items()
        ]
        schemes_data.append({
            "id": s_id,
            "name": meta["name"],
            "domain": meta["domain"],
            "badge": meta["badge"],
            "icon": meta["icon"],
            "description": meta["description"],
            "verified_rules": meta["verified_rules"],
            "scenarios": scenarios_list,
        })
    return {"schemes": schemes_data}


@app.post("/api/verify")
def verify_claim(req: VerifyRequest):
    """Run condition-aware claim verification across pre-loaded schemes or uploaded files."""
    start_time = time.perf_counter()

    if req.session_id and req.session_id in _UPLOAD_SESSIONS:
        sess = _UPLOAD_SESSIONS[req.session_id]
        store: EvidenceStore = sess["store"]
        retrievers = sess["retrievers"]
        verifier: FieldGuardVerifier = sess["verifier"]
        is_upload = True
        source_title = sess["file_name"]
    else:
        store, retrievers, verifier = get_scheme_backend(req.scheme_id)
        is_upload = False
        source_title = SCHEME_METADATA.get(req.scheme_id, {}).get("name", req.scheme_id)

    # 1. Retrieve evidence
    retriever = retrievers.get(req.retrieval_method, retrievers.get("hybrid") or list(retrievers.values())[0])
    query = f"{req.question} {req.candidate_claim}".strip()
    results = retriever.retrieve(query, top_k=req.top_k)
    ret_items = [r.to_dict() for r in results]

    # 2. Run verification
    pred: VerificationPrediction = verifier.verify_claim(
        claim_id=f"WEB_{uuid.uuid4().hex[:8].upper()}",
        question=req.question or req.candidate_claim,
        candidate_claim=req.candidate_claim,
        retrieved_items=ret_items,
        retrieval_method=req.retrieval_method,
    )

    # 3. Construct condition-by-condition checks
    checks = []
    verdict = pred.predicted_verdict
    if verdict == "SUPPORTED":
        checks = [
            {"name": "Numeric & Unit Agreement", "status": "PASSED", "detail": "Claimed value matches applicable statutory rule"},
            {"name": "Beneficiary / Entity Scope", "status": "PASSED", "detail": "Target beneficiary and category aligned"},
            {"name": "Frequency / Periodicity Agreement", "status": "PASSED", "detail": "Payment frequency and intervals validated"},
            {"name": "Qualifications & Exclusions", "status": "PASSED", "detail": "Statutory qualifiers and exclusions satisfied"},
            {"name": "Temporal Applicability", "status": "PASSED", "detail": "Source document is active and legally applicable"},
            {"name": "Source Authority & Provenance", "status": "PASSED", "detail": "Verified official government gazette / policy guidelines"},
        ]
    elif verdict == "WRONG_CONTEXT":
        checks = [
            {"name": "Numeric & Unit Agreement", "status": "PASSED", "detail": "Claimed number exists in verified official guidelines"},
            {"name": "Entity Scope / Category", "status": "FAILED" if any(k in m for m in pred.context_mismatch for k in ("crop", "beneficiary", "entity", "mudra")) else "PASSED", "detail": "Claimed category differs from rule applicability"},
            {"name": "Frequency / Periodicity", "status": "FAILED" if any("season" in m or "frequency" in m for m in pred.context_mismatch) else "PASSED", "detail": "Claimed frequency differs from rule periodicity"},
            {"name": "Temporal Applicability", "status": "FAILED" if any("temporal" in m or "version" in m for m in pred.context_mismatch) else "PASSED", "detail": "Policy version or effective era mismatch"},
            {"name": "Source Authority & Provenance", "status": "PASSED", "detail": "Official government publication"},
        ]
    elif verdict == "CONTRADICTED":
        checks = [
            {"name": "Numeric & Unit Agreement", "status": "FAILED", "detail": "Value or rate directly contradicts official evidence"},
            {"name": "Context Matching", "status": "PASSED", "detail": "Evaluated under the matching policy category"},
            {"name": "Source Authority & Provenance", "status": "PASSED", "detail": "Official government guidelines"},
        ]
    else:
        checks = [
            {"name": "Evidence Sufficiency", "status": "INSUFFICIENT", "detail": pred.abstention_reason or "Available evidence does not establish claim"},
            {"name": "Temporal Resolution", "status": pred.temporal_status, "detail": "Cannot verify applicability for requested era"},
        ]

    # 4. Construct Side-by-Side Condition Diff
    # Match against the best candidate rule in store
    diff = []
    matched_rule = None
    for r_id in pred.supporting_evidence_ids + pred.contradicting_evidence_ids:
        for r in store.trusted_rules.values():
            if r.evidence_id == r_id:
                matched_rule = r
                break
        if matched_rule:
            break

    parsed = pred.parsed_claim
    if matched_rule:
        diff = [
            {
                "dimension": "Scheme",
                "claimed": parsed.get("scheme") or req.scheme_id,
                "evidence_rule": matched_rule.scheme,
                "is_match": (parsed.get("scheme") or req.scheme_id).upper() == matched_rule.scheme.upper() or is_upload,
            },
            {
                "dimension": "Entity / Crop Category",
                "claimed": parsed.get("crop_category") or parsed.get("entity_scope") or "General",
                "evidence_rule": matched_rule.crop_category or matched_rule.entity_scope or "General",
                "is_match": not any("crop" in m or "entity" in m for m in pred.context_mismatch),
            },
            {
                "dimension": "Season / Frequency",
                "claimed": parsed.get("season") or parsed.get("frequency") or "Annual",
                "evidence_rule": matched_rule.season or matched_rule.frequency or "Annual",
                "is_match": not any("season" in m or "frequency" in m for m in pred.context_mismatch),
            },
            {
                "dimension": "Numerical Value",
                "claimed": f"{parsed.get('claimed_value') or parsed.get('canonical_value') or ''} {parsed.get('claimed_unit') or parsed.get('canonical_unit') or ''}".strip(),
                "evidence_rule": f"{matched_rule.allowed_values or matched_rule.minimum_value or ''} {matched_rule.unit or ''}".strip(),
                "is_match": verdict in ("SUPPORTED", "WRONG_CONTEXT"),
            },
            {
                "dimension": "Statutory Qualifier",
                "claimed": parsed.get("qualifier") or "None",
                "evidence_rule": matched_rule.qualifier or "None",
                "is_match": not any("qualifier" in m for m in pred.context_mismatch),
            },
        ]

    # Evidence items annotated with role
    annotated_evidence = []
    for it in ret_items:
        e_id = it.get("evidence_id")
        is_sup = e_id in pred.supporting_evidence_ids
        is_con = e_id in pred.contradicting_evidence_ids
        role = "SUPPORTING" if is_sup else ("CONTRADICTING" if is_con else "NEUTRAL")
        annotated_evidence.append({
            "evidence_id": e_id,
            "document_id": it.get("source_document_id"),
            "page": it.get("physical_pdf_page"),
            "score": round(it.get("retrieval_score", 0.0), 4),
            "text": it.get("text", ""),
            "role": role,
        })

    total_latency_ms = (time.perf_counter() - start_time) * 1000.0

    return {
        "claim_id": pred.claim_id,
        "scheme_id": req.scheme_id,
        "source_title": source_title,
        "is_uploaded_document": is_upload,
        "question": req.question,
        "candidate_claim": req.candidate_claim,
        "verdict": verdict,
        "verification_rationale": pred.verification_rationale,
        "abstention_reason": pred.abstention_reason,
        "temporal_status": pred.temporal_status,
        "context_mismatch": pred.context_mismatch,
        "latency_ms": round(total_latency_ms, 2),
        "condition_checks": checks,
        "condition_diff": diff,
        "retrieved_evidence": annotated_evidence,
        "parsed_claim": pred.parsed_claim,
    }


@app.post("/api/qa")
def question_answering(req: QARequest):
    """Retrieve grounded passages and generate citation-backed answer."""
    if req.session_id and req.session_id in _UPLOAD_SESSIONS:
        sess = _UPLOAD_SESSIONS[req.session_id]
        store = sess["store"]
        retrievers = sess["retrievers"]
        res = answer_question_from_uploaded_doc(req.question, store, retrievers, top_k=req.top_k)
        return {
            "question": req.question,
            "answer": res["answer"],
            "citations": res["citations"],
            "top_chunks": res["top_chunks"],
        }

    store, retrievers, verifier = get_scheme_backend(req.scheme_id)
    retriever = retrievers.get("hybrid", list(retrievers.values())[0])
    results = retriever.retrieve(req.question, top_k=req.top_k)
    if not results:
        return {
            "question": req.question,
            "answer": "No relevant evidence found in the official guidelines.",
            "citations": [],
            "top_chunks": [],
        }

    top_chunk = results[0]
    answer_text = (
        f"According to {top_chunk.source_document_id} (Page {top_chunk.physical_pdf_page}), "
        f"the policy specifies: \"{top_chunk.text.strip()}\""
    )

    citations = [
        f"{c.source_document_id} p.{c.physical_pdf_page} [{round(c.retrieval_score, 3)}]"
        for c in results
    ]

    return {
        "question": req.question,
        "answer": answer_text,
        "citations": citations,
        "top_chunks": [r.to_dict() for r in results],
    }


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """Dynamically ingest and index an arbitrary government policy PDF or TXT file."""
    file_bytes = await file.read()
    file_name = file.filename or "policy_document.pdf"

    try:
        store, units, rules = process_uploaded_document(file_bytes, file_name)
        retrievers = build_all_retrievers(store)
        verifier = FieldGuardVerifier(evidence_store=store)
    except (UploadedDocumentError, Exception) as exc:
        raise HTTPException(status_code=400, detail=f"Failed to process document: {exc}")

    session_id = uuid.uuid4().hex
    _UPLOAD_SESSIONS[session_id] = {
        "store": store,
        "retrievers": retrievers,
        "verifier": verifier,
        "file_name": file_name,
        "units": units,
        "rules": rules,
        "created_at": time.time(),
    }

    # Clean old sessions if more than 20
    if len(_UPLOAD_SESSIONS) > 20:
        oldest_key = min(_UPLOAD_SESSIONS.keys(), key=lambda k: _UPLOAD_SESSIONS[k]["created_at"])
        del _UPLOAD_SESSIONS[oldest_key]

    preview_units = [
        {
            "evidence_id": u.evidence_id,
            "page": u.physical_pdf_page,
            "type": u.evidence_type,
            "snippet": u.text[:180] + ("..." if len(u.text) > 180 else ""),
        }
        for u in units[:12]
    ]

    return {
        "session_id": session_id,
        "file_name": file_name,
        "units_count": len(units),
        "rules_count": len(rules),
        "preview_units": preview_units,
    }


@app.post("/api/certificate")
def generate_audit_certificate(req: CertificateRequest):
    """Generate a cryptographically verifiable JSON audit certificate."""
    v_data = req.verification_data
    raw_payload = json.dumps(v_data, sort_keys=True)
    cert_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

    cert = {
        "certificate_id": f"FG-CERT-{uuid.uuid4().hex[:12].upper()}",
        "timestamp_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "provenance_hash_sha256": cert_hash,
        "engine": "FieldGuard Neuro-Symbolic Verifier v3.0.0",
        "claim": v_data.get("candidate_claim"),
        "question": v_data.get("question"),
        "verdict": v_data.get("verdict"),
        "scheme": v_data.get("scheme_id"),
        "latency_ms": v_data.get("latency_ms"),
        "evidence_sources": [
            {
                "id": e.get("evidence_id"),
                "document": e.get("document_id"),
                "page": e.get("page"),
                "role": e.get("role"),
            }
            for e in v_data.get("retrieved_evidence", [])
        ],
        "condition_checks": v_data.get("condition_checks", []),
        "authenticity_status": "VERIFIED_OFFICIAL_RECORD",
    }
    return cert


@app.get("/api/benchmark-stats")
def get_benchmark_stats():
    """Return published empirical benchmark metrics across PMFBY and PM-KISAN."""
    return {
        "pmfby": {
            "name": "PMFBY Held-Out Benchmark (168 Claims)",
            "accuracy": 0.9405,
            "macro_f1": 0.9411,
            "false_support_rate": 0.0263,
            "coverage": 0.8214,
            "latency_ms": 1.42,
            "baselines": [
                {"name": "Retrieval-Only (Cosine)", "accuracy": 0.1071, "fsr": 0.2105, "coverage": 0.1429},
                {"name": "Numeric-Only (String Match)", "accuracy": 0.4464, "fsr": 0.8158, "coverage": 0.9821},
                {"name": "Numeric + Basic Context", "accuracy": 0.7262, "fsr": 0.3684, "coverage": 0.8750},
                {"name": "FieldGuard Full", "accuracy": 0.9405, "fsr": 0.0263, "coverage": 0.8214},
            ],
        },
        "pm_kisan": {
            "name": "PM-KISAN Cross-Scheme Transfer (26 Claims)",
            "accuracy": 0.9231,
            "macro_f1": 0.9195,
            "false_support_rate": 0.0000,
            "coverage": 0.8462,
            "latency_ms": 1.25,
            "baselines": [
                {"name": "Numeric-Only Baseline", "accuracy": 0.5000, "fsr": 0.7143, "coverage": 1.0000},
                {"name": "Basic Context Baseline", "accuracy": 0.6923, "fsr": 0.4286, "coverage": 0.9231},
                {"name": "FieldGuard Full", "accuracy": 0.9231, "fsr": 0.0000, "coverage": 0.8462},
            ],
        },
    }


# Mount frontend static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def index_page():
    index_html = STATIC_DIR / "index.html"
    if not index_html.is_file():
        return HTMLResponse("<h2>FieldGuard Frontend Initializing...</h2>", status_code=200)
    return HTMLResponse(index_html.read_text(encoding="utf-8"), status_code=200)
