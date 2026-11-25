"""Curated demonstration scenarios; not a held-out benchmark."""

SCHEME_SCENARIOS = {
    "PMFBY": {
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
    },
    "PM_KISAN": {
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
    },
    "MGNREGA": {
        "1. Supported: 100 Days Guaranteed Wage Employment": (
            "How many days of guaranteed wage employment are provided to rural households under MGNREGS?",
            "Under MGNREGS, every rural household whose adult members volunteer for unskilled manual work is guaranteed 100 days of wage employment per financial year.",
        ),
        "2. Supported: 15-Day Work Allocation Deadline": (
            "Within how many days must employment be provided to an applicant under MGNREGS?",
            "Under MGNREGS, work must be provided within 15 days of application, failing which daily unemployment allowance is payable.",
        ),
        "3. Wrong Context: 100 Days Claimed for Urban Industrial Households": (
            "Are urban industrial households entitled to 100 days guaranteed work under MGNREGS?",
            "Urban industrial households receive 100 days of guaranteed wage employment under MGNREGS.",
        ),
    },
    "PM_JAY": {
        "1. Supported: Rs 5 Lakh Annual Health Cover Per Family": (
            "What is the annual health cover provided to eligible families under Ayushman Bharat PM-JAY?",
            "Ayushman Bharat PM-JAY provides an annual health cover of Rs 500000 per eligible family for secondary and tertiary care hospitalisation.",
        ),
        "2. Supported: 100% Cashless Treatment with No Family Size Cap": (
            "Are benefits under Ayushman Bharat PM-JAY cashless?",
            "Treatment under Ayushman Bharat PM-JAY is 100 percent cashless across empanelled public and private hospitals with no cap on family size.",
        ),
        "3. Contradicted: Claiming Rs 10 Lakh Annual Cover": (
            "What is the maximum annual coverage under Ayushman Bharat PM-JAY?",
            "Ayushman Bharat PM-JAY provides an annual health cover of Rs 1000000 per family.",
        ),
    },
    "PMAY_G": {
        "1. Supported: Plain Areas Unit Assistance (Rs 1,20,000)": (
            "What is the unit assistance provided for house construction in plain areas under PMAY-G?",
            "Under PMAY-G, beneficiaries in plain areas receive unit grant assistance of Rs 120000.",
        ),
        "2. Supported: Hilly Areas Unit Assistance (Rs 1,30,000)": (
            "What is the unit assistance for hilly and difficult areas under PMAY-G?",
            "Under PMAY-G, beneficiaries in hilly states and difficult areas receive unit grant assistance of Rs 130000.",
        ),
        "3. Supported: Minimum Floor Area of 25 Sq. Metres": (
            "What is the minimum floor area prescribed for a house under PMAY-G?",
            "Under PMAY-G, the minimum floor area of the house is 25 sq. metres including a hygienic cooking space.",
        ),
    },
    "PM_KUSUM": {
        "1. Supported: 60% Total Capital Subsidy (30% Centre + 30% State)": (
            "What is the subsidy percentage provided for standalone solar pumps under PM-KUSUM Component-B?",
            "Under PM-KUSUM Component-B, farmers receive a total capital subsidy of 60 percent for standalone solar agriculture pumps.",
        ),
        "2. Supported: 30% Central Financial Assistance (CFA)": (
            "What is the Central Government share of subsidy under PM-KUSUM Component-B?",
            "Under PM-KUSUM, Central Financial Assistance (CFA) provides 30 percent of the benchmark pump cost.",
        ),
    },
    "PMMY": {
        "1. Supported: Shishu Loan Limit up to Rs 50,000": (
            "What is the maximum loan limit under the Shishu category of Pradhan Mantri Mudra Yojana?",
            "Under the Shishu category of Pradhan Mantri Mudra Yojana (PMMY), loans are sanctioned up to Rs 50000 without collateral.",
        ),
        "2. Contradicted: Claiming Rs 1,00,000 under Shishu Category": (
            "What is the maximum loan limit under the Shishu category of PMMY?",
            "Under the Shishu category of Mudra Yojana, entrepreneurs can avail loans up to Rs 100000.",
        ),
    },
}
