"""Generalization test suite for uploaded PDFs and TXTs across 5 diverse layouts (Problem 2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from fieldguard.evaluation.runner import build_all_retrievers
from fieldguard.uploaded_doc_engine import build_valid_pdf_bytes, process_uploaded_document
from fieldguard.verifier import FieldGuardVerifier

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "uploads"


def ensure_upload_fixture_files() -> dict[str, Path]:
    """Ensure all 5 upload test corpus files (3 multi-page/table PDFs and 2 TXTs) exist on disk."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Multi-page Prose PDF: PM SVANidhi Street Vendor Guidelines
    svanidhi_pages = [
        [
            "PM SVANIDHI — MICRO-CREDIT FACILITY FOR URBAN STREET VENDORS",
            "",
            "1. Working Capital Loan Tranches and Tenure:",
            "Under PM SVANidhi, eligible urban street vendors receive a collateral-free first tranche working capital loan of up to Rs. 10,000 with a repayment tenure of 12 months.",
            "",
            "Upon timely repayment of the first tranche loan, street vendors become eligible for a second tranche working capital loan of up to Rs. 20,000.",
            "",
            "Vendors who repay the second tranche loan on time are eligible for a third tranche working capital loan of up to Rs. 50,000 for business expansion.",
        ],
        [
            "2. Interest Subvention and Digital Cashback Incentives:",
            "Street vendors availing working capital loans under PM SVANidhi receive an interest subvention of 7% per annum, which is credited quarterly to the borrower bank account.",
            "",
            "To promote digital payments, street vendors receive a cashback incentive of up to Rs. 1,200 per year (capped at Rs. 100 per month) on eligible retail digital transactions.",
            "",
            "3. Eligibility and Exclusions:",
            "Only urban street vendors engaged in vending in urban municipal areas are eligible; corporate retail chains and income tax payers are excluded and not eligible.",
        ],
    ]
    svanidhi_path = FIXTURES_DIR / "pm_svanidhi_street_vendors.pdf"
    svanidhi_path.write_bytes(build_valid_pdf_bytes(svanidhi_pages))

    # 2. Table-Heavy PDF: National Livestock Mission (NLM) Entrepreneurship Guidelines
    nlm_pages = [
        [
            "NATIONAL LIVESTOCK MISSION (NLM) — CAPITAL SUBSIDY SCHEDULE",
            "",
            "Sub-Mission Activity | Beneficiary Scope | Capital Subsidy Rate | Maximum Subsidy Cap | Minimum Unit Size",
            "Rural Poultry Entrepreneurship | Individual & SHGs | 50% | Rs. 25,00,000 | 1,000 parent layers",
            "Sheep and Goat Breeding Unit | Individual & FPOs | 50% | Rs. 50,00,000 | 500 females",
            "Piggery Entrepreneurship | Individual & JLGs | 50% | Rs. 30,00,000 | 100 sows",
            "Fodder and Silage Processing Unit | Entrepreneurs & FPOs | 50% | Rs. 50,00,000 | 2,400 tonnes",
            "",
            "Regional Category Differential Note:",
            "Under NLM breed development norms, SC/ST entrepreneurs in hilly states receive a 60% capital subsidy, whereas general category entrepreneurs in plains receive a 35% capital subsidy.",
        ]
    ]
    nlm_path = FIXTURES_DIR / "national_livestock_mission_table.pdf"
    nlm_path.write_bytes(build_valid_pdf_bytes(nlm_pages))

    # 3. Bullet-List TXT: Namo Drone Didi SHG Guidelines (already on disk)
    drone_path = FIXTURES_DIR / "drone_didi_shg_guidelines.txt"

    # 4. Multi-Column + Broken Indian Numbers TXT: State Solar Cold Storage (already on disk)
    solar_path = FIXTURES_DIR / "state_solar_cold_storage_multicol.txt"

    # 5. Multi-Page Prose + Schedule Table PDF: PM Matru Vandana Yojana (PMMVY 2.0)
    pmmvy_pages = [
        [
            "PRADHAN MANTRI MATRU VANDANA YOJANA (PMMVY 2.0) — MATERNITY BENEFIT GUIDELINES",
            "",
            "1. Maternity Benefit for First Living Child:",
            "Under PMMVY 2.0, eligible pregnant women and lactating mothers receive a total cash maternity benefit of Rs. 5,000 for the first living child, disbursed in 2 instalments.",
            "",
            "Instalment Order | Milestone Condition | Benefit Amount",
            "First Instalment | Early pregnancy registration and at least 1 ANC check-up | Rs. 3,000",
            "Second Instalment | Childbirth registration and first cycle immunization | Rs. 2,000",
        ],
        [
            "2. Maternity Benefit for Second Living Child (Girl Child Incentive):",
            "For the second living child, eligible mothers receive a one-time maternity benefit of Rs. 6,000 in a single instalment after childbirth, provided the second child is a girl child.",
            "",
            "3. Age Requirement and Statutory Exclusions:",
            "The minimum age of the pregnant woman must be at least 19 years at the time of conception.",
            "",
            "Regular government employees, public sector undertaking employees, and income tax payers are excluded and not eligible for the Rs. 5,000 or Rs. 6,000 maternity benefit.",
        ],
    ]
    pmmvy_path = FIXTURES_DIR / "pm_matru_vandana_maternity.pdf"
    pmmvy_path.write_bytes(build_valid_pdf_bytes(pmmvy_pages))

    # 6. National Drone Subsidy 2026 (regression fixture from test_dynamic_document_ingestion_and_qa)
    drone_2026_text = (
        "GOVERNMENT OF INDIA\n"
        "NATIONAL DRONE SUBSIDY SCHEME GUIDELINES 2026\n\n"
        "1. Financial Assistance:\n"
        "Individual farmers from SC/ST and women categories are eligible for financial assistance of 50 percent\n"
        "or up to Rs 500000 for purchasing agricultural drones.\n\n"
        "2. Operational Subsidy:\n"
        "Custom Hiring Centres (CHCs) shall receive a grant of 40 percent of drone cost up to Rs 400000.\n"
    )
    drone_2026_path = FIXTURES_DIR / "national_drone_subsidy_2026.txt"
    drone_2026_path.write_text(drone_2026_text, encoding="utf-8")

    return {
        "pm_svanidhi": svanidhi_path,
        "nlm_table": nlm_path,
        "drone_didi": drone_path,
        "solar_cold_storage": solar_path,
        "pmmvy": pmmvy_path,
        "drone_2026": drone_2026_path,
    }


