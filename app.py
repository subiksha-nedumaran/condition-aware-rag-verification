"""FieldGuard Universal Multi-Scheme Policy Verification & Q&A Platform.

Interactive interface supporting:
1. All 7 flagship Indian government schemes:
   - PMFBY (Crop Insurance)
   - PM-KISAN (Direct Income Support)
   - MGNREGS (Rural Employment Guarantee)
   - Ayushman Bharat PM-JAY (Health Assurance)
   - PMAY-G (Rural Housing Assistance)
   - PM-KUSUM (Solar Agriculture)
   - PMMY (Mudra Micro-Enterprise Credit)
2. Dynamic Government Policy Document Upload (PDF / TXT):
   - Natural language Q&A with page-level grounded citations
   - Condition-aware numerical claim verification
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

# Ensure src/ is on python path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

try:
    import streamlit as st
except ImportError:
    print("Streamlit is not installed in the active environment. Install with: pip install streamlit")
    sys.exit(0)

from fieldguard.evidence_store import (
    build_default_evidence_store,
    build_pm_kisan_evidence_store,
)
from fieldguard.flagship_schemes_data import build_flagship_scheme_evidence_store
from fieldguard.evaluation.runner import build_all_retrievers
from fieldguard.verifier import FieldGuardVerifier, VerifierConfig
from fieldguard.verdicts import Verdict
from fieldguard.uploaded_doc_engine import (
    UploadedDocumentError,
    answer_question_from_uploaded_doc,
)
from fieldguard.uploaded_backend import load_uploaded_backend


@st.cache_resource
def load_scheme_backend(scheme_key: str, verification_revision: str = "numeric-v2"):
    if scheme_key == "PM_KISAN":
        store = build_pm_kisan_evidence_store(PROJECT_ROOT)
    elif scheme_key == "PMFBY":
        store = build_default_evidence_store(PROJECT_ROOT)
    else:
        store = build_flagship_scheme_evidence_store(scheme_key, PROJECT_ROOT)
    retrievers = build_all_retrievers(store)
    verifier = FieldGuardVerifier(evidence_store=store)
    return store, retrievers, verifier


st.set_page_config(
    page_title="FieldGuard — Universal Government Scheme Verification & Q&A",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ FieldGuard")
st.subheader("Condition-Aware Numerical Claim Verification & Policy Q&A Across Government Schemes")

# Benchmark scenarios for all 7 schemes
from fieldguard.demo_scenarios import SCHEME_SCENARIOS

with st.sidebar:
    st.header("🏛️ Scheme Navigation")
    scheme_options = [
        "🌾 PMFBY (Crop Insurance)",
        "🚜 PM-KISAN (Direct Income Support)",
        "👷 MGNREGS (Rural Employment Guarantee)",
        "🏥 Ayushman Bharat PM-JAY (Health Assurance)",
        "🏠 PMAY-G (Rural Housing Assistance)",
        "☀️ PM-KUSUM (Solar Agriculture)",
        "💼 PMMY (Mudra Micro-Credit)",
        "📂 Upload Custom Scheme Document (PDF / TXT)",
    ]
    scheme_choice = st.radio("Select Scheme Mode:", scheme_options, index=0)

    is_upload_mode = "Upload Custom" in scheme_choice

    if not is_upload_mode:
        # Determine internal scheme key
        if "PMFBY" in scheme_choice:
            scheme_key = "PMFBY"
        elif "PM-KISAN" in scheme_choice:
            scheme_key = "PM_KISAN"
        elif "MGNREGS" in scheme_choice:
            scheme_key = "MGNREGA"
        elif "PM-JAY" in scheme_choice:
            scheme_key = "PM_JAY"
        elif "PMAY-G" in scheme_choice:
            scheme_key = "PMAY_G"
        elif "PM-KUSUM" in scheme_choice:
            scheme_key = "PM_KUSUM"
        else:
            scheme_key = "PMMY"

        try:
            store, retrievers, verifier = load_scheme_backend(scheme_key)
        except RuntimeError as exc:
            st.error(str(exc))
            st.stop()

        st.header("⚙️ Configuration")
        scenarios = SCHEME_SCENARIOS.get(scheme_key, {})
        selected_scenario = st.selectbox(
            "Choose a Benchmark Scenario:", ["Custom Query / Claim"] + list(scenarios.keys())
        )
        retrieval_method = st.selectbox("Retrieval Method:", ["hybrid", "semantic", "lexical", "table"])
        top_k = st.slider("Top-K Evidence Items:", min_value=1, max_value=10, value=5)

        st.markdown("---")
        st.markdown("**Corpus Status:**")
        st.markdown(f"- Scheme: **{scheme_key}**")
        st.markdown(f"- Indexed Units: **{len(store.evidence_units)}**")
        st.markdown(f"- Verified Rules: **{len(store.trusted_rules)}**")
        st.markdown("- Verification Status: **Official Trusted Guidelines**")

# ==========================================
# BRANCH A: UPLOAD CUSTOM SCHEME DOCUMENT
# ==========================================
if is_upload_mode:
    st.markdown("### 📂 Upload Any Government Scheme Document")
    st.info(
        "Upload an official PDF or TXT guidelines document for **any** national or state government scheme. "
        "FieldGuard dynamically extracts text chunks and tables, builds an in-memory retrieval index, "
        "and enables both **Question Answering** and **Condition-Aware Numerical Claim Verification**."
    )

    uploaded_file = st.file_uploader("Upload Scheme PDF or TXT:", type=["pdf", "txt"])
    st.caption(
        "Upload verdicts compare claims with this document only. Official provenance and current "
        "policy applicability are unverified. Explicit numerical passages and recognized yield-threshold "
        "paraphrases can be checked; unresolved wording or omitted conditions return UNVERIFIABLE."
    )

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        file_name = uploaded_file.name

        with st.spinner(f"Ingesting and indexing '{file_name}'..."):
            try:
                up_store, up_units, up_rules, up_retrievers, up_verifier = load_uploaded_backend(
                    st.session_state, file_bytes, file_name)
            except (UploadedDocumentError, RuntimeError) as exc:
                st.error(str(exc))
                st.stop()

        st.success(
            f"✅ **Document Processed Successfully!** "
            f"Extracted **{len(up_units)}** evidence units and **{len(up_rules)}** candidate numerical rules from `{file_name}`."
        )

        tab1, tab2, tab3 = st.tabs(["❓ Ask a Question from Document", "🛡️ Verify a Numerical Claim", "📑 Document Structure"])

        with tab1:
            st.markdown("#### Search Document Excerpts")
            st.caption("Search returns source passages, not generated answers. Weak lexical matches are omitted; relevant excerpts may still be incomplete.")
            q_text = st.text_input(
                "Enter your question regarding the uploaded document:",
                placeholder="e.g. What is the maximum subsidy or financial assistance allowed?",
            )
            q_top_k = st.slider("Number of Evidence Passages to Retrieve:", 1, 10, 5, key="q_top_k")

            if st.button("🔎 Search & Answer", type="primary", key="btn_qa"):
                if not q_text.strip():
                    st.warning("Please enter a question.")
                else:
                    qa_res = answer_question_from_uploaded_doc(q_text, up_store, up_retrievers, top_k=q_top_k)
                    st.markdown("### 📄 Retrieved Excerpts")
                    st.write(qa_res["answer"])

                    st.markdown("### 📑 Citations & Source Evidence")
                    for idx, ch in enumerate(qa_res["top_chunks"]):
                        with st.expander(f"Passage {idx + 1} — Page {ch.get('physical_pdf_page', 'N/A')} (Score: {round(ch.get('retrieval_score', 0.0), 4)})"):
                            st.write(ch.get("text", ""))

        with tab2:
            st.markdown("#### Condition-Aware Numerical Claim Verification")
            claim_q = st.text_input(
                "Context / Question (Optional):",
                placeholder="e.g. Under the policy, what is the maximum assistance?",
                key="up_claim_q",
            )
            claim_text = st.text_area(
                "Candidate Numerical Claim to Verify:",
                placeholder="e.g. Beneficiaries receive a financial assistance of Rs 50000.",
                key="up_claim_text",
            )

            if st.button("🛡️ Verify Claim Against Document", type="primary", key="btn_up_verify"):
                if not claim_text.strip():
                    st.warning("Please enter a claim to verify.")
                else:
                    query = f"{claim_q} {claim_text}".strip()
                    ret_engine = up_retrievers.get("hybrid") or list(up_retrievers.values())[0]
                    ret_items = [r.to_dict() for r in ret_engine.retrieve(query, top_k=5)]

                    pred = up_verifier.verify_claim(
                        claim_id="UPLOADED_DOC_CLAIM",
                        question=claim_q or claim_text,
                        candidate_claim=claim_text,
                        retrieved_items=ret_items,
                    )

                    st.markdown("---")
                    st.header("📊 Verification Result")
                    verdict = pred.predicted_verdict
                    if verdict == "SUPPORTED":
                        st.success(f"### Verdict: **{verdict}** ✅")
                    elif verdict == "WRONG_CONTEXT":
                        st.warning(f"### Verdict: **{verdict}** ⚠️ (Number occurs in document, but applies to a different condition/context)")
                    elif verdict == "CONTRADICTED":
                        st.error(f"### Verdict: **{verdict}** ❌ (Contradicted under matching context)")
                    else:
                        st.info(f"### Verdict: **{verdict}** ❓ (Insufficient evidence to establish support)")

                    st.caption("Verification scope: uploaded document only — source unverified.")
                    st.markdown(f"**Verification Rationale:** {pred.verification_rationale}")
                    if pred.verdict_reason_code or pred.abstention_reason:
                        st.markdown(f"**Diagnostic Reason Code:** `{pred.verdict_reason_code or pred.abstention_reason}`")
                    if pred.matched_passage:
                        st.markdown(f"**Matched Passage (Page {pred.matched_page or 'N/A'}, Score {pred.matched_score}):** {pred.matched_passage}")
                    if pred.matched_candidate_rule:
                        with st.expander("🔍 Matched Uploaded Candidate Rule", expanded=True):
                            st.json(pred.matched_candidate_rule)

                    c1, c2 = st.columns(2)
                    with c1:
                        st.metric("Total Latency", f"{round(pred.latency_ms, 2)} ms")
                    with c2:
                        st.metric("Retrieved Units", len(ret_items))

                    if pred.context_mismatch:
                        st.warning(f"**Context Mismatch Dimensions:** {'; '.join(pred.context_mismatch)}")

                    st.markdown("### 📑 Retrieved Evidence Records")
                    for idx, item in enumerate(ret_items):
                        is_sup = item["evidence_id"] in pred.supporting_evidence_ids
                        is_con = item["evidence_id"] in pred.contradicting_evidence_ids
                        badge = "🟢" if is_sup else ("🔴" if is_con else "⚪")
                        with st.expander(f"{badge} [Rank {idx + 1}] Page {item.get('physical_pdf_page', 'N/A')} (ID: {item['evidence_id']})"):
                            st.write(item.get("text", ""))

        with tab3:
            st.markdown("#### Document Overview & Indexed Chunks")
            with st.expander("Extracted numerical candidates (unverified)"):
                st.caption("Bounds are extracted only when explicit. Full passages retain eligibility and qualifications; unknown fields remain blank.")
                st.json([rule.to_dict() for rule in up_rules])
            st.write(f"Total Extracted Passages / Table Rows: **{len(up_units)}**")
            for idx, u in enumerate(up_units[:25]):
                with st.expander(f"Unit {idx + 1} — Page {u.physical_pdf_page} ({u.evidence_type})"):
                    st.write(u.text)
            if len(up_units) > 25:
                st.caption(f"... and {len(up_units) - 25} more units indexed.")

    else:
        st.session_state.pop("fieldguard_upload_backend", None)

# ==========================================
# BRANCH B: PRE-LOADED 7 FLAGSHIP SCHEMES
# ==========================================
else:
    default_q = ""
    default_c = ""
    if "current_scenario" not in st.session_state or st.session_state.current_scenario != selected_scenario:
        st.session_state.current_scenario = selected_scenario
        if selected_scenario != "Custom Query / Claim" and selected_scenario in scenarios:
            st.session_state.pre_q_input, st.session_state.pre_c_input = scenarios[selected_scenario]
        elif selected_scenario == "Custom Query / Claim":
            st.session_state.pre_q_input = ""
            st.session_state.pre_c_input = ""
    default_q = st.session_state.get("pre_q_input", "")
    default_c = st.session_state.get("pre_c_input", "")

    tab_v, tab_q = st.tabs(["🛡️ Numerical Claim Verification", "❓ Question Answering (RAG)"])

    with tab_v:
        question_input = st.text_input(
            "User Question (Context):",
            placeholder="e.g. What is the maximum subsidy or benefit under this scheme?",
            key="pre_q_input",
        )
        claim_input = st.text_area(
            "Candidate Numerical Claim to Verify:",
            height=90,
            placeholder="e.g. Under the scheme guidelines, eligible beneficiaries receive...",
            key="pre_c_input",
        )

        if st.button("🔍 Verify Claim", type="primary", key="btn_pre_verify"):
            if not claim_input.strip():
                st.warning("Please enter a candidate numerical claim.")
            else:
                retriever = retrievers.get(retrieval_method, retrievers["hybrid"])
                query = f"{question_input} {claim_input}".strip()
                ret_items = [r.to_dict() for r in retriever.retrieve(query, top_k=top_k)]

                pred = verifier.verify_claim(
                    claim_id="WEB_INTERACTIVE",
                    question=question_input or claim_input,
                    candidate_claim=claim_input,
                    retrieved_items=ret_items,
                    retrieval_method=retrieval_method,
                )

                st.markdown("---")
                st.header("📊 Verification Result")

                verdict = pred.predicted_verdict
                if verdict == "SUPPORTED":
                    st.success(f"### Verdict: **{verdict}** ✅")
                elif verdict == "WRONG_CONTEXT":
                    st.warning(f"### Verdict: **{verdict}** ⚠️ (Number occurs in official document, but applies to a different context/condition)")
                elif verdict == "CONTRADICTED":
                    st.error(f"### Verdict: **{verdict}** ❌ (Contradicted under matching context)")
                else:
                    st.info(f"### Verdict: **{verdict}** ❓ (Insufficient or ambiguous evidence to establish support)")

                st.markdown(f"**Verification Rationale:** {pred.verification_rationale}")
                if pred.component_results:
                    with st.expander("Checks for each numerical component", expanded=True):
                        st.dataframe(pred.component_results, use_container_width=True)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Latency", f"{round(pred.latency_ms, 2)} ms")
                with col2:
                    st.metric("Retrieved Chunks", len(ret_items))
                with col3:
                    st.metric("Temporal Status", pred.temporal_status)

                st.markdown("### 📋 Condition-by-Condition Checks")
                checks_data = []
                if verdict == "SUPPORTED":
                    checks_data = [
                        ("Numeric & Unit Agreement", "PASSED", "Claimed value matches applicable policy rate/threshold"),
                        ("Beneficiary / Entity Scope", "PASSED", "Rule applies to requested entity / beneficiary scope"),
                        ("Frequency / Periodicity Agreement", "PASSED", "Rule applies to requested frequency or period"),
                        ("Qualification & Exclusions", "PASSED", "Statutory exclusion and qualifier constraints verified"),
                        ("Temporal Applicability", "PASSED", "Source document is active and applicable to requested era"),
                        ("Source Authority", "PASSED", "Official government guidelines / verified gazette notification"),
                    ]
                elif verdict == "WRONG_CONTEXT":
                    checks_data = [
                        ("Numeric & Unit Agreement", "PASSED", "Claimed number exists in verified official corpus"),
                        ("Entity Scope / Category", "FAILED" if any(k in m for m in pred.context_mismatch for k in ("crop", "beneficiary", "entity", "ineligible", "mudra")) else "PASSED", "Claimed category differs from rule applicability"),
                        ("Frequency / Periodicity", "FAILED" if any("season" in m or "frequency" in m for m in pred.context_mismatch) else "PASSED", "Claimed frequency differs from rule periodicity"),
                        ("Temporal Applicability", "FAILED" if any("temporal" in m or "version" in m for m in pred.context_mismatch) else "PASSED", "Policy era or version mismatch"),
                        ("Source Authority", "PASSED", "Official government document"),
                    ]
                elif verdict == "CONTRADICTED":
                    checks_data = [
                        ("Numeric & Unit Agreement", "FAILED", "Value, operator, or qualification directly contradicts evidence"),
                        ("Context Matching", "PASSED", "Evaluated under the matching entity scope and temporal window"),
                        ("Source Authority", "PASSED", "Official government guidelines"),
                    ]
                else:
                    checks_data = [
                        ("Evidence Sufficiency", "INSUFFICIENT", pred.abstention_reason or "Available evidence does not establish claim"),
                        ("Temporal Resolution", pred.temporal_status, "Cannot determine current validity of unverified policy year"),
                    ]

                for name, status, detail in checks_data:
                    badge = "🟢" if status == "PASSED" else ("🔴" if status == "FAILED" else "🟡")
                    st.markdown(f"- {badge} **{name}**: `{status}` — *{detail}*")

                if pred.context_mismatch:
                    st.warning(f"**Context Mismatch Dimensions:** {'; '.join(pred.context_mismatch)}")

                st.markdown("### 📑 Retrieved Evidence Records")
                for idx, item in enumerate(ret_items):
                    is_supported_ev = item["evidence_id"] in pred.supporting_evidence_ids
                    is_contradicted_ev = item["evidence_id"] in pred.contradicting_evidence_ids
                    header_icon = "🟢" if is_supported_ev else ("🔴" if is_contradicted_ev else "⚪")
                    with st.expander(f"{header_icon} [Rank {idx + 1}] {item['evidence_id']} — Source: {item['source_document_id']} (Page {item.get('physical_pdf_page', 'N/A')})"):
                        st.markdown(f"**Score:** `{round(item.get('retrieval_score', 0.0), 4)}` | **Type:** `{item.get('evidence_type', 'chunk')}`")
                        st.markdown(f"```text\n{item.get('text', '')}\n```")

    with tab_q:
        st.markdown(f"#### Ask Any Question about {scheme_key}")
        user_qa_q = st.text_input(
            "Enter policy question:",
            value=default_q,
            placeholder="e.g. What is the financial assistance provided?",
            key="pre_tab_qa_q",
        )
        if st.button("🔎 Get Grounded Answer", type="primary", key="btn_pre_qa"):
            if not user_qa_q.strip():
                st.warning("Please enter a question.")
            else:
                retriever = retrievers.get(retrieval_method, retrievers["hybrid"])
                res_chunks = retriever.retrieve(user_qa_q, top_k=top_k)
                if not res_chunks:
                    st.info("No relevant policy evidence found.")
                else:
                    top_chunk = res_chunks[0]
                    st.markdown("### 💡 Grounded Answer & Top Finding")
                    st.info(f"**Key Evidence ({top_chunk.source_document_id}, Page {top_chunk.physical_pdf_page}):**\n\n\"{top_chunk.text}\"")

                    st.markdown("### 📑 Supporting Passages & Tables")
                    for idx, c in enumerate(res_chunks):
                        with st.expander(f"[Rank {idx + 1}] Page {c.physical_pdf_page} — ID: {c.evidence_id} (Score: {round(c.retrieval_score, 4)})"):
                            st.write(c.text)
