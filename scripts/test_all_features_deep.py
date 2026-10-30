"""Comprehensive End-to-End Feature Test Suite for FieldGuard Enterprise Next-Level Platform.
Tests 100% of the platform's features, across all 7 flagship schemes, dynamic uploads,
grounded Q&A, condition diffs, deterministic gates, audit certificates, and theme toggling.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

DEEP_DIR = Path("results/screenshots/deep_test")
DEEP_DIR.mkdir(parents=True, exist_ok=True)


def log_step(title: str):
    print("\n" + "=" * 70)
    print(f"STEP: {title}")
    print("=" * 70)


def log_pass(desc: str):
    print(f"  [PASS] {desc}")


def run_all_feature_tests():
    print("=" * 70)
    print("STARTING COMPLETE FEATURE-BY-FEATURE VALIDATION SUITE")
    print("Target: http://localhost:8501")
    print("=" * 70)

    stats = {"passed": 0, "failed": 0, "total": 0}

    def record_check(name: str, passed: bool, detail: str = ""):
        stats["total"] += 1
        if passed:
            stats["passed"] += 1
            log_pass(f"{name}: {detail}")
        else:
            stats["failed"] += 1
            print(f"  [FAIL] {name}: {detail}")
            raise AssertionError(f"Check failed: {name} - {detail}")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()

        page.on("console", lambda msg: print(f"    [BROWSER CONSOLE] {msg.type}: {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda err: print(f"    [PAGE ERROR]: {err}"))
        page.on("dialog", lambda dialog: dialog.accept())

        def verify_and_get_verdict():
            with page.expect_response(lambda r: "/api/verify" in r.url and r.status == 200, timeout=20000):
                verify_btn.click()
            page.wait_for_selector("#verification-result-box:not(.hidden)", timeout=15000)
            page.wait_for_selector("#verdict-title", timeout=15000)
            return page.locator("#verdict-title").inner_text()

        # =====================================================================
        # FEATURE 1: Homepage Loading, Header Branding & KPI Hero Cards
        # =====================================================================
        log_step("1. Homepage Loading, Branding & KPI Hero Cards")
        page.goto("http://localhost:8501", wait_until="networkidle", timeout=30000)
        page.wait_for_selector("header", timeout=15000)

        # Header check
        header_text = page.locator("header").inner_text()
        record_check("Header Brand", "FieldGuard" in header_text, "FieldGuard brand detected")
        record_check("Version Badge", "v3.0 ENTERPRISE" in header_text, "v3.0 ENTERPRISE badge present")
        record_check("Engine Status", "Groq LPU Active" in header_text or "Engine Active" in header_text, "Active engine status confirmed")

        # KPI Cards check
        kpi_cards = page.locator(".glass-card").all_inner_texts()
        record_check("KPI Cards Count", len(kpi_cards) >= 4, f"Found {len(kpi_cards)} initial cards")
        record_check("Empirical Accuracy KPI", any("94.05%" in c for c in kpi_cards), "94.05% held-out accuracy shown")
        record_check("FSR KPI", any("2.63%" in c for c in kpi_cards), "2.63% false support rate shown")
        record_check("Average Latency KPI", any("1.42 ms" in c for c in kpi_cards), "1.42 ms average latency shown")

        page.screenshot(path=str(DEEP_DIR / "01_homepage_hero_kpis.png"))
        log_pass("Saved screenshot: 01_homepage_hero_kpis.png")

        # =====================================================================
        # FEATURE 2: Verification Studio — All 7 Flagship Schemes
        # =====================================================================
        log_step("2. Verification Studio: Testing All 7 Flagship Welfare Schemes")
        page.wait_for_function("document.getElementById('select-scheme') && document.getElementById('select-scheme').options.length >= 7", timeout=10000)
        verify_btn = page.locator("#btn-verify")

        schemes_to_test = [
            ("PMFBY", "PMFBY", "SUPPORTED", "Kharif food grains 2.0% maximum premium"),
            ("PM_KISAN", "PM-KISAN", "SUPPORTED", "₹6,000 per year income support"),
            ("MGNREGA", "MGNREGS", "SUPPORTED", "100 days statutory wage employment"),
            ("PM_JAY", "PM-JAY", "SUPPORTED", "₹5,00,000 family health cover cashless"),
            ("PMAY_G", "PMAY-G", "SUPPORTED", "₹1,20,000 assistance in plain areas"),
            ("PM_KUSUM", "PM-KUSUM", "SUPPORTED", "60% solar pump capital subsidy"),
            ("PMMY", "PMMY", "SUPPORTED", "₹50,000 Shishu micro-credit collateral-free"),
        ]

        for s_id, expected_badge, expected_verdict, test_label in schemes_to_test:
            print(f"\n  --> Testing Scheme: {s_id} ({test_label})")
            page.select_option("#select-scheme", s_id)
            time.sleep(0.5)

            badge = page.locator("#active-scheme-badge").inner_text()
            record_check(f"Badge {s_id}", expected_badge in badge, f"Badge shows '{badge}'")

            # Check scenario auto-fill
            page.wait_for_function("document.getElementById('input-claim') && document.getElementById('input-claim').value.length > 5")
            claim_text = page.locator("#input-claim").input_value()
            record_check(f"Scenario Auto-fill {s_id}", len(claim_text) > 10, f"Claim auto-filled: '{claim_text[:50]}...'")

            # Click verify with network expectation
            actual_verdict = verify_and_get_verdict()
            timing = page.locator("#verdict-timing-badge").inner_text()
            record_check(f"Verdict {s_id}", actual_verdict == expected_verdict, f"Verdict={actual_verdict} in {timing}")

            # Verify side-by-side diff table has rows
            diff_rows = page.locator("#condition-diff-tbody tr").all_inner_texts()
            record_check(f"Diff Matrix {s_id}", len(diff_rows) >= 1, f"{len(diff_rows)} condition diff rows rendered")

            # Verify deterministic gates checklist has items
            gate_items = page.locator("#condition-checks-list > div").all_inner_texts()
            record_check(f"Gates Checklist {s_id}", len(gate_items) >= 4, f"{len(gate_items)} gate checklist items rendered")

            # Verify retrieved evidence cards
            ev_cards = page.locator("#retrieved-evidence-cards > div").all_inner_texts()
            record_check(f"Evidence Passages {s_id}", len(ev_cards) >= 1, f"{len(ev_cards)} official evidence cards rendered")

            screenshot_name = f"02_scheme_{s_id.lower()}_{actual_verdict.lower()}.png"
            page.screenshot(path=str(DEEP_DIR / screenshot_name), full_page=True)
            log_pass(f"Saved screenshot: {screenshot_name}")

        # =====================================================================
        # FEATURE 3: Wrong Context Distractor Verification
        # =====================================================================
        log_step("3. Testing Wrong-Context Distractor Detection")
        page.select_option("#select-scheme", "PMFBY")
        time.sleep(0.5)

        # Select Scenario 2 (5.0% Claimed on Kharif Food Grains)
        page.evaluate("() => { document.getElementById('select-scenario').value = '1'; onScenarioSelect(); }")
        time.sleep(0.5)
        wrong_claim = page.locator("#input-claim").input_value()
        print(f"  Evaluating Distractor Claim: '{wrong_claim}'")

        wc_verdict = verify_and_get_verdict()
        record_check("Distractor Verdict", wc_verdict in ("WRONG_CONTEXT", "CONTRADICTED"), f"Correctly rejected as {wc_verdict}")

        page.screenshot(path=str(DEEP_DIR / "03_wrong_context_verification.png"), full_page=True)
        log_pass("Saved screenshot: 03_wrong_context_verification.png")

        # =====================================================================
        # FEATURE 4: Official Cryptographic Audit Certificate Generation
        # =====================================================================
        log_step("4. Testing Cryptographic Audit Certificate Generation & Provenance")
        cert_btn = page.locator("button:has-text('Download Audit Certificate')").first
        with page.expect_response(lambda r: "/api/certificate" in r.url and r.status == 200, timeout=10000):
            cert_btn.click()

        page.wait_for_selector("#cert-modal:not(.hidden)", timeout=5000)
        page.wait_for_selector("#cert-content", timeout=5000)
        cert_text = page.locator("#cert-content").inner_text()

        record_check("Cert ID", "CERTIFICATE ID: FG-CERT-" in cert_text, "Valid FG-CERT- ID issued")
        record_check("Cert Authenticity", "VERIFIED_OFFICIAL_RECORD" in cert_text, "Official record authenticity certified")
        record_check("SHA-256 Provenance", "SHA256 PROVENANCE HASH:" in cert_text, "SHA-256 provenance hash generated")

        page.screenshot(path=str(DEEP_DIR / "04_audit_certificate_modal.png"))
        log_pass("Saved screenshot: 04_audit_certificate_modal.png")

        # Close Certificate Modal
        page.evaluate("closeCertModal()")
        time.sleep(0.5)
        record_check("Cert Modal Closed", page.locator("#cert-modal").get_attribute("class") and "hidden" in page.locator("#cert-modal").get_attribute("class"), "Modal closed cleanly")

        # =====================================================================
        # FEATURE 5: Keyboard Shortcut Verification (Ctrl + Enter)
        # =====================================================================
        log_step("5. Testing Keyboard Shortcut (Ctrl + Enter)")
        page.select_option("#select-scheme", "PM_KISAN")
        time.sleep(0.5)
        page.evaluate("() => { document.getElementById('select-scenario').value = '0'; onScenarioSelect(); }")
        time.sleep(0.5)

        # Trigger verify via Ctrl + Enter with network expectation
        with page.expect_response(lambda r: "/api/verify" in r.url and r.status == 200, timeout=15000):
            page.keyboard.press("Control+Enter")
        page.wait_for_selector("#verdict-title", timeout=15000)
        shortcut_verdict = page.locator("#verdict-title").inner_text()
        record_check("Ctrl+Enter Verification", shortcut_verdict == "SUPPORTED", f"Keyboard shortcut triggered verification: {shortcut_verdict}")

        # Test Clear Button
        clear_btn = page.locator("button:has-text('Clear')").first
        clear_btn.click()
        time.sleep(0.5)
        claim_after_clear = page.locator("#input-claim").input_value()
        record_check("Clear Inputs Button", claim_after_clear == "", "Input claim cleared successfully")

        # =====================================================================
        # FEATURE 6: Tab 2 — Grounded Policy Question Answering
        # =====================================================================
        log_step("6. Testing Tab 2: Grounded Policy Question Answering")
        page.locator("#nav-qa").click()
        time.sleep(0.5)
        record_check("QA Tab Active", page.locator("#tab-qa:not(.hidden)").is_visible(), "Tab 2 active")

        # Query 1: PM-KISAN
        qa_input = page.locator("#qa-question-input")
        qa_input.fill("What is the annual financial support provided under PM-KISAN?")
        with page.expect_response(lambda r: "/api/qa" in r.url and r.status == 200, timeout=15000):
            page.locator("button:has-text('Search & Answer')").click()

        page.wait_for_selector("#qa-citations-list > div", timeout=15000)
        ans1 = page.locator("#qa-answer-text").inner_text()
        citations1 = page.locator("#qa-citations-list > div").all_inner_texts()
        record_check("QA Answer Generated", len(ans1) > 20 and "Searching" not in ans1, f"Answer: '{ans1[:80]}...'")
        record_check("QA Citations Rendered", len(citations1) >= 1, f"Found {len(citations1)} source citations with physical PDF pages")

        page.screenshot(path=str(DEEP_DIR / "05_grounded_policy_qa_pmkisan.png"), full_page=True)
        log_pass("Saved screenshot: 05_grounded_policy_qa_pmkisan.png")

        # Query 2: PMFBY Kharif
        page.evaluate("() => { document.getElementById('select-scheme').value = 'PMFBY'; onSchemeChange(); }")
        time.sleep(0.5)
        qa_input.fill("What is the maximum premium rate payable by a farmer for Kharif food grains?")
        with page.expect_response(lambda r: "/api/qa" in r.url and r.status == 200, timeout=15000):
            page.locator("button:has-text('Search & Answer')").click()

        page.wait_for_selector("#qa-citations-list > div", timeout=15000)
        ans2 = page.locator("#qa-answer-text").inner_text()
        record_check("QA Answer PMFBY", "2" in ans2 or "food" in ans2.lower() or "premium" in ans2.lower(), f"PMFBY Grounded Answer: '{ans2[:80]}...'")

        # =====================================================================
        # FEATURE 7: Tab 3 — Evaluation Benchmark Leaderboard
        # =====================================================================
        log_step("7. Testing Tab 3: Evaluation Benchmark Leaderboard")
        page.locator("#nav-benchmark").click()
        time.sleep(0.5)
        record_check("Benchmark Tab Active", page.locator("#tab-benchmark:not(.hidden)").is_visible(), "Tab 3 active")

        bench_text = page.locator("#tab-benchmark").inner_text()
        record_check("FieldGuard Metric (94.05%)", "94.05%" in bench_text, "Held-out accuracy metric 94.05% verified")
        record_check("FSR Metric (2.63%)", "2.63%" in bench_text, "False Support Rate 2.63% verified")
        record_check("Baseline C Metric (72.62%)", "72.62%" in bench_text, "Baseline C comparison verified")
        record_check("Baseline B Metric (44.64%)", "44.64%" in bench_text, "Baseline B comparison verified")
        record_check("Baseline A Metric (10.71%)", "10.71%" in bench_text, "Baseline A comparison verified")
        record_check("Transfer Accuracy (92.31%)", "92.31%" in bench_text, "Zero-shot transfer accuracy verified")

        page.screenshot(path=str(DEEP_DIR / "06_benchmark_leaderboard.png"), full_page=True)
        log_pass("Saved screenshot: 06_benchmark_leaderboard.png")

        # =====================================================================
        # FEATURE 8: Tab 4 — Policy Rules & Evidence Corpus Explorer
        # =====================================================================
        log_step("8. Testing Tab 4: Policy Rules & Statutory Corpus Explorer")
        page.locator("#nav-docs").click()
        time.sleep(0.5)
        record_check("Corpus Tab Active", page.locator("#tab-docs:not(.hidden)").is_visible(), "Tab 4 active")

        rule_rows = page.locator("#corpus-rules-tbody tr").all_inner_texts()
        record_check("Corpus Rules Count", len(rule_rows) >= 7, f"Found {len(rule_rows)} statutory rule records")
        corpus_text = page.locator("#corpus-rules-tbody").inner_text()
        record_check("PMFBY in Corpus", "PMFBY" in corpus_text, "PMFBY rules present")
        record_check("PM-KISAN in Corpus", "PM-KISAN" in corpus_text, "PM-KISAN rules present")
        record_check("MGNREGS in Corpus", "MGNREGS" in corpus_text, "MGNREGS rules present")
        record_check("PM-JAY in Corpus", "PM-JAY" in corpus_text, "PM-JAY rules present")
        record_check("PMAY-G in Corpus", "PMAY-G" in corpus_text, "PMAY-G rules present")
        record_check("PM-KUSUM in Corpus", "PM-KUSUM" in corpus_text, "PM-KUSUM rules present")
        record_check("PMMY in Corpus", "PMMY" in corpus_text, "PMMY rules present")

        page.screenshot(path=str(DEEP_DIR / "07_policy_rules_corpus.png"), full_page=True)
        log_pass("Saved screenshot: 07_policy_rules_corpus.png")

        # =====================================================================
        # FEATURE 9: Dynamic Custom Policy Document Ingestion (Modal & Session)
        # =====================================================================
        log_step("9. Testing Dynamic Document Upload Modal & Ingestion Session")
        page.locator("#nav-verify").click()
        time.sleep(0.5)

        # Open Upload Modal
        page.locator("button:has-text('Upload PDF/TXT')").first.click()
        page.wait_for_selector("#upload-modal:not(.hidden)", timeout=5000)
        record_check("Upload Modal Opened", page.locator("#upload-modal").is_visible(), "Upload modal open")

        # Create test document
        test_policy_text = (
            "Women receive 50 percent assistance.\n\n"
            "Men receive 40 percent assistance.\n"
        )
        test_doc_path = DEEP_DIR / "rajasthan_solar_mission.txt"
        test_doc_path.write_text(test_policy_text, encoding="utf-8")

        # Attach file
        page.locator("#file-input").set_input_files(str(test_doc_path))
        time.sleep(0.5)

        file_label = page.locator("#selected-file-label").inner_text()
        record_check("Selected File Label", "rajasthan_solar_mission.txt" in file_label, f"File selected: {file_label}")

        # Submit upload with network expectation
        submit_btn = page.locator("#btn-submit-upload")
        record_check("Submit Button Enabled", submit_btn.is_enabled(), "Submit button active")
        with page.expect_response(lambda r: "/api/upload" in r.url and r.status == 200, timeout=15000):
            submit_btn.click()

        # Verify active session banner
        page.wait_for_selector("#upload-session-banner:not(.hidden)", timeout=15000)
        banner_text = page.locator("#upload-session-banner").inner_text()
        record_check("Custom Document Banner", "custom document mode" in banner_text.lower(), "Active Custom Document Mode banner displayed")
        record_check("Uploaded File Pill", "rajasthan_solar_mission.txt" in banner_text, "Filename shown on banner")

        page.screenshot(path=str(DEEP_DIR / "08_custom_document_mode_active.png"), full_page=True)
        log_pass("Saved screenshot: 08_custom_document_mode_active.png")

        # Test Claim Verification on uploaded document
        page.locator("#input-claim").fill("Women receive 50 percent assistance.")
        up_verdict = verify_and_get_verdict()
        record_check("Uploaded Doc Claim Verdict", up_verdict == "SUPPORTED", f"Verdict={up_verdict} against uploaded document")

        # Test Q&A on uploaded document
        page.locator("#nav-qa").click()
        time.sleep(0.5)
        qa_input.fill("What is the assistance for women?")
        with page.expect_response(lambda r: "/api/qa" in r.url and r.status == 200, timeout=15000):
            page.locator("button:has-text('Search & Answer')").click()
        page.wait_for_selector("#qa-citations-list > div", timeout=15000)
        up_qa_ans = page.locator("#qa-answer-text").inner_text()
        record_check("Uploaded Doc QA", "50" in up_qa_ans or "assistance" in up_qa_ans.lower(), f"Answer on uploaded doc: '{up_qa_ans[:80]}...'")

        # Return to Flagship Corpus via banner button
        page.locator("#nav-verify").click()
        time.sleep(0.5)
        page.locator("#upload-session-banner button:has-text('Return to Flagship Corpus')").click()
        time.sleep(0.5)
        banner_after_clear = page.locator("#upload-session-banner").get_attribute("class")
        record_check("Session Cleared", "hidden" in banner_after_clear, "Custom document mode cleared; returned to flagship corpus")

        # =====================================================================
        # FEATURE 10: Dark / Light Theme Toggle
        # =====================================================================
        log_step("10. Testing Theme Engine (Dark / Light Transitions)")
        page.evaluate("toggleTheme()")
        time.sleep(0.5)
        html_class_light = page.locator("html").get_attribute("class")
        record_check("Light Theme", "light" in html_class_light, f"Class={html_class_light}")
        page.screenshot(path=str(DEEP_DIR / "09_light_theme_mode.png"), full_page=True)
        log_pass("Saved screenshot: 09_light_theme_mode.png")

        page.evaluate("toggleTheme()")
        time.sleep(0.5)
        html_class_dark = page.locator("html").get_attribute("class")
        record_check("Dark Theme Restored", "dark" in html_class_dark, f"Class={html_class_dark}")
        page.screenshot(path=str(DEEP_DIR / "10_dark_theme_restored.png"), full_page=True)
        log_pass("Saved screenshot: 10_dark_theme_restored.png")

        browser.close()

    print("\n" + "=" * 70)
    print(f"COMPLETE FEATURE VALIDATION FINISHED: {stats['passed']} PASSED, {stats['failed']} FAILED (Total: {stats['total']})")
    print("=" * 70)
    assert stats["failed"] == 0


if __name__ == "__main__":
    run_all_feature_tests()