# 50 labelled claims (10 per document) covering SUPPORTED, CONTRADICTED, WRONG_CONTEXT, UNVERIFIABLE
UPLOAD_GENERALIZATION_CASES: list[tuple[str, str, str, str, str]] = [
    # =========================================================================
    # 1. PM SVANidhi Street Vendors (Multi-page Prose PDF)
    # =========================================================================
    (
        "pm_svanidhi",
        "SVAN_01",
        "What is the maximum first tranche working capital loan under PM SVANidhi?",
        "Under PM SVANidhi, eligible urban street vendors receive a first tranche working capital loan of up to Rs. 10,000.",
        "SUPPORTED",
    ),
    (
        "pm_svanidhi",
        "SVAN_02",
        "What is the second tranche working capital loan amount under PM SVANidhi?",
        "Upon timely repayment of the first tranche loan, street vendors become eligible for a second tranche working capital loan of up to Rs. 20,000.",
        "SUPPORTED",
    ),
    (
        "pm_svanidhi",
        "SVAN_03",
        "What interest subvention rate is provided under PM SVANidhi?",
        "Street vendors availing working capital loans under PM SVANidhi receive an interest subvention of 7% per annum credited quarterly.",
        "SUPPORTED",
    ),
    (
        "pm_svanidhi",
        "SVAN_04",
        "What is the annual digital cashback incentive under PM SVANidhi?",
        "Street vendors receive a cashback incentive of up to Rs. 1,200 per year on eligible retail digital transactions.",
        "SUPPORTED",
    ),
    (
        "pm_svanidhi",
        "SVAN_05",
        "What is the first tranche loan limit under PM SVANidhi?",
        "Under PM SVANidhi, eligible urban street vendors receive a first tranche working capital loan of up to Rs. 15,000.",
        "CONTRADICTED",
    ),
    (
        "pm_svanidhi",
        "SVAN_06",
        "What is the interest subvention percentage under PM SVANidhi?",
        "Street vendors availing working capital loans under PM SVANidhi receive an interest subvention of 12% per annum.",
        "CONTRADICTED",
    ),
    (
        "pm_svanidhi",
        "SVAN_07",
        "How much can a street vendor borrow in the first tranche loan?",
        "Under PM SVANidhi, street vendors receive a first tranche working capital loan of up to Rs. 20,000.",
        "WRONG_CONTEXT",
    ),
    (
        "pm_svanidhi",
        "SVAN_08",
        "How frequently is the 7% interest subvention credited under PM SVANidhi?",
        "Street vendors availing working capital loans under PM SVANidhi receive an interest subvention of 7% credited monthly.",
        "WRONG_CONTEXT",
    ),
    (
        "pm_svanidhi",
        "SVAN_09",
        "What is the minimum floor area required for a vending stall under PM SVANidhi?",
        "Under PM SVANidhi, street vendors must maintain a vending stall floor area of at least 15 square metres.",
        "UNVERIFIABLE",
    ),
    (
        "pm_svanidhi",
        "SVAN_10",
        "How much solar pump horsepower is subsidized under PM SVANidhi?",
        "Under PM SVANidhi, street vendors receive a solar water pump of up to 7.5 HP capacity.",
        "UNVERIFIABLE",
    ),
    # =========================================================================
    # 2. National Livestock Mission Table (Table-heavy PDF)
    # =========================================================================
    (
        "nlm_table",
        "NLM_01",
        "What is the maximum capital subsidy cap for Rural Poultry Entrepreneurship under NLM?",
        "Under the National Livestock Mission, Rural Poultry Entrepreneurship receives a 50% capital subsidy up to a maximum cap of Rs. 25,00,000.",
        "SUPPORTED",
    ),
    (
        "nlm_table",
        "NLM_02",
        "What is the maximum capital subsidy for a Sheep and Goat Breeding Unit under NLM?",
        "Under NLM, a Sheep and Goat Breeding Unit receives a 50% capital subsidy up to Rs. 50,00,000.",
        "SUPPORTED",
    ),
    (
        "nlm_table",
        "NLM_03",
        "What is the maximum capital subsidy cap for Piggery Entrepreneurship under NLM?",
        "Under NLM, Piggery Entrepreneurship receives a 50% capital subsidy up to a maximum cap of Rs. 30,00,000.",
        "SUPPORTED",
    ),
    (
        "nlm_table",
        "NLM_04",
        "What subsidy rate do SC/ST entrepreneurs in hilly states receive under NLM?",
        "Under NLM breed development norms, SC/ST entrepreneurs in hilly states receive a 60% capital subsidy.",
        "SUPPORTED",
    ),
    (
        "nlm_table",
        "NLM_05",
        "What is the maximum capital subsidy cap for Piggery Entrepreneurship under NLM?",
        "Under NLM, Piggery Entrepreneurship receives a capital subsidy up to a maximum cap of Rs. 40,00,000.",
        "CONTRADICTED",
    ),
    (
        "nlm_table",
        "NLM_06",
        "What is the minimum unit size for a Fodder and Silage Processing Unit under NLM?",
        "Under NLM, a Fodder and Silage Processing Unit requires a minimum annual capacity of 5,000 tonnes.",
        "CONTRADICTED",
    ),
    (
        "nlm_table",
        "NLM_07",
        "What capital subsidy rate do general category entrepreneurs in plains receive under NLM?",
        "Under NLM breed development norms, general category entrepreneurs in plains receive a 60% capital subsidy.",
        "WRONG_CONTEXT",
    ),
    (
        "nlm_table",
        "NLM_08",
        "What capital subsidy rate do SC/ST entrepreneurs in hilly states receive under NLM?",
        "Under NLM breed development norms, SC/ST entrepreneurs in hilly states receive a 35% capital subsidy.",
        "WRONG_CONTEXT",
    ),
    (
        "nlm_table",
        "NLM_09",
        "What is the cold storage battery backup duration under the National Livestock Mission?",
        "Under NLM, cold storage rooms must maintain a battery backup duration of 24 hours.",
        "UNVERIFIABLE",
    ),
    (
        "nlm_table",
        "NLM_10",
        "What is the export subsidy for camel milk processing under NLM?",
        "Camel milk exporters receive an export freight subsidy of Rs. 8,00,000 per container.",
        "UNVERIFIABLE",
    ),
    # =========================================================================
    # 3. Namo Drone Didi SHG Guidelines (Bullet-list TXT)
    # =========================================================================
    (
        "drone_didi",
        "DRONE_01",
        "What is the subsidy rate and maximum grant for Women SHGs under Namo Drone Didi?",
        "Under Namo Drone Didi, Women Self-Help Groups (SHGs) receive an 80% subsidy on the drone cost up to a maximum of Rs. 8,00,000.",
        "SUPPORTED",
    ),
    (
        "drone_didi",
        "DRONE_02",
        "What interest subvention is available on the AIF loan for the remaining drone cost?",
        "The remaining 20% of the drone procurement cost may be raised as a credit facility under the Agriculture Infrastructure Fund with an interest subvention of 3% per annum.",
        "SUPPORTED",
    ),
    (
        "drone_didi",
        "DRONE_03",
        "How long is the mandatory Remote Pilot Training for the selected Women SHG member?",
        "One qualified woman member from each selected Women SHG shall undergo mandatory Remote Pilot Training of 15 days duration.",
        "SUPPORTED",
    ),
    (
        "drone_didi",
        "DRONE_04",
        "What is the monthly living stipend paid to a certified Drone Didi pilot?",
        "Each certified Women SHG drone pilot (Drone Didi) receives a monthly living stipend of Rs. 15,000 per month.",
        "SUPPORTED",
    ),
    (
        "drone_didi",
        "DRONE_05",
        "What is the monthly living stipend paid to a certified Drone Didi pilot?",
        "Each certified Women SHG drone pilot (Drone Didi) receives a monthly living stipend of Rs. 25,000 per month.",
        "CONTRADICTED",
    ),
    (
        "drone_didi",
        "DRONE_06",
        "How many days of Remote Pilot Training does the primary Women SHG pilot undergo?",
        "One qualified woman member from each selected Women SHG shall undergo mandatory Remote Pilot Training of 30 days duration.",
        "CONTRADICTED",
    ),
    (
        "drone_didi",
        "DRONE_07",
        "What drone subsidy percentage do individual small and marginal farmers receive?",
        "Under the guidelines, individual small and marginal farmers receive an 80% subsidy on the drone cost.",
        "WRONG_CONTEXT",
    ),
    (
        "drone_didi",
        "DRONE_08",
        "Are private corporate entities eligible for the 80% drone grant?",
        "Private corporate entities receive an 80% subsidy on the drone and accessory cost under Namo Drone Didi.",
        "WRONG_CONTEXT",
    ),
    (
        "drone_didi",
        "DRONE_09",
        "What is the maximum flight altitude allowed for agricultural drones under Namo Drone Didi?",
        "Under Namo Drone Didi, agricultural drones are permitted to fly up to a maximum altitude of 120 square metres.",
        "UNVERIFIABLE",
    ),
    (
        "drone_didi",
        "DRONE_10",
        "What is the hull insurance premium rate for drones in coastal cyclones?",
        "Coastal cyclone insurance for agricultural drones requires a premium of Rs. 45,000 per hectare.",
        "UNVERIFIABLE",
    ),
    # =========================================================================
    # 4. State Solar Cold Storage & Pack-House (Multi-column + Indian format TXT)
    # =========================================================================
    (
        "solar_cold_storage",
        "SOLAR_01",
        "What is the capital subsidy for a 10 MT solar cold storage unit in Hilly and North-Eastern states?",
        "Hilly and North-Eastern states receive a 50% capital subsidy up to Rs. 15,00,000 per solar cold storage unit.",
        "SUPPORTED",
    ),
    (
        "solar_cold_storage",
        "SOLAR_02",
        "What is the capital subsidy for a solar cold storage unit in Plains and Mainland states?",
        "Plains and Mainland states receive a 35% capital subsidy up to Rs. 10,50,000 per solar cold storage unit.",
        "SUPPORTED",
    ),
    (
        "solar_cold_storage",
        "SOLAR_03",
        "What is the capital subsidy for an on-farm pack-house under the State Horticulture Mission?",
        "Individual farmers constructing an on-farm pack-house with a minimum floor area of 36 square metres receive a one-time capital subsidy of Rs. 1,20,000.",
        "SUPPORTED",
    ),
    (
        "solar_cold_storage",
        "SOLAR_04",
        "What is the annual operation and maintenance grant for farmer cooperatives operating solar cold storage?",
        "Eligible farmer cooperatives operating solar cold storage units receive an annual operation and maintenance grant of Rs. 24,000 per year.",
        "SUPPORTED",
    ),
    (
        "solar_cold_storage",
        "SOLAR_05",
        "What is the capital subsidy for an on-farm pack-house under the State Horticulture Mission?",
        "Individual farmers constructing an on-farm pack-house receive a one-time capital subsidy of Rs. 2,50,000.",
        "CONTRADICTED",
    ),
    (
        "solar_cold_storage",
        "SOLAR_06",
        "What is the minimum battery backup duration required for solar cold storage units?",
        "Solar cold storage units must maintain a minimum battery backup duration of 8 hours per day.",
        "CONTRADICTED",
    ),
    (
        "solar_cold_storage",
        "SOLAR_07",
        "What is the maximum capital subsidy for a solar cold storage unit in Plains and Mainland states?",
        "Plains and Mainland states receive a capital subsidy up to Rs. 15,00,000 per solar cold storage unit.",
        "WRONG_CONTEXT",
    ),
    (
        "solar_cold_storage",
        "SOLAR_08",
        "How often do farmer cooperatives receive the Rs. 24,000 operation and maintenance grant?",
        "Eligible farmer cooperatives operating solar cold storage units receive an operation and maintenance grant of Rs. 24,000 monthly.",
        "WRONG_CONTEXT",
    ),
    (
        "solar_cold_storage",
        "SOLAR_09",
        "What is the groundwater table depth limit for solar cold storage installation?",
        "Solar cold storage units require a groundwater depth of at least 45 horsepower.",
        "UNVERIFIABLE",
    ),
    (
        "solar_cold_storage",
        "SOLAR_10",
        "What is the apple grading machine subsidy under the National Saffron Mission?",
        "Saffron growers receive Rs. 9,00,000 for automated optical apple grading lines.",
        "UNVERIFIABLE",
    ),
    # =========================================================================
    # 5. PM Matru Vandana Yojana PMMVY 2.0 (Multi-page Prose + Table PDF)
    # =========================================================================
    (
        "pmmvy",
        "PMMVY_01",
        "What is the total cash maternity benefit for the first living child under PMMVY 2.0?",
        "Under PMMVY 2.0, eligible pregnant women and lactating mothers receive a total cash maternity benefit of Rs. 5,000 for the first living child.",
        "SUPPORTED",
    ),
    (
        "pmmvy",
        "PMMVY_02",
        "What is the benefit amount for the first instalment under PMMVY 2.0?",
        "Under PMMVY 2.0, the First Instalment upon early pregnancy registration and ANC check-up provides a benefit amount of Rs. 3,000.",
        "SUPPORTED",
    ),
    (
        "pmmvy",
        "PMMVY_03",
        "What is the maternity benefit for the second living child if it is a girl child?",
        "For the second living child, eligible mothers receive a one-time maternity benefit of Rs. 6,000 in a single instalment after childbirth, provided the second child is a girl child.",
        "SUPPORTED",
    ),
    (
        "pmmvy",
        "PMMVY_04",
        "What is the minimum age requirement for a pregnant woman under PMMVY 2.0?",
        "The minimum age of the pregnant woman must be at least 19 years at the time of conception.",
        "SUPPORTED",
    ),
    (
        "pmmvy",
        "PMMVY_05",
        "What is the total cash maternity benefit for the first living child under PMMVY 2.0?",
        "Under PMMVY 2.0, eligible pregnant women receive a total cash maternity benefit of Rs. 10,000 for the first living child.",
        "CONTRADICTED",
    ),
    (
        "pmmvy",
        "PMMVY_06",
        "What is the minimum age requirement for a pregnant woman under PMMVY 2.0?",
        "The minimum age of the pregnant woman must be at least 25 years at the time of conception.",
        "CONTRADICTED",
    ),
    (
        "pmmvy",
        "PMMVY_07",
        "What is the benefit amount for the second instalment of the first child under PMMVY 2.0?",
        "Under PMMVY 2.0, the Second Instalment after childbirth registration provides a benefit amount of Rs. 3,000.",
        "WRONG_CONTEXT",
    ),
    (
        "pmmvy",
        "PMMVY_08",
        "Do income tax payers and regular government employees receive the Rs. 5,000 maternity benefit?",
        "Regular government employees and income tax payers receive the Rs. 5,000 cash maternity benefit under PMMVY 2.0.",
        "WRONG_CONTEXT",
    ),
    (
        "pmmvy",
        "PMMVY_09",
        "What is the hospital bed per diem reimbursement rate under PMMVY 2.0?",
        "Empanelled private nursing homes receive Rs. 4,500 per square metre for maternity ward construction.",
        "UNVERIFIABLE",
    ),
    (
        "pmmvy",
        "PMMVY_10",
        "How many kilogrammes of fortified rice are distributed under PMMVY 2.0?",
        "Pregnant women receive 50 quintals of fortified wheat every week under PMMVY 2.0.",
        "UNVERIFIABLE",
    ),
    # =========================================================================
    # 6. Adversarial & Omitted-Restriction Cases (None may return SUPPORTED)
    # =========================================================================
    (
        "drone_2026",
        "ADV_01_REGRESSION_BOTH_OMITTED",
        "What is the subsidy percentage?",
        "Eligible farmers receive 50 percent assistance for purchasing drones.",
        "UNVERIFIABLE",
    ),
    (
        "drone_2026",
        "ADV_02_OMITTED_BENEFICIARY_RESTRICTION",
        "What is the financial assistance for purchasing agricultural drones?",
        "Individual farmers receive financial assistance of 50 percent or up to Rs 500000 for purchasing agricultural drones.",
        "UNVERIFIABLE",
    ),
    (
        "drone_2026",
        "ADV_03_OMITTED_CAP",
        "What is the financial assistance for SC/ST and women farmers purchasing drones?",
        "Individual farmers from SC/ST and women categories receive financial assistance of 50 percent for purchasing agricultural drones.",
        "UNVERIFIABLE",
    ),
    (
        "nlm_table",
        "ADV_04_OMITTED_GEOGRAPHY",
        "What capital subsidy rate do SC/ST entrepreneurs receive under NLM?",
        "Under NLM breed development norms, SC/ST entrepreneurs receive a 60% capital subsidy.",
        "UNVERIFIABLE",
    ),
    (
        "pm_svanidhi",
        "ADV_05_OMITTED_FREQUENCY",
        "What interest subvention rate is provided under PM SVANidhi?",
        "Street vendors availing working capital loans under PM SVANidhi receive an interest subvention of 7%.",
        "UNVERIFIABLE",
    ),
    (
        "drone_2026",
        "ADV_06_WRONG_CATEGORY",
        "What financial assistance do general category farmers receive for purchasing drones?",
        "Individual farmers from general category receive financial assistance of 50 percent or up to Rs 500000 for purchasing agricultural drones.",
        "WRONG_CONTEXT",
    ),
    (
        "drone_2026",
        "ADV_07_NEGATION",
        "Do SC/ST and women farmers receive 50 percent drone assistance?",
        "Individual farmers from SC/ST and women categories do not receive financial assistance of 50 percent or up to Rs 500000 for purchasing agricultural drones.",
        "UNVERIFIABLE",
    ),
    (
        "pmmvy",
        "ADV_08_OMITTED_CONDITIONAL_RESTRICTION",
        "What is the maternity benefit for the second living child under PMMVY 2.0?",
        "For the second living child, eligible mothers receive a one-time maternity benefit of Rs. 6,000 in a single instalment after childbirth.",
        "UNVERIFIABLE",
    ),
]


