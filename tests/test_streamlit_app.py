"""Automated end-to-end UI tests for Streamlit FieldGuard Web App.
Uses Streamlit's official AppTest framework to verify all scheme modes,
claim verification, Q&A tabs, file uploads, and edge cases.
"""

from __future__ import annotations

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def app():
    """Initializes and runs AppTest against app.py."""
    at = AppTest.from_file(APP_PATH, default_timeout=35)
    at.run()
    return at


def test_app_initial_load(app):
    """Verify clean initial boot, title, and 8 sidebar scheme options."""
    assert len(app.exception) == 0, f"Exceptions on initial load: {app.exception}"

    # Verify title
    titles = [t.value for t in app.title]
    assert any("FieldGuard" in t for t in titles)

    # Verify sidebar radio options
    radio = app.sidebar.radio[0]
    assert len(radio.options) == 8
    expected_schemes = [
        "PMFBY",
        "PM-KISAN",
        "MGNREGS",
        "PM-JAY",
        "PMAY-G",
        "PM-KUSUM",
        "PMMY",
        "Upload Custom",
    ]
    for exp in expected_schemes:
        assert any(exp in opt for opt in radio.options), f"Option {exp} missing from sidebar: {radio.options}"


def test_pmfby_verification_scenario(app):
    """Test selecting a PMFBY benchmark scenario and verifying the claim."""
    # Select Scenario 1
    scenario_box = app.sidebar.selectbox[0]
    supported_opt = [o for o in scenario_box.options if "1. Supported" in o][0]
    scenario_box.select(supported_opt).run()
    assert len(app.exception) == 0

    # Click verify button
    verify_btn = app.button(key="btn_pre_verify")
    verify_btn.click().run()
    assert len(app.exception) == 0

    # Verify verdict output
    all_success = [s.value for s in app.success]
    has_verdict = any("Verdict:" in s and "SUPPORTED" in s for s in all_success)
    assert has_verdict, f"Expected SUPPORTED verdict in success outputs: {all_success}"

    # Verify condition checks rendered
    all_markdown = [m.value for m in app.markdown]
    has_checks = any("Condition-by-Condition Checks" in m for m in all_markdown)
    assert has_checks


def test_pmfby_qa_tab(app):
    """Test asking a policy question in the Q&A tab under PMFBY."""
    qa_input = app.text_input(key="pre_tab_qa_q")
    qa_input.set_value("What is the maximum farmer premium for Kharif food grains?").run()
    assert len(app.exception) == 0

    qa_btn = app.button(key="btn_pre_qa")
    qa_btn.click().run()
    assert len(app.exception) == 0

    all_markdown = [m.value for m in app.markdown]
    assert any("Grounded Answer & Top Finding" in m for m in all_markdown)


@pytest.mark.parametrize(
    "scheme_keyword",
    [
        "PM-KISAN",
        "MGNREGS",
        "PM-JAY",
        "PMAY-G",
        "PM-KUSUM",
        "PMMY",
    ],
)
def test_flagship_schemes_switch_and_verify(scheme_keyword):
    """Test switching across all flagship schemes and verifying preloaded scenarios."""
    at = AppTest.from_file(APP_PATH, default_timeout=35)
    at.run()

    radio = at.sidebar.radio[0]
    target_opt = [o for o in radio.options if scheme_keyword in o][0]
    radio.set_value(target_opt).run()
    assert len(at.exception) == 0

    # Pick the first supported benchmark scenario
    scenario_box = at.sidebar.selectbox[0]
    target_scenarios = [o for o in scenario_box.options if "1. Supported" in o]
    if target_scenarios:
        scenario_box.select(target_scenarios[0]).run()
        assert len(at.exception) == 0

    # Click Verify
    verify_btn = at.button(key="btn_pre_verify")
    verify_btn.click().run()
    assert len(at.exception) == 0

    all_success = [s.value for s in at.success]
    assert any("SUPPORTED" in s for s in all_success), f"Expected SUPPORTED in {all_success}"


def test_upload_custom_document_flow():
    """Test arbitrary document upload, Q&A grounded answering, and claim verification."""
    at = AppTest.from_file(APP_PATH, default_timeout=35)
    at.run()

    # Switch to Upload Mode
    radio = at.sidebar.radio[0]
    upload_opt = [o for o in radio.options if "Upload Custom" in o][0]
    radio.set_value(upload_opt).run()
    assert len(at.exception) == 0

    # Simulate uploading a policy document
    sample_policy = (
        "NATIONAL MICRO-IRRIGATION POLICY 2026\n"
        "1. Subsidy Entitlement: Small and marginal farmers are entitled to 55 percent subsidy\n"
        "for installation of drip irrigation systems up to Rs 75000 per hectare.\n"
        "2. General Category: Other farmers receive 45 percent subsidy.\n"
    )
    at.file_uploader[0].upload("micro_irrigation_2026.txt", sample_policy.encode("utf-8")).run()
    assert len(at.exception) == 0

    # 1. Test Question Answering
    qa_input = at.text_input[0]
    qa_input.set_value("What is the subsidy percentage for small and marginal farmers?").run()
    qa_btn = at.button(key="btn_qa")
    qa_btn.click().run()
    assert len(at.exception) == 0

    all_markdown = [m.value for m in at.markdown]
    assert any("Grounded Answer" in m for m in all_markdown)

    # 2. Test Claim Verification
    claim_area = at.text_area(key="up_claim_text")
    claim_area.set_value("Small and marginal farmers receive 55 percent subsidy for drip irrigation.").run()
    verify_btn = at.button(key="btn_up_verify")
    verify_btn.click().run()
    assert len(at.exception) == 0

    all_success = [s.value for s in at.success]
    assert any("SUPPORTED" in s for s in all_success)


def test_empty_input_validation(app):
    """Test that submitting empty claim warns the user without raising exceptions."""
    # Clear claim input and submit
    claim_area = app.text_area(key="pre_c_input")
    claim_area.set_value("").run()
    verify_btn = app.button(key="btn_pre_verify")
    verify_btn.click().run()
    assert len(app.exception) == 0
    warnings = [w.value for w in app.warning]
    assert any("Please enter a candidate numerical claim" in w for w in warnings)
