"""Generalization test suite for all 7 curated flagship schemes (Problem 1, Step 6).

Tests 12 NEW non-benchmark, non-demo claims per scheme (84 claims total across
MGNREGA, PM_JAY, PMAY_G, PM_KUSUM, PMMY, PM_KISAN, and PMFBY), covering:
- SUPPORTED (including free-form claims, omitted scheme names, and non-demo rules)
- CONTRADICTED (wrong numerical value under identical conditions)
- WRONG_CONTEXT (valid document number applied to wrong category, geography, frequency, period, or era)
- UNVERIFIABLE (genuinely unaddressed parameters not covered by the source evidence)
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pytest

from fieldguard.evaluation.runner import build_all_retrievers
from fieldguard.evidence_store import (
    EvidenceStore,
    build_default_evidence_store,
    build_pm_kisan_evidence_store,
)
from fieldguard.flagship_schemes_data import build_flagship_scheme_evidence_store
from fieldguard.verdicts import Verdict
from fieldguard.verifier import FieldGuardVerifier

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# 12 new claims per scheme (84 total), none from demo_scenarios.py or benchmark files.
GENERALIZATION_CLAIMS: dict[str, list[dict[str, Any]]] = {
    "MGNREGA": [
        {
            "id": "MGNREGA_GEN_01",
            "question": "",
            "claim": "Under MGNREGS wages must be paid within 15 days of the closure of the muster roll.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "MGNREGA_GEN_02",
            "question": "What is the daily compensation rate for delayed wage payments?",
            "claim": "Workers are entitled to delayed wage compensation at 0.05% per day of unpaid wages beyond 15 days of muster roll closure.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "MGNREGA_GEN_03",
            "question": "What is the minimum share of women beneficiaries in MGNREGA works?",
            "claim": "At least one-third (33.33%) of the beneficiaries given employment under MGNREGA must be women.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "MGNREGA_GEN_04",
            "question": "How much ex-gratia compensation is paid for accidental death at an MGNREGA worksite?",
            "claim": "In case of accidental death or permanent disability at a worksite, ex-gratia compensation of Rs 25,000 is payable.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "MGNREGA_GEN_05",
            "question": "How many days of guaranteed work are provided to Scheduled Tribe households with FRA titles?",
            "claim": "Scheduled Tribe households with Forest Rights Act (FRA) land titles are eligible for 150 days of guaranteed employment per financial year.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "MGNREGA_GEN_06",
            "question": "Within how many days must a Job Card be issued after registration under MGNREGA?",
            "claim": "Gram Panchayats must issue a Job Card within 45 days of registration application under MGNREGA.",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "MGNREGA_GEN_07",
            "question": "What is the maximum administrative expense ceiling under MGNREGA?",
            "claim": "Administrative expenses under MGNREGA are permitted up to 15% of total annual scheme expenditure.",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "MGNREGA_GEN_08",
            "question": "How often must the Gram Sabha conduct a social audit of MGNREGA works?",
            "claim": "Mandatory social audit of MGNREGA projects by the Gram Sabha is required once every 24 months.",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "MGNREGA_GEN_09",
            "question": "What is the unemployment allowance rate for the first 30 days under MGNREGA?",
            "claim": "Under MGNREGA, the unemployment allowance for the first 30 days is 50% of the daily wage rate.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "MGNREGA_GEN_10",
            "question": "What is the unemployment allowance rate after the first 30 days under MGNREGA?",
            "claim": "After the first 30 days of non-allocation of work under MGNREGA, the unemployment allowance is 25% of the wage rate.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "MGNREGA_GEN_11",
            "question": "What is the standard guaranteed employment entitlement for general rural households in non-drought plains?",
            "claim": "Every general rural household in non-drought areas is guaranteed 150 days of wage employment per year under MGNREGA.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "MGNREGA_GEN_12",
            "question": "What is the smartphone purchase grant provided to MGNREGA workers?",
            "claim": "Under MGNREGA, registered workers receive a smartphone subsidy of Rs 8,000 for attendance tracking.",
            "expected": Verdict.UNVERIFIABLE.value,
        },
    ],
    "PM_JAY": [
        {
            "id": "PMJAY_GEN_01",
            "question": "",
            "claim": "Under Ayushman Bharat PM-JAY, pre-hospitalisation medical expenses are covered for up to 3 days prior to admission.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMJAY_GEN_02",
            "question": "How many days of post-hospitalisation follow-up expenses are covered?",
            "claim": "Post-hospitalisation follow-up and medication costs are covered for 15 days after discharge.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMJAY_GEN_03",
            "question": "What is the minimum age for universal senior citizen health cover under Ayushman Vay Vandana?",
            "claim": "Senior citizens aged 70 years and above receive universal health coverage under the PM-JAY expansion.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMJAY_GEN_04",
            "question": "What is the turnaround time for deciding hospital pre-authorization requests under PM-JAY?",
            "claim": "Hospital pre-authorization requests under PM-JAY must be decided within 6 hours.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMJAY_GEN_05",
            "question": "What is the minimum bed capacity required for general private hospital empanelment under PM-JAY?",
            "claim": "General private hospitals require a minimum of 10 beds to qualify for empanelment under PM-JAY.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMJAY_GEN_06",
            "question": "How many Health Benefit Packages are covered under PM-JAY?",
            "claim": "The PM-JAY National Health Benefit Package master schedule covers only 500 procedures.",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "PMJAY_GEN_07",
            "question": "What is the penal interest rate for delayed hospital claim settlement under PM-JAY?",
            "claim": "Under PM-JAY, delayed hospital claim settlement attracts penal interest of 5% per week.",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "PMJAY_GEN_08",
            "question": "After how many hours is an undecided pre-authorization request deemed auto-approved under PM-JAY?",
            "claim": "An undecided pre-authorization request under PM-JAY is deemed auto-approved after 72 hours.",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "PMJAY_GEN_09",
            "question": "How many days of pre-hospitalisation diagnostics are covered before admission under PM-JAY?",
            "claim": "Under PM-JAY, pre-hospitalisation expenses are covered for 15 days prior to hospital admission.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "PMJAY_GEN_10",
            "question": "What is the Central Government share of PM-JAY premium funding in general states?",
            "claim": "In general states, the Central Government bears 90% of the premium funding under PM-JAY.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "PMJAY_GEN_11",
            "question": "Within how many days must intra-state hospital claims be settled under PM-JAY?",
            "claim": "Intra-state hospital claims within the same state under PM-JAY have a standard settlement turnaround time of 30 days.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "PMJAY_GEN_12",
            "question": "What is the monthly overseas medical travel allowance under PM-JAY?",
            "claim": "Under PM-JAY, patients travelling abroad for surgery receive an international airfare allowance of Rs 1,50,000.",
            "expected": Verdict.UNVERIFIABLE.value,
        },
    ],
    "PMAY_G": [
        {
            "id": "PMAYG_GEN_01",
            "question": "",
            "claim": "Under PMAY-G, financial assistance of Rs 12,000 is provided for household toilet construction in convergence with SBM-G.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMAYG_GEN_02",
            "question": "What is the maximum optional institutional loan facilitated for a PMAY-G beneficiary?",
            "claim": "Beneficiaries can avail an optional institutional loan of up to Rs 70,000 from banks for house construction.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMAYG_GEN_03",
            "question": "What interest subvention is offered on optional bank loans under PMAY-G?",
            "claim": "Under PMAY-G, optional housing loans up to Rs 70,000 carry an interest subvention of 3% per annum.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMAYG_GEN_04",
            "question": "Within how many months must house construction be completed under PMAY-G?",
            "claim": "House construction under PMAY-G must be completed within 12 months from the sanction of the first instalment.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMAYG_GEN_05",
            "question": "What percentage of PMAY-G targets is earmarked for SC/ST households?",
            "claim": "At least 60% of the housing targets under PMAY-G are earmarked for SC/ST households.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMAYG_GEN_06",
            "question": "What is the horizontal reservation percentage for Persons with Disabilities under PMAY-G?",
            "claim": "Under PMAY-G, 25% of housing targets are reserved horizontally for Persons with Disabilities (PwD).",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "PMAYG_GEN_07",
            "question": "What is the ceiling on administrative funds under PMAY-G?",
            "claim": "Up to 10% of programme funds under PMAY-G can be spent on administrative expenses.",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "PMAYG_GEN_08",
            "question": "What is the unit assistance for house construction in plain areas under PMAY-G?",
            "claim": "Under PMAY-G, beneficiaries in plain areas receive unit grant assistance of Rs 2,50,000.",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "PMAYG_GEN_09",
            "question": "What is the unit grant assistance for PMAY-G beneficiaries in plain areas?",
            "claim": "Under PMAY-G, beneficiaries in plain areas receive unit grant assistance of Rs 1,30,000.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "PMAYG_GEN_10",
            "question": "What is the minimum floor area prescribed for a house under current PMAY-G guidelines?",
            "claim": "Under PMAY-G, the minimum prescribed house floor area is 20 sq. metres.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "PMAYG_GEN_11",
            "question": "What is the Central Government funding share for PMAY-G in plain areas?",
            "claim": "In plain areas, the Central Government bears 90% of the PMAY-G unit assistance cost.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "PMAYG_GEN_12",
            "question": "What is the rooftop air-conditioner subsidy provided under PMAY-G?",
            "claim": "Under PMAY-G, households receive a solar air-conditioner voucher of Rs 35,000 upon completion.",
            "expected": Verdict.UNVERIFIABLE.value,
        },
    ],
    "PM_KUSUM": [
        {
            "id": "PMKUSUM_GEN_01",
            "question": "",
            "claim": "Under PM-KUSUM, individual farmers are eligible for standalone solar pumps up to 7.5 HP capacity.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMKUSUM_GEN_02",
            "question": "What is the Central Financial Assistance percentage for PM-KUSUM in North-Eastern and hilly states?",
            "claim": "In North-Eastern and hilly states, Central Financial Assistance (CFA) under PM-KUSUM is 50% of the benchmark cost.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMKUSUM_GEN_03",
            "question": "What is the DISCOM Performance Based Incentive rate per kWh under PM-KUSUM Component-A?",
            "claim": "Under PM-KUSUM Component-A, DISCOMs receive a Performance Based Incentive (PBI) of Rs 0.40 per kWh.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMKUSUM_GEN_04",
            "question": "What is the mandatory vendor Comprehensive Maintenance Contract duration under PM-KUSUM?",
            "claim": "System vendors under PM-KUSUM must provide a mandatory Comprehensive Maintenance Contract (CMC) for 5 years.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMKUSUM_GEN_05",
            "question": "Within what radius of a distribution substation must Component-A solar plants be located?",
            "claim": "Decentralized solar power plants under PM-KUSUM Component-A must be located within a 5 km radius of the substation.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMKUSUM_GEN_06",
            "question": "What is the national cumulative solar capacity target under PM-KUSUM Component-A?",
            "claim": "PM-KUSUM Component-A targets a national cumulative capacity of 50,000 MW of decentralized solar plants.",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "PMKUSUM_GEN_07",
            "question": "What is the upfront farmer margin when availing a 30% bank loan under PM-KUSUM in general states?",
            "claim": "When availing a 30% bank loan in general states under PM-KUSUM, the farmer must pay an upfront margin of 35%.",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "PMKUSUM_GEN_08",
            "question": "What is the annual cap per MW on DISCOM Performance Based Incentive under PM-KUSUM?",
            "claim": "The annual DISCOM Performance Based Incentive under PM-KUSUM Component-A is capped at Rs 15,00,000 per MW.",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "PMKUSUM_GEN_09",
            "question": "What is the maximum solar pump capacity eligible for CFA for an individual farmer under PM-KUSUM?",
            "claim": "Under PM-KUSUM, individual farmers are eligible for Central Financial Assistance on solar pumps up to 15 HP.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "PMKUSUM_GEN_10",
            "question": "What is the Central Financial Assistance rate for solar pumps in general states under PM-KUSUM?",
            "claim": "In general states, Central Financial Assistance (CFA) under PM-KUSUM is 50% of the benchmark pump cost.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "PMKUSUM_GEN_11",
            "question": "What is the total combined government subsidy for solar pumps in general states under PM-KUSUM?",
            "claim": "In general states, the combined Central and State government subsidy under PM-KUSUM is 80% of the pump cost.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "PMKUSUM_GEN_12",
            "question": "What is the electric tractor battery replacement subsidy under PM-KUSUM?",
            "claim": "Under PM-KUSUM, farmers receive a lithium battery replacement grant of Rs 90,000 every three years.",
            "expected": Verdict.UNVERIFIABLE.value,
        },
    ],
    "PMMY": [
        {
            "id": "PMMY_GEN_01",
            "question": "",
            "claim": "Under PMMY, Kishore category loans cover credit limits above Rs 50,000 and up to Rs 5,00,000.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMMY_GEN_02",
            "question": "What is the maximum loan limit under the Tarun Plus category of PMMY?",
            "claim": "Under the Tarun Plus category of PMMY, repeat borrowers who repaid previous Tarun loans can avail up to Rs 20,00,000.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMMY_GEN_03",
            "question": "What is the processing fee charged on Shishu loans under PMMY?",
            "claim": "Banks charge 0% upfront processing fee on Shishu category loans under PMMY.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMMY_GEN_04",
            "question": "What is the portfolio credit guarantee cover percentage under CGFMU for PMMY loans?",
            "claim": "Under CGFMU, eligible PMMY loans receive a credit guarantee cover of up to 75% of the amount in default.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMMY_GEN_05",
            "question": "What minimum share of the total PMMY credit corpus is earmarked for Shishu loans?",
            "claim": "At least 60% of the total PMMY credit corpus must be earmarked for Shishu category units.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMMY_GEN_06",
            "question": "What is the interest subvention rate for prompt repayment of Shishu loans under PMMY?",
            "claim": "Prompt repayment of Shishu loans under PMMY receives an interest subvention of 8% per annum.",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "PMMY_GEN_07",
            "question": "What is the minimum eligible age for an individual borrower under PMMY?",
            "claim": "Individual applicants must be at least 25 years of age to apply for a MUDRA loan under PMMY.",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "PMMY_GEN_08",
            "question": "What is the first-loss portfolio default percentage borne by the lending institution under CGFMU?",
            "claim": "Under CGFMU, the first 15% of the crystallized portfolio default is borne entirely by the lending institution.",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "PMMY_GEN_09",
            "question": "What is the maximum loan limit under the Shishu category of PMMY?",
            "claim": "Under the Shishu category of PMMY, loans are sanctioned up to Rs 5,00,000.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "PMMY_GEN_10",
            "question": "What is the maximum loan limit under the Kishore category of PMMY?",
            "claim": "Under the Kishore category of PMMY, the maximum loan limit is Rs 10,00,000.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "PMMY_GEN_11",
            "question": "Can a first-time new borrower avail Rs 20,00,000 under Tarun Plus in PMMY?",
            "claim": "First-time new borrowers without prior credit history can avail Rs 20,00,000 under the Tarun Plus category of PMMY.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "PMMY_GEN_12",
            "question": "What is the export freight reimbursement percentage provided under PMMY?",
            "claim": "Under PMMY, micro-enterprises exporting handicrafts receive a 40% sea-freight reimbursement.",
            "expected": Verdict.UNVERIFIABLE.value,
        },
    ],
    "PM_KISAN": [
        {
            "id": "PMKISAN_GEN_01",
            "question": "",
            "claim": "Under PM-KISAN, the annual support of Rs 6,000 is disbursed in 3 equal instalments per financial year.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMKISAN_GEN_02",
            "question": "Every how many months is an instalment released under PM-KISAN?",
            "claim": "Instalments under PM-KISAN are released every 4 months during the financial year.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMKISAN_GEN_03",
            "question": "What is the monthly pension threshold above which pensioners are excluded from PM-KISAN?",
            "claim": "Superannuated pensioners receiving a monthly pension of Rs 10,000 or more are excluded from PM-KISAN.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMKISAN_GEN_04",
            "question": "What percentage of PM-KISAN financial benefits are transferred electronically through the Aadhaar Payment Bridge System (APBS)?",
            "claim": "Financial benefits under PM-KISAN are transferred 100% electronically through the Aadhaar Payment Bridge System (APBS) into Aadhaar-seeded bank accounts.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMKISAN_GEN_05",
            "question": "What was the landholding eligibility ceiling under the original February 2019 launch guidelines of PM-KISAN?",
            "claim": "Under the original February 2019 launch guidelines of PM-KISAN, eligibility was capped at 2.0 hectares of cultivable land.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMKISAN_GEN_06",
            "question": "What is the four-monthly instalment amount paid to eligible farmer families under PM-KISAN?",
            "claim": "Under PM-KISAN, each four-monthly instalment is Rs 4,000 per eligible landholding farmer family.",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "PMKISAN_GEN_07",
            "question": "What is the monthly pension threshold for exclusion of pensioners under PM-KISAN?",
            "claim": "Pensioners are excluded from PM-KISAN only if their monthly pension is Rs 25,000 or more.",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "PMKISAN_GEN_08",
            "question": "What percentage of PM-KISAN financial benefits are transferred electronically via the Aadhaar Payment Bridge System (APBS)?",
            "claim": "Under PM-KISAN, only 50% of financial benefits are transferred electronically through the Aadhaar Payment Bridge System (APBS).",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "PMKISAN_GEN_09",
            "question": "What is the annual financial benefit under PM-KISAN for eligible landholding farmer families?",
            "claim": "Under PM-KISAN, eligible landholding farmer families receive a total of Rs 2,000 per year.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "PMKISAN_GEN_10",
            "question": "Are income tax payees eligible for Rs 6,000 annual support under PM-KISAN?",
            "claim": "Farmers who paid income tax in the last assessment year receive Rs 6,000 per year under PM-KISAN.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "PMKISAN_GEN_11",
            "question": "Are landless agricultural labourers entitled to Rs 2,000 per instalment under PM-KISAN?",
            "claim": "Landless agricultural labourers receive Rs 2,000 per instalment under PM-KISAN.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "PMKISAN_GEN_12",
            "question": "What is the cold-storage rental subsidy provided to farmers under PM-KISAN?",
            "claim": "Under PM-KISAN, farmers receive a cold-storage warehouse subsidy of Rs 18,000 per season.",
            "expected": Verdict.UNVERIFIABLE.value,
        },
    ],
    "PMFBY": [
        {
            "id": "PMFBY_GEN_01",
            "question": "",
            "claim": "Under the 2023 PMFBY operational guidelines, post-harvest losses are covered for up to 14 days from harvesting for crops left in cut-and-spread condition.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMFBY_GEN_02",
            "question": "Within how many hours must a farmer intimate localized crop loss under the 2023 PMFBY guidelines?",
            "claim": "Under the 2023 PMFBY operational guidelines, farmers must intimate localized peril losses within 72 hours of occurrence.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMFBY_GEN_03",
            "question": "What is the maximum on-account relief for mid-season adversity under the 2023 PMFBY guidelines?",
            "claim": "Under the 2023 PMFBY operational guidelines, mid-season adversity relief provides on-account payment up to 25% of likely claims.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMFBY_GEN_04",
            "question": "How many days prior to the enrolment cut-off date must a loanee farmer submit a declaration to opt out of PMFBY?",
            "claim": "Under the 2023 PMFBY operational guidelines, a loanee farmer must submit a written opt-out declaration at least 7 days prior to the enrolment cut-off date.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMFBY_GEN_05",
            "question": "What is the penal interest rate for delayed claim settlement by insurance companies under the 2023 PMFBY guidelines?",
            "claim": "Under the 2023 PMFBY operational guidelines, insurance companies must pay 12% per annum penal interest on delayed claim settlements.",
            "expected": Verdict.SUPPORTED.value,
        },
        {
            "id": "PMFBY_GEN_06",
            "question": "How many best years out of the preceding 7 years are used to calculate Threshold Yield under the 2023 PMFBY guidelines?",
            "claim": "Under the 2023 PMFBY operational guidelines, Threshold Yield is calculated as the average yield of the best 3 years out of the preceding 7 years.",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "PMFBY_GEN_07",
            "question": "Within how many days of the enrolment cut-off must banks upload crop insurance proposals on the NCIP portal under PMFBY?",
            "claim": "Under the 2023 PMFBY operational guidelines, banks have 45 days after the enrolment cut-off date to upload farmer details on the portal.",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "PMFBY_GEN_08",
            "question": "What percentage of gross premium is earmarked for IEC and administrative expenses under the 2023 PMFBY guidelines?",
            "claim": "Under the 2023 PMFBY operational guidelines, 8.0% of gross premium is earmarked for IEC and administrative expenses.",
            "expected": Verdict.CONTRADICTED.value,
        },
        {
            "id": "PMFBY_GEN_09",
            "question": "Under the 2023 PMFBY operational guidelines, what is the Central Government's share of normal premium subsidy in North-Eastern States?",
            "claim": "Under the 2023 PMFBY operational guidelines, the Central Government's share of normal premium subsidy in North-Eastern States is 50%.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "PMFBY_GEN_10",
            "question": "Under the 2023 PMFBY operational guidelines, what is the actuarial premium rate cap for Central subsidy in unirrigated areas?",
            "claim": "Under the 2023 PMFBY operational guidelines, Central Government premium subsidy for unirrigated areas is capped at an actuarial rate of 25%.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "PMFBY_GEN_11",
            "question": "Under the 2023 PMFBY operational guidelines, what is the maximum farmer premium for annual commercial and horticultural crops?",
            "claim": "Under the 2023 PMFBY operational guidelines, the maximum farmer premium for annual commercial and horticultural crops is 1.5% of Sum Insured or actuarial rate, whichever is less.",
            "expected": Verdict.WRONG_CONTEXT.value,
        },
        {
            "id": "PMFBY_GEN_12",
            "question": "Under the 2023 PMFBY operational guidelines, what is the minimum export price guarantee for basmati rice?",
            "claim": "Under the 2023 PMFBY operational guidelines, farmers exporting basmati rice are guaranteed a minimum export price of Rs 85,000 per tonne.",
            "expected": Verdict.UNVERIFIABLE.value,
        },
    ],
}


def _get_scheme_store(scheme: str) -> EvidenceStore:
    if scheme == "PMFBY":
        return build_default_evidence_store(PROJECT_ROOT)
    if scheme == "PM_KISAN":
        return build_pm_kisan_evidence_store(PROJECT_ROOT)
    return build_flagship_scheme_evidence_store(scheme)


@pytest.fixture(scope="module")
def scheme_verifiers() -> dict[str, tuple[FieldGuardVerifier, dict[str, Any]]]:
    out: dict[str, tuple[FieldGuardVerifier, dict[str, Any]]] = {}
    for scheme in GENERALIZATION_CLAIMS:
        store = _get_scheme_store(scheme)
        verifier = FieldGuardVerifier(evidence_store=store)
        retrievers = build_all_retrievers(store)
        out[scheme] = (verifier, retrievers)
    return out


@pytest.mark.parametrize(
    "scheme,case",
    [
        (scheme, case)
        for scheme, cases in GENERALIZATION_CLAIMS.items()
        for case in cases
    ],
    ids=[
        case["id"]
        for cases in GENERALIZATION_CLAIMS.values()
        for case in cases
    ],
)
def test_flagship_generalization_claim(
    scheme: str,
    case: dict[str, Any],
    scheme_verifiers: dict[str, tuple[FieldGuardVerifier, dict[str, Any]]],
) -> None:
    verifier, retrievers = scheme_verifiers[scheme]
    query = f"{case['question']} {case['claim']}".strip()
    ret_items = [r.to_dict() for r in retrievers["hybrid"].retrieve(query, top_k=5)]
    pred = verifier.verify_claim(
        claim_id=case["id"],
        question=case["question"],
        candidate_claim=case["claim"],
        retrieved_items=ret_items,
    )
    assert pred.predicted_verdict == case["expected"], (
        f"[{case['id']}] Expected {case['expected']} but got {pred.predicted_verdict}. "
        f"Parsed={pred.parsed_claim}, rationale={pred.verification_rationale}, "
        f"abstention_reason={pred.abstention_reason}"
    )
    if case["expected"] == Verdict.UNVERIFIABLE.value:
        assert pred.abstention_reason in (
            "no_rule_for_parameter",
            "parser_failed",
            "no_retrieved_evidence",
            "temporal_ambiguity",
        ), f"Expected diagnostic abstention_reason, got {pred.abstention_reason}"


def test_report_per_scheme_generalization_accuracy(
    scheme_verifiers: dict[str, tuple[FieldGuardVerifier, dict[str, Any]]],
) -> None:
    """Compute and save per-scheme generalization accuracy across all 7 schemes."""
    rows: list[dict[str, Any]] = []
    total_correct = 0
    total_claims = 0

    for scheme, cases in GENERALIZATION_CLAIMS.items():
        verifier, retrievers = scheme_verifiers[scheme]
        correct = 0
        for case in cases:
            query = f"{case['question']} {case['claim']}".strip()
            ret_items = [r.to_dict() for r in retrievers["hybrid"].retrieve(query, top_k=5)]
            pred = verifier.verify_claim(
                claim_id=case["id"],
                question=case["question"],
                candidate_claim=case["claim"],
                retrieved_items=ret_items,
            )
            if pred.predicted_verdict == case["expected"]:
                correct += 1
        acc = round(100.0 * correct / len(cases), 2)
        rows.append(
            {
                "scheme": scheme,
                "total_claims": len(cases),
                "correct": correct,
                "accuracy_pct": acc,
            }
        )
        total_correct += correct
        total_claims += len(cases)
        assert acc >= 90.0, f"Generalization accuracy for {scheme} too low: {acc}%"

    out_path = PROJECT_ROOT / "results" / "tables" / "flagship_generalization_summary.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["scheme", "total_claims", "correct", "accuracy_pct"])
        writer.writeheader()
        writer.writerows(rows)
        writer.writerow(
            {
                "scheme": "ALL_7_SCHEMES",
                "total_claims": total_claims,
                "correct": total_correct,
                "accuracy_pct": round(100.0 * total_correct / total_claims, 2),
            }
        )