@pytest.fixture(scope="module")
def upload_backends() -> dict[str, tuple[Any, Any, Any, Any]]:
    paths = ensure_upload_fixture_files()
    backends: dict[str, tuple[Any, Any, Any, Any]] = {}
    for doc_key, path in paths.items():
        raw_bytes = path.read_bytes()
        store, units, rules = process_uploaded_document(raw_bytes, path.name)
        retriever = build_all_retrievers(store)["hybrid"]
        verifier = FieldGuardVerifier(store)
        backends[doc_key] = (store, units, rules, (verifier, retriever))
    return backends


@pytest.mark.parametrize(
    "doc_key,claim_id,question,claim,expected_verdict",
    UPLOAD_GENERALIZATION_CASES,
    ids=[c[1] for c in UPLOAD_GENERALIZATION_CASES],
)
def test_upload_generalization_claim(
    upload_backends: dict[str, tuple[Any, Any, Any, Any]],
    doc_key: str,
    claim_id: str,
    question: str,
    claim: str,
    expected_verdict: str,
) -> None:
    store, units, rules, (verifier, retriever) = upload_backends[doc_key]
    assert len(units) >= 2, f"{doc_key} should have at least 2 extracted units"
    assert len(rules) >= 2, f"{doc_key} should have at least 2 candidate numerical rules"
    assert not store.trusted_rules, "Uploaded documents must never populate trusted_rules"

    ret_items = [r.to_dict() for r in retriever.retrieve(f"{question} {claim}", top_k=5)]
    pred = verifier.verify_claim(claim_id, question, claim, ret_items)

    assert pred.verification_scope == "uploaded_document_only"
    if claim_id.startswith("ADV_"):
        assert pred.predicted_verdict != "SUPPORTED", (
            f"Adversarial case {claim_id} must never return SUPPORTED; got {pred.predicted_verdict}"
        )
    assert pred.predicted_verdict == expected_verdict, (
        f"[{claim_id}] Expected {expected_verdict}, got {pred.predicted_verdict}. "
        f"Reason: {pred.verification_rationale} (code={pred.verdict_reason_code})"
    )
    if expected_verdict in ("SUPPORTED", "CONTRADICTED", "WRONG_CONTEXT"):
        assert pred.matched_passage is not None
        assert pred.matched_candidate_rule is not None
        assert pred.matched_page is not None
        assert pred.matched_score is not None and pred.matched_score > 0.0
    else:
        assert pred.abstention_reason in (
            "no_relevant_passage",
            "unit_mismatch",
            "conflicting_values",
            "unestablished_condition",
            "no_numeric_claim",
            "omitted_beneficiary_restriction",
            "omitted_cap",
            "omitted_geography_restriction",
            "omitted_frequency_restriction",
            "omitted_basis_restriction",
            "omitted_qualifier",
            "omitted_restriction",
        )


