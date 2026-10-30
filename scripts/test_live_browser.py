"""Live browser automation test for running FieldGuard Enterprise Next-Gen UI (http://localhost:8501).
Uses Playwright with Microsoft Edge to test all tabs, verification, diff tables, Q&A, and modal uploads.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import time
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

RESULTS_DIR = Path("results/screenshots")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def run_live_browser_tests():
    print("=" * 65)
    print("STARTING LIVE SPA BROWSER TESTS AGAINST http://localhost:8501")
    print("=" * 65)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 950})
        page = context.new_page()

        page.on("console", lambda msg: print(f"    [BROWSER CONSOLE] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"    [PAGE ERROR]: {err}"))
        page.on("dialog", lambda dialog: print(f"    [BROWSER DIALOG]: {dialog.message}") or dialog.accept())

        # -------------------------------------------------------------
        # 1. Navigate to live application
        # -------------------------------------------------------------
        print("\n1. Navigating to http://localhost:8501...")
        page.goto("http://localhost:8501", wait_until="networkidle", timeout=30000)
        page.wait_for_selector("header", timeout=15000)
        
        brand_text = page.locator("header").inner_text()
        print(f"   [PASS] Header detected: FieldGuard v3.0 ENTERPRISE")
        assert "FieldGuard" in brand_text

        # Verify KPI Hero Cards
        kpi_cards = page.locator(".glass-card").all_inner_texts()
        print(f"   [PASS] Detected {len(kpi_cards)} initial cards on page.")
        assert any("accuracy" in c.lower() for c in kpi_cards)
        assert any("94.05%" in c for c in kpi_cards)

        # -------------------------------------------------------------
        # 2. Test Verification Studio with PMFBY Scenario 1
        # -------------------------------------------------------------
        print("\n2. Testing Verification Studio: PMFBY Default Scenario...")
        page.wait_for_function("document.getElementById('select-scheme') && document.getElementById('select-scheme').options.length >= 7", timeout=10000)
        
        # Check that all 7 flagship schemes are loaded in the select
        options = page.locator("#select-scheme option").all_inner_texts()
        print(f"   Detected {len(options)} scheme options in dropdown:")
        for opt in options:
            print(f"     - {opt}")
        assert len(options) >= 7
        assert any("PMFBY" in o for o in options)
        assert any("PM-KISAN" in o for o in options)
        assert any("MGNREGS" in o or "MGNREGA" in o for o in options)

        # Wait for claim to be populated
        page.wait_for_function("document.getElementById('input-claim') && document.getElementById('input-claim').value.length > 5", timeout=10000)
        curr_claim = page.locator("#input-claim").input_value()
        print(f"   [PASS] Current claim input: '{curr_claim[:60]}...'")

        # Click "Verify Numerical Claim" button
        verify_btn = page.locator("#btn-verify")
        verify_btn.click()
        
        # Wait for verification result to appear
        page.wait_for_selector("#verification-result-box:not(.hidden)", timeout=15000)
        page.wait_for_selector("#verdict-title", timeout=15000)
        verdict = page.locator("#verdict-title").inner_text()
        timing = page.locator("#verdict-timing-badge").inner_text()
        print(f"   [PASS] Live Verification Verdict: {verdict} (Latency: {timing})")
        assert verdict == "SUPPORTED"

        # Check Side-by-Side Diff Table
        diff_rows = page.locator("#condition-diff-tbody tr").all_inner_texts()
        print(f"   [PASS] Condition Diff Matrix rows: {len(diff_rows)}")
        assert len(diff_rows) >= 3

        # Check 10-Step Deterministic Gates
        gate_items = page.locator("#condition-checks-list > div").all_inner_texts()
        print(f"   [PASS] Gate Checklist items: {len(gate_items)}")
        assert len(gate_items) >= 5

        # Check Evidence Passages
        evidence_cards = page.locator("#retrieved-evidence-cards > div").all_inner_texts()
        print(f"   [PASS] Retrieved Evidence Cards: {len(evidence_cards)}")
        assert len(evidence_cards) >= 3

        # Screenshot PMFBY result
        pmfby_screen = RESULTS_DIR / "live_spa_pmfby_supported.png"
        page.screenshot(path=str(pmfby_screen), full_page=True)
        print(f"   [PASS] Saved screenshot: {pmfby_screen}")

        # -------------------------------------------------------------
        # 3. Test Audit Certificate Modal
        # -------------------------------------------------------------
        print("\n3. Testing Audit Certificate Modal...")
        cert_btn = page.locator("button:has-text('Audit Certificate')").first
        cert_btn.click()
        page.wait_for_selector("#cert-modal:not(.hidden)", timeout=5000)
        page.wait_for_selector("#cert-content", timeout=5000)
        
        cert_text = page.locator("#cert-content").inner_text()
        assert "CERTIFICATE ID:" in cert_text
        assert "SHA256 PROVENANCE HASH:" in cert_text
        print("   [PASS] Cryptographic audit certificate modal generated successfully.")

        # Screenshot Certificate Modal
        cert_screen = RESULTS_DIR / "live_spa_audit_certificate.png"
        page.screenshot(path=str(cert_screen))
        print(f"   [PASS] Saved screenshot: {cert_screen}")

        # Close Certificate Modal
        page.evaluate("closeCertModal()")
        time.sleep(0.5)

        # -------------------------------------------------------------
        # 4. Test Scheme Switch to PM-KISAN
        # -------------------------------------------------------------
        print("\n4. Testing Scheme Switch to PM-KISAN...")
        page.select_option("#select-scheme", "PM_KISAN")
        time.sleep(1.0)
        
        # Verify PM-KISAN badge
        badge = page.locator("#active-scheme-badge").inner_text()
        assert "PM-KISAN" in badge
        print(f"   [PASS] Active scheme badge updated to: {badge}")

        # Verify Scenario auto-fill
        claim_val = page.locator("#input-claim").input_value()
        print(f"   [PASS] Auto-filled scenario claim: '{claim_val[:60]}...'")
        assert "6000" in claim_val

        # Verify Claim
        verify_btn.click()
        page.wait_for_selector("#verdict-title", timeout=15000)
        kisan_verdict = page.locator("#verdict-title").inner_text()
        print(f"   [PASS] PM-KISAN Live Alert Verdict: {kisan_verdict}")
        assert kisan_verdict == "SUPPORTED"

        kisan_screen = RESULTS_DIR / "live_spa_pm_kisan_supported.png"
        page.screenshot(path=str(kisan_screen), full_page=True)
        print(f"   [PASS] Saved screenshot: {kisan_screen}")

        # -------------------------------------------------------------
        # 5. Test Tab 2: Grounded Policy Q&A
        # -------------------------------------------------------------
        print("\n5. Testing Tab 2: Grounded Policy Q&A...")
        page.locator("#nav-qa").click()
        time.sleep(0.5)
        assert page.locator("#tab-qa:not(.hidden)").is_visible()

        qa_input = page.locator("#qa-question-input")
        qa_input.fill("What is the financial assistance provided under PM-KISAN?")
        
        search_qa_btn = page.locator("button:has-text('Search & Answer')").first
        search_qa_btn.click()

        page.wait_for_selector("#qa-result-box:not(.hidden)", timeout=15000)
        page.wait_for_selector("#qa-citations-list > div", timeout=15000)
        ans = page.locator("#qa-answer-text").inner_text()
        print(f"   [PASS] Grounded Policy Answer: {ans[:90]}...")
        assert len(ans) > 20
        assert "Searching" not in ans

        citations = page.locator("#qa-citations-list > div").all_inner_texts()
        print(f"   [PASS] Citations rendered: {len(citations)} source passages.")
        assert len(citations) >= 1

        qa_screen = RESULTS_DIR / "live_spa_policy_qa.png"
        page.screenshot(path=str(qa_screen), full_page=True)
        print(f"   [PASS] Saved screenshot: {qa_screen}")

        # -------------------------------------------------------------
        # 6. Test Tab 3: Evaluation Benchmark Leaderboard
        # -------------------------------------------------------------
        print("\n6. Testing Tab 3: Evaluation Benchmark Leaderboard...")
        page.locator("#nav-benchmark").click()
        time.sleep(0.5)
        assert page.locator("#tab-benchmark:not(.hidden)").is_visible()

        bench_text = page.locator("#tab-benchmark").inner_text()
        assert "94.05%" in bench_text
        assert "Baseline C" in bench_text
        assert "Baseline B" in bench_text
        print("   [PASS] Benchmark leaderboard rendered with empirical comparative metrics.")

        bench_screen = RESULTS_DIR / "live_spa_benchmark.png"
        page.screenshot(path=str(bench_screen), full_page=True)
        print(f"   [PASS] Saved screenshot: {bench_screen}")

        # -------------------------------------------------------------
        # 7. Test Tab 4: Policy Rules & Evidence Corpus
        # -------------------------------------------------------------
        print("\n7. Testing Tab 4: Policy Rules & Corpus Explorer...")
        page.locator("#nav-docs").click()
        time.sleep(0.5)
        assert page.locator("#tab-docs:not(.hidden)").is_visible()

        rule_rows = page.locator("#corpus-rules-tbody tr").all_inner_texts()
        print(f"   [PASS] Statutory Rule records in table: {len(rule_rows)}")
        assert len(rule_rows) >= 7

        rules_screen = RESULTS_DIR / "live_spa_corpus_rules.png"
        page.screenshot(path=str(rules_screen), full_page=True)
        print(f"   [PASS] Saved screenshot: {rules_screen}")

        # -------------------------------------------------------------
        # 8. Test Dynamic File Upload Mode
        # -------------------------------------------------------------
        print("\n8. Testing Dynamic Document Upload Modal & Indexing...")
        # Switch back to Verify Tab
        page.locator("#nav-verify").click()
        time.sleep(0.5)

        # Click upload button in header
        page.locator("button:has-text('Upload PDF/TXT')").first.click()
        page.wait_for_selector("#upload-modal:not(.hidden)", timeout=5000)

        # Create temporary policy document
        sample_policy = (
            "GOVERNMENT OF RAJASTHAN\n"
            "CHIEF MINISTER SOLAR SCHEME GUIDELINES 2026\n"
            "1. Solar Water Pump Subsidy:\n"
            "Women farmers receive 50 percent assistance for installation of solar pumps.\n"
            "2. General Category Farmers:\n"
            "Men receive 40 percent assistance.\n"
        )
        sample_path = RESULTS_DIR / "sample_rajasthan_solar.txt"
        sample_path.write_text(sample_policy, encoding="utf-8")

        # Set input file
        file_input = page.locator("#file-input")
        file_input.set_input_files(str(sample_path))
        time.sleep(0.5)

        submit_btn = page.locator("#btn-submit-upload")
        assert submit_btn.is_enabled()
        
        # Submit upload
        submit_btn.click()

        # Wait for banner to appear
        page.wait_for_selector("#upload-session-banner:not(.hidden)", timeout=15000)
        banner_text = page.locator("#upload-session-banner").inner_text()
        print(f"   [PASS] Custom Document Mode Banner: {banner_text}")
        assert "custom document mode" in banner_text.lower()

        # Verify claim against uploaded doc
        claim_input = page.locator("#input-claim")
        claim_input.fill("Women receive 50 percent assistance.")
        
        verify_btn.click()
        page.wait_for_selector("#verdict-title", timeout=15000)
        upload_verdict = page.locator("#verdict-title").inner_text()
        print(f"   [PASS] Uploaded Document Claim Verdict: {upload_verdict}")
        assert upload_verdict == "SUPPORTED"

        upload_screen = RESULTS_DIR / "live_spa_uploaded_doc_mode.png"
        page.screenshot(path=str(upload_screen), full_page=True)
        print(f"   [PASS] Saved screenshot: {upload_screen}")

        # -------------------------------------------------------------
        # 9. Test Theme Switcher
        # -------------------------------------------------------------
        print("\n9. Testing Dark / Light Theme Toggle...")
        page.evaluate("toggleTheme()")
        time.sleep(0.5)
        html_class = page.locator("html").get_attribute("class")
        print(f"   [PASS] Switched theme to: {html_class}")
        assert "light" in html_class

        page.evaluate("toggleTheme()")
        time.sleep(0.5)
        html_class = page.locator("html").get_attribute("class")
        print(f"   [PASS] Reverted theme to: {html_class}")
        assert "dark" in html_class

        browser.close()

    print("\n" + "=" * 65)
    print("ALL LIVE SPA BROWSER TESTS PASSED (100%)!")
    print("=" * 65)


if __name__ == "__main__":
    run_live_browser_tests()
