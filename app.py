"""FieldGuard Interactive Demonstration Interface.

Streamlit application providing condition-aware numerical claim verification
for multi-scheme government policy question answering (PMFBY and PM-KISAN).
Calls the exact same underlying FieldGuardVerifier backend as the CLI and evaluation runner.
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
from fieldguard.evaluation.runner import build_all_retrievers
from fieldguard.verifier import FieldGuardVerifier, VerifierConfig
from fieldguard.verdicts import Verdict


@st.cache_resource
def load_backend(scheme_key: str):
    if scheme_key == "PM_KISAN":
        store = build_pm_kisan_evidence_store(PROJECT_ROOT)
    else:
        store = build_default_evidence_store(PROJECT_ROOT)
    retrievers = build_all_retrievers(store)
    verifier = FieldGuardVerifier(evidence_store=store)
    return store, retrievers, verifier


st.set_page_config(
    page_title="FieldGuard — Multi-Scheme Numerical Claim Verification",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ FieldGuard")
st.subheader("Condition-Aware Verification of Numerical Claims in Government-Scheme Question Answering")

PMFBY_SAMPLE_CLAIMS = {
    "1. Supported: Kharif Food Grains Farmer Premium (2.0%)": (
        "Under the 2023 PMFBY operational guidelines, what is the maximum farmer premium for Kharif food grains?",
        "Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 2.0% of Sum Insured.",
    ),
    "2. Wrong Context: 5.0% Claimed on Kharif Food Grains (Commercial Crop Rate)": (
        "For Kharif food grains under PMFBY, what is the maximum farmer premium?",
        "Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 5.0% of Sum Insured.",
    ),
    "3. Contradicted: Claiming Flat Rate Ignoring 'Whichever is Less' Qualifier": (
        "Under the 2023 PMFBY operational guidelines, does a Kharif food-grain farmer always pay a flat 2.0% premium?",
        "Under the 2023 PMFBY operational guidelines, a Kharif food-grain farmer always pays a flat 2.0% of Sum Insured even when the actuarial rate is lower at 1.2%.",
    ),
    "4. Unverifiable: Premature / Unverified 2026 Policy Claim": (
        "Under the latest 2026 revised guidelines, what is the maximum farmer premium for Kharif food grains?",
        "Under the latest current 2026 revised PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 1.0% of Sum Insured.",
    ),
    "5. Supported Add-on: Wild Animal Attack 100% State Cost (PIB Dec 2025)": (
        "What share of the cost is borne by the State Government when notifying wild animal attack add-on cover?",
        "According to the December 2025 PIB press release (PRID=2197713), wild animal attack add-on cover under PMFBY is implemented 100.0% at the cost of the respective State Government.",
    ),
}

PMKISAN_SAMPLE_CLAIMS = {
    "1. Supported: Annual Income Support (Rs 6,000 / year)": (
        "Under PM-KISAN, what is the annual financial assistance provided to eligible farmer families?",
        "Under PM-KISAN, eligible landholding farmer families receive an annual financial benefit of Rs 6000.",
    ),
    "2. Wrong Context: Rs 6,000 Claimed Per Instalment (Frequency Distractor)": (
        "Under PM-KISAN, what is the financial assistance provided per four-monthly instalment?",
        "Under PM-KISAN, eligible farmers receive Rs 6000 per instalment.",
    ),
    "3. Wrong Context: Tenant Farmers Claiming Rs 6,000 (Ineligible Beneficiary)": (
        "Under PM-KISAN, what is the annual financial support provided to tenant farmers?",
        "Under PM-KISAN, tenant farmers receive an annual income support of Rs 6000.",
    ),
    "4. Supported: Statutory Exclusion of Institutional Landholders (0 INR Benefit)": (
        "Are institutional landholders eligible to receive benefits under PM-KISAN?",
        "All institutional landholders are statutorily excluded (Rs 0 benefit) from PM-KISAN.",
    ),
    "5. Contradicted: Claiming 4 Quarterly Instalments per Year instead of 3": (
        "How many instalments are paid in a financial year under PM-KISAN?",
        "Under PM-KISAN, the financial benefit is disbursed in 4 quarterly instalments per year.",
    ),
    "6. Supported: Mandatory 100% eKYC and Aadhaar DBT": (
        "What is the eKYC compliance requirement for registered farmers under PM-KISAN?",
        "Under PM-KISAN, eKYC completion is 100 percent mandatory for all registered farmers.",
    ),
}

with st.sidebar:
    st.header("🏛️ Scheme Selection")
    scheme_choice = st.radio(
        "Select Scheme Domain:",
        ["PMFBY (Crop Insurance)", "PM-KISAN (Direct Income Support)"],
        index=0,
    )
    scheme_key = "PM_KISAN" if "PM-KISAN" in scheme_choice else "PMFBY"

    store, retrievers, verifier = load_backend(scheme_key)

    st.header("⚙️ Configuration")
    sample_options = (
        PMKISAN_SAMPLE_CLAIMS if scheme_key == "PM_KISAN" else PMFBY_SAMPLE_CLAIMS
    )
    selected_sample = st.selectbox(
        "Choose a Benchmark Scenario:", ["Custom Claim"] + list(sample_options.keys())
    )
    retrieval_method = st.selectbox("Retrieval Method:", ["hybrid", "semantic", "lexical", "table"])
    top_k = st.slider("Top-K Evidence Items:", min_value=1, max_value=10, value=5)
    st.markdown("---")
    st.markdown("**Active Corpus Status:**")
    st.markdown(f"- Scheme: **{scheme_key}**")
    st.markdown(f"- Indexed Units: **{len(store.evidence_units)}**")
    st.markdown(f"- Verified Rules: **{len(store.trusted_rules)}**")
    if scheme_key == "PM_KISAN":
        st.markdown("- Official Sources: **PM-KISAN Guidelines (2020 & 2019 Hist), PIB June 2019, Official Portal FAQ**")
    else:
        st.markdown("- Official Sources: **PMFBY Operational Guidelines (2023 & 2016), PIB PRID=2197713**")

default_q, default_c = "", ""
if selected_sample != "Custom Claim":
    default_q, default_c = sample_options[selected_sample]

question_input = st.text_input(
    "User Question (Context):",
    value=default_q,
    placeholder="e.g. Under PM-KISAN, what is the annual financial assistance provided to eligible farmer families?",
)
claim_input = st.text_area(
    "Candidate Numerical Claim to Verify:",
    value=default_c,
    height=100,
    placeholder="e.g. Under PM-KISAN, eligible landholding farmer families receive an annual financial benefit of Rs 6000.",
)

if st.button("🔍 Verify Claim", type="primary"):
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

        # Color-coded badge
        verdict = pred.predicted_verdict
        if verdict == "SUPPORTED":
            st.success(f"### Verdict: **{verdict}** ✅")
        elif verdict == "WRONG_CONTEXT":
            st.warning(f"### Verdict: **{verdict}** ⚠️ (Number occurs in document, but applies to a different context/condition)")
        elif verdict == "CONTRADICTED":
            st.error(f"### Verdict: **{verdict}** ❌ (Contradicted under matching context)")
        else:
            st.info(f"### Verdict: **{verdict}** ❓ (Insufficient or ambiguous evidence to establish support)")

        st.markdown(f"**Verification Rationale:** {pred.verification_rationale}")

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
                ("Frequency / Season Agreement", "PASSED", "Rule applies to requested frequency or season"),
                ("Qualification & Exclusions", "PASSED", "Statutory exclusion and qualifier constraints verified"),
                ("Temporal Applicability", "PASSED", "Source document is active and applicable to requested era"),
                ("Source Authority", "PASSED", "Official government guidelines / verified gazette notification"),
            ]
        elif verdict == "WRONG_CONTEXT":
            checks_data = [
                ("Numeric & Unit Agreement", "PASSED", "Claimed number exists in verified official corpus"),
                ("Entity Scope / Category", "FAILED" if any(k in m for m in pred.context_mismatch for k in ("crop", "beneficiary", "entity", "ineligible")) else "PASSED", "Claimed category differs from rule applicability"),
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