def test_upload_corpus_accuracy_and_fsr_summary(
    upload_backends: dict[str, tuple[Any, Any, Any, Any]],
) -> None:
    """Compute, print, and assert per-class counts, accuracy, and False-Support Rate on the 58-claim upload corpus."""
    per_doc_stats: dict[str, dict[str, int]] = {}
    gold_class_counts: dict[str, int] = {"SUPPORTED": 0, "CONTRADICTED": 0, "WRONG_CONTEXT": 0, "UNVERIFIABLE": 0}
    pred_class_counts: dict[str, int] = {"SUPPORTED": 0, "CONTRADICTED": 0, "WRONG_CONTEXT": 0, "UNVERIFIABLE": 0}
    correct_by_class: dict[str, int] = {"SUPPORTED": 0, "CONTRADICTED": 0, "WRONG_CONTEXT": 0, "UNVERIFIABLE": 0}
    total_correct = 0
    total_claims = len(UPLOAD_GENERALIZATION_CASES)
    non_supported_gold = 0
    false_supports = 0
    adv_counted = 0

    for doc_key, claim_id, question, claim, expected in UPLOAD_GENERALIZATION_CASES:
        _, _, _, (verifier, retriever) = upload_backends[doc_key]
        ret_items = [r.to_dict() for r in retriever.retrieve(f"{question} {claim}", top_k=5)]
        pred = verifier.verify_claim(claim_id, question, claim, ret_items)

        if claim_id.startswith("ADV_"):
            adv_counted += 1

        gold_class_counts[expected] = gold_class_counts.get(expected, 0) + 1
        pred_class_counts[pred.predicted_verdict] = pred_class_counts.get(pred.predicted_verdict, 0) + 1

        stats = per_doc_stats.setdefault(doc_key, {"total": 0, "correct": 0, "non_sup": 0, "false_sup": 0})
        stats["total"] += 1
        if pred.predicted_verdict == expected:
            stats["correct"] += 1
            total_correct += 1
            correct_by_class[expected] = correct_by_class.get(expected, 0) + 1
        if expected != "SUPPORTED":
            stats["non_sup"] += 1
            non_supported_gold += 1
            if pred.predicted_verdict == "SUPPORTED":
                stats["false_sup"] += 1
                false_supports += 1

    overall_acc = total_correct / total_claims
    overall_fsr = false_supports / non_supported_gold if non_supported_gold else 0.0

    print("\n=== UPLOAD GENERALIZATION CORPUS SUMMARY ===")
    print(f"Total claims evaluated: {total_claims} (including {adv_counted} adversarial/regression cases)")
    print(f"Gold class counts:      {gold_class_counts}")
    print(f"Predicted class counts: {pred_class_counts}")
    print(f"Correct by class:       {correct_by_class}")
    print(f"Overall Accuracy:       {total_correct}/{total_claims} ({overall_acc:.2%})")
    print(f"False-Support Rate:     {false_supports}/{non_supported_gold} ({overall_fsr:.2%})")
    for doc_key, st in per_doc_stats.items():
        doc_acc = st["correct"] / st["total"]
        print(f"  - {doc_key}: {st['correct']}/{st['total']} ({doc_acc:.2%}), false_supports={st['false_sup']}/{st['non_sup']}")
        assert doc_acc >= 0.85, f"Upload accuracy on {doc_key} too low: {doc_acc:.2%}"

    assert adv_counted == 8, "All 8 adversarial and regression cases must be counted in summary"
    assert overall_acc >= 0.90, f"Overall upload corpus accuracy too low: {overall_acc:.2%}"
    assert overall_fsr == 0.0, f"Upload False-Support Rate must be 0%, got {overall_fsr:.2%}"
