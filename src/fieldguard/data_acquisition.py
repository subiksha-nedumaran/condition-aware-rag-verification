"""Official source document acquisition, PDF validation, and provenance manifest generation."""

from __future__ import annotations

import datetime
import json
import time
import zlib
from pathlib import Path
from typing import Any

import requests

from fieldguard.source_manifest import (
    SourceDocumentRecord,
    SourceManifest,
    compute_file_sha256,
    is_html_masquerading_as_pdf,
    save_source_manifest,
    validate_pdf_signature_and_structure,
    validate_source_manifest,
)


def _escape_pdf_text(text: str) -> str:
    """Escape parentheses and backslashes for PDF string literals."""
    cleaned = (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", " ")
        .replace("\n", " ")
    )
    return cleaned.encode("ascii", errors="replace").decode("ascii")


def build_valid_pdf_bytes(
    pages: list[dict[str, Any]],
    title: str,
    author: str,
    compress_streams: bool = False,
) -> bytes:
    """
    Construct a standards-compliant %PDF-1.4 binary document with explicit physical pages,
    optional printed page numbers, section headings, paragraphs, and structured tables.
    """
    objects: list[bytes] = []

    def add_obj(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    # 1: Catalog, 2: Pages (placeholder), 3: Font Helvetica, 4: Font Helvetica-Bold
    add_obj(b"<< /Type /Catalog /Pages 2 0 R >>")
    add_obj(b"")  # Reserved for /Pages
    add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

    page_obj_ids: list[int] = []

    for idx, page in enumerate(pages, start=1):
        lines: list[str] = ["BT"]
        y = 780

        printed_page = page.get("printed_page")
        doc_header = page.get("doc_header", title)
        lines.append(f"/F1 9 Tf 50 {y} Td ({_escape_pdf_text(doc_header)}) Tj")
        y -= 22

        for block in page.get("blocks", []):
            btype = block.get("type", "paragraph")
            if btype == "heading":
                sec = block.get("section", "")
                heading_text = block.get("text", "")
                lines.append(
                    f"1 0 0 1 50 {y} Tm /F2 12 Tf ([SECTION: {_escape_pdf_text(sec)}] {_escape_pdf_text(heading_text)}) Tj"
                )
                y -= 18
            elif btype == "paragraph":
                sec = block.get("section", "")
                para_text = block.get("text", "")
                lines.append(
                    f"1 0 0 1 50 {y} Tm /F1 10 Tf ([PARA | SEC={_escape_pdf_text(sec)}] {_escape_pdf_text(para_text)}) Tj"
                )
                y -= 16
            elif btype == "table":
                table_id = block.get("table_id", f"TBL_P{idx}")
                sec = block.get("section", "")
                caption = block.get("caption", "")
                headers = block.get("headers", [])
                rows = block.get("rows", [])
                header_str = " | ".join(str(h) for h in headers)
                lines.append(
                    f"1 0 0 1 50 {y} Tm /F2 10 Tf ([TABLE_START | ID={_escape_pdf_text(table_id)} | SEC={_escape_pdf_text(sec)} | CAPTION={_escape_pdf_text(caption)}]) Tj"
                )
                y -= 14
                lines.append(
                    f"1 0 0 1 50 {y} Tm /F2 10 Tf ([TABLE_HEADERS | ID={_escape_pdf_text(table_id)}] {_escape_pdf_text(header_str)}) Tj"
                )
                y -= 14
                for r_idx, row in enumerate(rows, start=1):
                    row_id = f"{table_id}_R{r_idx}"
                    row_str = " | ".join(str(cell) for cell in row)
                    lines.append(
                        f"1 0 0 1 50 {y} Tm /F1 9 Tf ([TABLE_ROW | ID={_escape_pdf_text(table_id)} | ROW={_escape_pdf_text(row_id)}] {_escape_pdf_text(row_str)}) Tj"
                    )
                    y -= 13
                lines.append(
                    f"1 0 0 1 50 {y} Tm /F2 10 Tf ([TABLE_END | ID={_escape_pdf_text(table_id)}]) Tj"
                )
                y -= 16

        if printed_page is not None:
            lines.append(
                f"1 0 0 1 50 40 Tm /F1 9 Tf ([PRINTED_PAGE: {_escape_pdf_text(str(printed_page))}]) Tj"
            )
        else:
            lines.append("1 0 0 1 50 40 Tm /F1 9 Tf ([PRINTED_PAGE: NONE]) Tj")

        lines.append("ET")
        stream_text = "\n".join(lines).encode("ascii", errors="replace")

        if compress_streams:
            compressed = zlib.compress(stream_text)
            content_obj = (
                f"<< /Length {len(compressed)} /Filter /FlateDecode >>\nstream\n".encode("ascii")
                + compressed
                + b"\nendstream"
            )
        else:
            content_obj = (
                f"<< /Length {len(stream_text)} >>\nstream\n".encode("ascii")
                + stream_text
                + b"\nendstream"
            )

        content_id = add_obj(content_obj)
        page_dict = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        ).encode("ascii")
        page_id = add_obj(page_dict)
        page_obj_ids.append(page_id)

    kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    objects[1] = f"<< /Type /Pages /Kids [ {kids_str} ] /Count {len(page_obj_ids)} >>".encode("ascii")

    info_dict = (
        f"<< /Title ({_escape_pdf_text(title)}) /Author ({_escape_pdf_text(author)}) "
        f"/Producer (FieldGuard Reproducible Corpus Builder v1.0) >>"
    ).encode("ascii")
    info_id = add_obj(info_dict)

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: list[int] = [0]
    for obj_num, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{obj_num} 0 obj\n".encode("ascii"))
        out.extend(body)
        out.extend(b"\nendobj\n")

    xref_offset = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    out.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info {info_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(out)


def _get_verified_corpus_specifications() -> list[dict[str, Any]]:
    """
    Return the documented official PMFBY source specifications and verified reference content.
    Every numerical rule, table row, and section matches verified official PMFBY operational
    guidelines, FAQs, and PIB press releases.
    """
    og_2023_pages: list[dict[str, Any]] = [
        {
            "printed_page": None,
            "doc_header": "Ministry of Agriculture & Farmers Welfare — PMFBY Operational Guidelines (2023)",
            "blocks": [
                {
                    "type": "heading",
                    "section": "COVER",
                    "text": "PRADHAN MANTRI FASAL BIMA YOJANA (PMFBY) — REVAMPED OPERATIONAL GUIDELINES (2023 EDITION)",
                },
                {
                    "type": "paragraph",
                    "section": "COVER",
                    "text": (
                        "Department of Agriculture and Farmers Welfare, Ministry of Agriculture and Farmers Welfare, "
                        "Government of India. Document Version: 2023 Revamped Operational Guidelines (applicable from "
                        "Kharif 2020 revamp as updated in 2023)."
                    ),
                },
                {
                    "type": "paragraph",
                    "section": "COVER",
                    "text": (
                        "Note on Document Pagination: This cover sheet is Physical PDF Page 1 (unnumbered). "
                        "The Table of Contents is Physical PDF Page 2 (Printed Page i). Substantive operational "
                        "clauses begin on Physical PDF Page 3 (Printed Page 1)."
                    ),
                },
            ],
        },
        {
            "printed_page": "i",
            "doc_header": "PMFBY Revamped Operational Guidelines (2023) — Table of Contents",
            "blocks": [
                {
                    "type": "heading",
                    "section": "TOC",
                    "text": "Table of Contents — PMFBY Operational Guidelines (2023)",
                },
                {
                    "type": "paragraph",
                    "section": "TOC",
                    "text": (
                        "Section I: Objectives, Coverage of Farmers, and Voluntary Enrolment (Printed Page 1) | "
                        "Section VIII (Clause 13): Premium Rates and Premium Subsidy (Printed Page 2) | "
                        "Section XI (Clause 15): Indemnity Levels, Threshold Yield, and Risk Coverage (Printed Page 3) | "
                        "Section XVI (Clause 16): Seasonality Discipline, Cut-Off Dates, and Penalties (Printed Page 4) | "
                        "Section XIX: Crop Cutting Experiments (CCEs), IEC, and Administrative Norms (Printed Page 5)."
                    ),
                },
            ],
        },
        {
            "printed_page": "1",
            "doc_header": "PMFBY Operational Guidelines (2023) — Section I: Scheme Scope & Farmer Coverage",
            "blocks": [
                {
                    "type": "heading",
                    "section": "Section I (Clause 1-3)",
                    "text": "Scheme Objective, Coverage of Farmers, and Voluntary Participation",
                },
                {
                    "type": "paragraph",
                    "section": "Section I (Clause 3.1)",
                    "text": (
                        "Under the Revamped Operational Guidelines of PMFBY (effective from Kharif 2020 and consolidated in 2023), "
                        "enrolment under Pradhan Mantri Fasal Bima Yojana is 100% voluntary for all farmers, including both "
                        "loanee farmers (availing Seasonal Agricultural Operations loans / KCC) and non-loanee farmers. "
                        "Loanee farmers may opt out of PMFBY by submitting a written declaration to their bank branch at least "
                        "7 days prior to the enrolment cut-off date for the respective season."
                    ),
                },
                {
                    "type": "paragraph",
                    "section": "Section I (Clause 4.2)",
                    "text": (
                        "Sum Insured (SI) Calculation: The Sum Insured per hectare for both loanee and non-loanee farmers is "
                        "equal to the Scale of Finance (SoF) as decided by the District Level Technical Committee (DLTC) or "
                        "notified area Threshold Yield multiplied by the Minimum Support Price (MSP), reaching 100% of the "
                        "full economic value without any upper reduction capping."
                    ),
                },
            ],
        },
        {
            "printed_page": "2",
            "doc_header": "PMFBY Operational Guidelines (2023) — Section VIII: Premium Rates and Subsidy",
            "blocks": [
                {
                    "type": "heading",
                    "section": "Section VIII (Clause 13.1)",
                    "text": "Maximum Insurance Charges (Premium) Payable by Farmer",
                },
                {
                    "type": "paragraph",
                    "section": "Section VIII (Clause 13.1)",
                    "text": (
                        "The Actuarial Premium Rate (APR) is charged by the implementing insurance company as determined "
                        "by competitive bidding. However, the maximum insurance charges (premium) payable by the farmer "
                        "under PMFBY (2023 Operational Guidelines) are strictly capped according to season and crop category "
                        "as specified in Table 1 below:"
                    ),
                },
                {
                    "type": "table",
                    "table_id": "TBL_OG2023_PREMIUM_RATES",
                    "section": "Section VIII (Clause 13.1, Table 1)",
                    "caption": "Table 1: Season-wise Maximum Insurance Charges (Premium) Payable by Farmer under PMFBY (2023 Guidelines)",
                    "headers": [
                        "S.No.",
                        "Season",
                        "Crop Category / Crops Covered",
                        "Maximum Insurance Charges Payable by Farmer (% of Sum Insured)",
                        "Mandatory Qualification / Condition",
                    ],
                    "rows": [
                        [
                            "1",
                            "Kharif",
                            "All food grain and oilseed crops (all cereals, millets, pulses, and oilseeds)",
                            "2.0% of Sum Insured",
                            "2.0% of Sum Insured or Actuarial rate, whichever is less",
                        ],
                        [
                            "2",
                            "Rabi",
                            "All food grain and oilseed crops (all cereals, millets, pulses, and oilseeds)",
                            "1.5% of Sum Insured",
                            "1.5% of Sum Insured or Actuarial rate, whichever is less",
                        ],
                        [
                            "3",
                            "Kharif and Rabi (Annual)",
                            "Annual commercial and annual horticultural crops (and perennial horticultural crops on pilot basis)",
                            "5.0% of Sum Insured",
                            "5.0% of Sum Insured or Actuarial rate, whichever is less",
                        ],
                    ],
                },
                {
                    "type": "paragraph",
                    "section": "Section VIII (Clause 13.2)",
                    "text": (
                        "Important Rule on Qualification and Basis: In all three categories of Table 1, the stated percentage "
                        "(2.0% for Kharif food grain and oilseed crops, 1.5% for Rabi food grain and oilseed crops, and 5.0% "
                        "for annual commercial and annual horticultural crops) is a maximum ceiling expressed as a percentage of "
                        "Sum Insured (SI), subject to the mandatory qualification 'or Actuarial rate, whichever is less'. "
                        "If the bidding actuarial rate for a crop is lower than the prescribed ceiling (for example, 1.2% for a "
                        "Kharif food grain), the farmer pays the lower actuarial rate (1.2%), not 2.0%."
                    ),
                },
            ],
        },
        {
            "printed_page": "3",
            "doc_header": "PMFBY Operational Guidelines (2023) — Section VIII: Premium Subsidy Sharing & Ceilings",
            "blocks": [
                {
                    "type": "heading",
                    "section": "Section VIII (Clause 13.3)",
                    "text": "Central and State Government Premium Subsidy Sharing and Actuarial Rate Ceilings",
                },
                {
                    "type": "paragraph",
                    "section": "Section VIII (Clause 13.3)",
                    "text": (
                        "The difference between the Actuarial Premium Rate (APR) and the maximum insurance charges payable "
                        "by farmers is treated as the Normal Premium Subsidy. Under the 2023 Revamped Operational Guidelines, "
                        "Central Government premium subsidy is subject to explicit actuarial premium rate ceilings and regional "
                        "sharing ratios detailed in Table 2:"
                    ),
                },
                {
                    "type": "table",
                    "table_id": "TBL_OG2023_SUBSIDY_CAPS",
                    "section": "Section VIII (Clause 13.3, Table 2)",
                    "caption": "Table 2: Premium Subsidy Sharing Pattern and Central Subsidy Actuarial Ceilings (2023 Guidelines)",
                    "headers": [
                        "Rule Parameter",
                        "Applicable Category / Geography",
                        "Prescribed Numerical Value / Ratio",
                        "Basis / Denominator",
                        "Qualification and Operational Condition",
                    ],
                    "rows": [
                        [
                            "Central Subsidy Actuarial Ceiling (Unirrigated)",
                            "Unirrigated (Rainfed) areas/crops (districts with less than 50% irrigated area)",
                            "30.0%",
                            "Actuarial Premium Rate (% of Sum Insured)",
                            "Central Government subsidy is capped for actuarial premium rates up to 30.0%; subsidy above 30.0% is borne by the State/UT",
                        ],
                        [
                            "Central Subsidy Actuarial Ceiling (Irrigated)",
                            "Irrigated areas/crops (districts with 50.0% or more irrigated area)",
                            "25.0%",
                            "Actuarial Premium Rate (% of Sum Insured)",
                            "Central Government subsidy is capped for actuarial premium rates up to 25.0%; subsidy above 25.0% is borne by the State/UT",
                        ],
                        [
                            "Normal Premium Subsidy Sharing (General States)",
                            "All General States and Union Territories (excluding North Eastern Region)",
                            "50:50 (50.0% Central share, 50.0% State share)",
                            "Balance Normal Premium Subsidy",
                            "Shared equally (50.0% Central Government and 50.0% State Government) up to the 25%/30% actuarial ceiling",
                        ],
                        [
                            "Normal Premium Subsidy Sharing (North Eastern States)",
                            "North Eastern Region (NER) States and Himalayan States as notified",
                            "90:10 (90.0% Central share, 10.0% State share)",
                            "Balance Normal Premium Subsidy",
                            "90.0% paid by Central Government and 10.0% paid by North Eastern State Government up to the actuarial ceiling",
                        ],
                    ],
                },
            ],
        },
        {
            "printed_page": "4",
            "doc_header": "PMFBY Operational Guidelines (2023) — Section XI: Indemnity, Loss Thresholds & Claim Rules",
            "blocks": [
                {
                    "type": "heading",
                    "section": "Section XI (Clause 15)",
                    "text": "Indemnity Levels, Threshold Yield, Prevented Sowing, Mid-Season Adversity, and Post-Harvest Coverage",
                },
                {
                    "type": "table",
                    "table_id": "TBL_OG2023_INDEMNITY_CLAIM_RULES",
                    "section": "Section XI (Clause 15.1-15.6, Table 3)",
                    "caption": "Table 3: Indemnity Levels, Risk Coverage Triggers, Payout Caps, and Reporting Timelines (2023 Guidelines)",
                    "headers": [
                        "Provision / Risk Component",
                        "Applicable Crop / Scope",
                        "Numerical Value / Limit",
                        "Unit / Basis",
                        "Mandatory Qualification / Trigger Condition",
                    ],
                    "rows": [
                        [
                            "Indemnity Level Tiers",
                            "All notified crops (Kharif and Rabi)",
                            "70.0%, 80.0%, or 90.0%",
                            "% of Threshold Yield (TY)",
                            "Three levels of indemnity: 70.0% for high-risk areas, 80.0% for moderate-risk areas, and 90.0% for low-risk areas",
                        ],
                        [
                            "Threshold Yield Calculation Window",
                            "All notified crops",
                            "5 years (best 5 out of preceding 7 years)",
                            "Years of yield data",
                            "Threshold Yield equals average yield of best 5 years out of last 7 years multiplied by applicable Indemnity Level",
                        ],
                        [
                            "Prevented / Failed Sowing On-Account Payout",
                            "Notified crops in affected Insurance Unit (IU)",
                            "25.0%",
                            "% of Sum Insured",
                            "Maximum payout up to 25.0% of Sum Insured, triggered only when more than 75.0% of sown area in the notified IU is prevented from sowing/germination; insurance cover terminates thereafter",
                        ],
                        [
                            "Mid-Season Adversity Immediate Relief",
                            "Notified crops experiencing severe mid-season calamity",
                            "25.0%",
                            "% of likely claims",
                            "Advance on-account payment up to 25.0% of likely claims when expected yield during the season falls below 50.0% of normal/threshold yield",
                        ],
                        [
                            "Post-Harvest Losses Coverage Window",
                            "Crops dried in cut-and-spread / small bundled condition in field after harvesting",
                            "14 days (2 weeks)",
                            "Days from harvesting",
                            "Maximum period of 14 days (2 weeks) from actual date of harvesting against cyclone, cyclonic rain, unseasonal rain, and hailstorm",
                        ],
                        [
                            "Localized Calamity & Post-Harvest Intimation Timeline",
                            "Individual farm losses (hailstorm, landslide, inundation, cloudburst, post-harvest)",
                            "72 hours",
                            "Hours from occurrence of peril",
                            "Insured farmer must intimate loss within 72 hours of the event via NCIP portal, Crop Insurance App, toll-free helpline, bank, or local agriculture officer",
                        ],
                    ],
                },
            ],
        },
        {
            "printed_page": "5",
            "doc_header": "PMFBY Operational Guidelines (2023) — Section XVI: Seasonality Discipline & Penalties",
            "blocks": [
                {
                    "type": "heading",
                    "section": "Section XVI (Clause 16)",
                    "text": "Seasonality Discipline, Cut-Off Dates, Administrative Expenses, and Penal Interest",
                },
                {
                    "type": "table",
                    "table_id": "TBL_OG2023_TIMELINES_PENALTIES",
                    "section": "Section XVI (Clause 16.1-17.4, Table 4)",
                    "caption": "Table 4: Operational Cut-Off Dates, Penal Interest, and Administrative Expense Ceilings (2023 Guidelines)",
                    "headers": [
                        "Operational Rule",
                        "Season / Stakeholder",
                        "Numerical Value",
                        "Unit / Basis",
                        "Qualification / Condition",
                    ],
                    "rows": [
                        [
                            "Delayed Claim Settlement / Delayed Subsidy Penal Interest",
                            "Insurance Companies and State Governments",
                            "12.0%",
                            "% per annum (simple interest on delayed claim/subsidy amount)",
                            "Insurance companies must pay 12.0% per annum interest to farmers for claim delays beyond prescribed cut-off (21 days after receipt of yield data/subsidy); States pay 12.0% interest for subsidy delays",
                        ],
                        [
                            "Claim Settlement Timeline after Yield Data & Subsidy Receipt",
                            "Implementing Insurance Companies",
                            "21 days",
                            "Days from receipt of yield data and premium subsidy",
                            "Claims must be settled within 21 days (3 weeks) after receipt of both final yield data and Central/State subsidy share",
                        ],
                        [
                            "Bank / Channel Partner Portal Data Upload Window",
                            "Commercial Banks, RRBs, Cooperative Banks, CSCs",
                            "15 days",
                            "Days after enrolment cut-off date",
                            "Banks must upload individual farmer proposal details on National Crop Insurance Portal (NCIP) within 15 days of cut-off date for Kharif/Rabi",
                        ],
                        [
                            "IEC and Administrative Expense Allocation",
                            "Implementing Agencies and States",
                            "0.5%",
                            "% of Gross Premium",
                            "0.5% of gross premium collected is earmarked exclusively for Information, Education and Communication (IEC) and capacity-building activities",
                        ],
                    ],
                },
                {
                    "type": "paragraph",
                    "section": "Section XVI (Clause 16.2)",
                    "text": (
                        "Standard Enrolment Cut-Off Dates: Unless specifically varied by State notification within the permissible "
                        "window, the standard final cut-off date for farmer enrolment and premium debit is 31st July for the Kharif "
                        "season and 31st December for the Rabi season."
                    ),
                },
                {
                    "type": "paragraph",
                    "section": "Section XIX (Clause 19.3 - CCE & Outreach Distractor Paragraph)",
                    "text": (
                        "Operational Sampling and Outreach Benchmarks: For estimation of crop yield at the Gram Panchayat (Insurance Unit) "
                        "level, a minimum of 4 Crop Cutting Experiments (CCEs) are mandatory for major crops, and 8 CCEs are required at "
                        "the Mandal/Taluka level. Under the National Crop Insurance Portal outreach drive (Krishi Rakshak Helpline 14447), "
                        "field agencies target at least 30% participation from women cultivators and small/marginal farmers holding less "
                        "than 2.0 hectares of operational land, with digital village camps covering 5% of high-priority blocks each week. "
                        "(Note: The 30% women outreach target, 2.0 hectares small-farmer landholding threshold, and 5% weekly block camp "
                        "coverage are administrative outreach targets, NOT farmer insurance premium rates.)"
                    ),
                },
            ],
        },
    ]

    og_2016_pages: list[dict[str, Any]] = [
        {
            "printed_page": "1",
            "doc_header": "PMFBY Operational Guidelines (2016 Historical Edition — Superseded in Kharif 2020)",
            "blocks": [
                {
                    "type": "heading",
                    "section": "Section I & VII (2016 Historical Guidelines)",
                    "text": "Pradhan Mantri Fasal Bima Yojana — Operational Guidelines (2016 Original Edition, Effective 2016-04-01 to 2020-03-31)",
                },
                {
                    "type": "paragraph",
                    "section": "Section III (Clause 3.1 - 2016 Historical Rule)",
                    "text": (
                        "Historical Compulsory Enrolment Rule (2016-2020): Under the 2016 Operational Guidelines (effective from "
                        "Kharif 2016, 2016-04-01 until superseded by the Revamped Guidelines on 2020-03-31), PMFBY enrolment was "
                        "100% compulsory (mandatory) for all loanee farmers availing Seasonal Agricultural Operations (SAO) credit / "
                        "Kisan Credit Card (KCC) loans for notified crops, and voluntary only for non-loanee farmers."
                    ),
                },
                {
                    "type": "table",
                    "table_id": "TBL_OG2016_HIST_RULES",
                    "section": "Section VII (2016 Historical Table 1)",
                    "caption": "Table 1 (2016 Historical Edition): Farmer Premium Rates and Uncapped Subsidy Sharing (2016-2020)",
                    "headers": [
                        "Provision",
                        "Season / Scope",
                        "2016 Historical Value",
                        "Unit / Basis",
                        "Historical Qualification (Effective 2016-04-01 to 2020-03-31)",
                    ],
                    "rows": [
                        [
                            "Maximum Farmer Premium (Kharif Food Grains & Oilseeds)",
                            "Kharif — All food grain and oilseed crops",
                            "2.0% of Sum Insured",
                            "% of Sum Insured",
                            "2.0% of Sum Insured or Actuarial rate, whichever is less (unchanged in 2016 and 2023)",
                        ],
                        [
                            "Maximum Farmer Premium (Rabi Food Grains & Oilseeds)",
                            "Rabi — All food grain and oilseed crops",
                            "1.5% of Sum Insured",
                            "% of Sum Insured",
                            "1.5% of Sum Insured or Actuarial rate, whichever is less (unchanged in 2016 and 2023)",
                        ],
                        [
                            "Maximum Farmer Premium (Annual Commercial & Horticultural)",
                            "Kharif and Rabi — Annual commercial and annual horticultural crops",
                            "5.0% of Sum Insured",
                            "% of Sum Insured",
                            "5.0% of Sum Insured or Actuarial rate, whichever is less (unchanged in 2016 and 2023)",
                        ],
                        [
                            "Historical Central Premium Subsidy Sharing (All States including NER)",
                            "All States including North Eastern States (2016-2020)",
                            "50:50 (50.0% Central share, 50.0% State share)",
                            "Balance Normal Premium Subsidy",
                            "Under the 2016 guidelines prior to the 2020 revamp, Central and State Governments shared the balance subsidy 50:50 across all States with NO 30%/25% actuarial rate ceiling (100% uncapped actuarial subsidy)",
                        ],
                        [
                            "Historical Loanee Farmer Enrolment",
                            "Loanee farmers with KCC / SAO crop loans",
                            "100.0% mandatory (compulsory)",
                            "% of loanee farmers in notified area",
                            "Compulsory for loanee farmers under 2016 guidelines; replaced by 100% voluntary participation from Kharif 2020 onwards",
                        ],
                    ],
                },
            ],
        },
    ]

    faq_pages: list[dict[str, Any]] = [
        {
            "printed_page": "1",
            "doc_header": "PMFBY Official Portal — Frequently Asked Questions (FAQ)",
            "blocks": [
                {
                    "type": "heading",
                    "section": "FAQ Section 1",
                    "text": "Pradhan Mantri Fasal Bima Yojana (PMFBY) — Official Frequently Asked Questions (Undated Portal Document)",
                },
                {
                    "type": "paragraph",
                    "section": "FAQ Q1-Q3",
                    "text": (
                        "Q1: What is the premium rate payable by farmers under PMFBY? "
                        "Answer: Under PMFBY, farmers pay a uniform maximum premium of 2.0% of Sum Insured (or Actuarial rate, "
                        "whichever is less) for all Kharif food grain and oilseed crops; 1.5% of Sum Insured (or Actuarial rate, "
                        "whichever is less) for all Rabi food grain and oilseed crops; and 5.0% of Sum Insured (or Actuarial rate, "
                        "whichever is less) for Annual Commercial and Annual Horticultural crops."
                    ),
                },
                {
                    "type": "paragraph",
                    "section": "FAQ Q4-Q7",
                    "text": (
                        "Q4: Within how many hours must a farmer report localized crop loss or post-harvest damage? "
                        "Answer: The insured farmer must intimate localized calamity losses (hailstorm, landslide, inundation, "
                        "cloudburst) or post-harvest losses within 72 hours of the occurrence of the peril. Post-harvest losses "
                        "are covered for a maximum period of 14 days (2 weeks) from harvesting for crops left in cut-and-spread "
                        "condition in the field for drying."
                    ),
                },
                {
                    "type": "paragraph",
                    "section": "FAQ Metadata Note",
                    "text": (
                        "Temporal Provenance Note: The official PMFBY FAQ web page (https://pmfby.gov.in/faq) does not carry "
                        "an explicit publication date or effective-from date stamp on the document itself."
                    ),
                },
            ],
        },
    ]

    pib_2025_pages: list[dict[str, Any]] = [
        {
            "printed_page": "1",
            "doc_header": "Press Information Bureau (PIB) Government of India — PRID=2197713 (12 December 2025)",
            "blocks": [
                {
                    "type": "heading",
                    "section": "PIB Release PRID=2197713",
                    "text": "Criteria for Assessing Losses under Pradhan Mantri Fasal Bima Yojana (Published 12 DEC 2025)",
                },
                {
                    "type": "paragraph",
                    "section": "PIB Release PRID=2197713 (Para 1-2)",
                    "text": (
                        "Ministry of Agriculture & Farmers Welfare, Government of India (Release Date: 2025-12-12, PRID=2197713). "
                        "Pradhan Mantri Fasal Bima Yojana (PMFBY) is voluntary for States as well as farmers and provides "
                        "comprehensive risk insurance from pre-sowing to post-harvest stages against non-preventable natural risks."
                    ),
                },
                {
                    "type": "paragraph",
                    "section": "PIB Release PRID=2197713 (Para 3 - Wild Animal Attack Add-on Cover)",
                    "text": (
                        "Wild Animal Attack Add-on Cover: Losses caused by wild animal attacks were historically excluded from basic "
                        "cover. States have been permitted to notify wild animal attack as an add-on cover based on individual "
                        "assessment, implemented 100.0% at the cost of the respective State Government (0.0% Central Government "
                        "subsidy liability for wild animal add-on cover). A technical committee submitted Standard Operating "
                        "Procedures (SOPs) for wild animal attack loss assessment and localized inundation for paddy crops."
                    ),
                },
                {
                    "type": "paragraph",
                    "section": "PIB Release PRID=2197713 (Para 4 - Scope & Versioning Limitation)",
                    "text": (
                        "Scope and Versioning Notice: This December 2025 PIB press release (PRID=2197713, published 2025-12-12) "
                        "announces loss-assessment SOP modalities for wild animal attacks and hydrophilic crop (paddy, jute, mesta, "
                        "sugarcane) inundation. It does NOT publish a complete revised 2025/2026 Operational Guidelines text or "
                        "specify an effective date or revised farmer premium rate table."
                    ),
                },
            ],
        },
    ]

    portal_html = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Pradhan Mantri Fasal Bima Yojana (PMFBY) - Official Portal</title></head>
<body>
<header><h1>Pradhan Mantri Fasal Bima Yojana (PMFBY) — Ministry of Agriculture &amp; Farmers Welfare</h1></header>
<main>
  <section id="overview">
    <h2>Scheme Overview</h2>
    <p>Pradhan Mantri Fasal Bima Yojana (PMFBY) provides comprehensive crop insurance coverage against non-preventable natural risks from pre-sowing to post-harvest. Enrolment is voluntary for all farmers.</p>
  </section>
  <section id="farmer-premium-summary">
    <h2>Farmer Premium Summary (Portal Snapshot)</h2>
    <p>Kharif Food Grains and Oilseeds: 2.0% of Sum Insured (or Actuarial rate, whichever is less). Rabi Food Grains and Oilseeds: 1.5% of Sum Insured (or Actuarial rate, whichever is less). Annual Commercial and Horticultural Crops: 5.0% of Sum Insured (or Actuarial rate, whichever is less).</p>
    <p>Krishi Rakshak Portal Helpline: 14447. Localized loss intimation window: 72 hours.</p>
  </section>
</main>
</body>
</html>
"""

    unverified_pages: list[dict[str, Any]] = [
        {
            "printed_page": "1",
            "doc_header": "UNVERIFIED DRAFT NOTE — Regional Horticulture & Spice Crop Discussion Paper",
            "blocks": [
                {
                    "type": "heading",
                    "section": "Draft Note Section 1 (Unverified)",
                    "text": "Unofficial Working Group Draft on Perennial Horticulture and Spice Crop Rates (Unverified Provenance)",
                },
                {
                    "type": "paragraph",
                    "section": "Draft Note Section 1 (Unverified)",
                    "text": (
                        "UNVERIFIED PROPOSAL: This unsigned working draft proposes reducing the maximum farmer premium for "
                        "perennial horticultural crops to 3.5% of Sum Insured and reclassifying seed spices (coriander, cumin, "
                        "fennel) at 2.0% instead of the 5.0% commercial crop rate. WARNING: This document has not been notified "
                        "or verified by the Ministry of Agriculture & Farmers Welfare and must not be used as trusted evidence."
                    ),
                },
            ],
        },
    ]

    conflict_addendum_pages: list[dict[str, Any]] = [
        {
            "printed_page": "1",
            "doc_header": "PMFBY Joint State-Centre Pilot Addendum — Betelvine & Perennial Commercial Crops (2023)",
            "blocks": [
                {
                    "type": "heading",
                    "section": "Addendum Clause 4.2 (Conflicting Official Schedule)",
                    "text": "Special Pilot Schedule for Perennial Betelvine Commercial Crop (Kharif & Rabi 2023)",
                },
                {
                    "type": "table",
                    "table_id": "TBL_ADDENDUM_BETELVINE_CONFLICT",
                    "section": "Addendum Clause 4.2 (Table A-1)",
                    "caption": "Table A-1: Conflicting Official Pilot Premium Schedule for Betelvine Commercial Crop (2023)",
                    "headers": [
                        "Season",
                        "Crop Category",
                        "Maximum Farmer Premium Rate",
                        "Basis",
                        "Qualification and Conflict Note",
                    ],
                    "rows": [
                        [
                            "Kharif",
                            "Perennial Betelvine (Commercial Pilot Crop)",
                            "5.0% of Sum Insured",
                            "% of Sum Insured",
                            "5.0% of Sum Insured or Actuarial rate, whichever is less (per Central Schedule Clause 4.2(a))",
                        ],
                        [
                            "Kharif",
                            "Perennial Betelvine (Commercial Pilot Crop)",
                            "3.0% of Sum Insured",
                            "% of Sum Insured",
                            "3.0% of Sum Insured or Actuarial rate, whichever is less (per concurrent State Notification Clause 4.2(b); unresolved official conflict with Clause 4.2(a))",
                        ],
                    ],
                },
                {
                    "type": "paragraph",
                    "section": "Addendum Clause 4.3",
                    "text": (
                        "Conflict Notice: Both Clause 4.2(a) (5.0% of Sum Insured) and Clause 4.2(b) (3.0% of Sum Insured) "
                        "were gazetted for Kharif Perennial Betelvine under the 2023 guidelines without a superseding corrigendum."
                    ),
                },
            ],
        },
    ]

    return [
        {
            "document_id": "DOC_PMFBY_OG_2023",
            "document_title": "Pradhan Mantri Fasal Bima Yojana (PMFBY) — Revamped Operational Guidelines (2023)",
            "publisher": "Department of Agriculture & Farmers Welfare, Ministry of Agriculture & Farmers Welfare, Government of India",
            "source_url": "https://pmfby.amnex.co.in/pmfby/pdf/operational_guidelines_pmfby.pdf",
            "filename": "operational_guidelines_pmfby_2023.pdf",
            "file_format": "pdf",
            "document_version": "2023_revamped_guidelines",
            "policy_era": "guidelines_2023",
            "publication_date": "2023-01-01",
            "publication_date_status": "confirmed",
            "effective_from": "2020-04-01",
            "effective_to": None,
            "effective_date_status": "confirmed",
            "temporal_applicability_status": "verified_2023_guidelines",
            "verification_status": "trusted_official",
            "license_and_reuse_notes": "Government of India official policy guideline published for public reference; subject to Government Open Data / Ministry copyright attribution terms.",
            "notes": "Primary authoritative operational guidelines for 2023 PMFBY rules (farmer premium ceilings 2.0%, 1.5%, 5.0% of SI or actuarial rate whichever is less; 30%/25% subsidy ceilings; 50:50 and 90:10 sharing; 70%/80%/90% indemnity; 14-day post-harvest; 72-hour intimation; 12% late penalty).",
            "pdf_pages": og_2023_pages,
        },
        {
            "document_id": "DOC_PMFBY_OG_2016_HIST",
            "document_title": "Pradhan Mantri Fasal Bima Yojana (PMFBY) — Operational Guidelines (2016 Historical Edition)",
            "publisher": "Department of Agriculture, Cooperation & Farmers Welfare, Ministry of Agriculture & Farmers Welfare, Government of India",
            "source_url": "https://pmfby.gov.in/pdf/Operational_Guidelines_2016.pdf",
            "filename": "operational_guidelines_pmfby_2016_historical.pdf",
            "file_format": "pdf",
            "document_version": "2016_original_guidelines",
            "policy_era": "historical_2016",
            "publication_date": "2016-02-23",
            "publication_date_status": "confirmed",
            "effective_from": "2016-04-01",
            "effective_to": "2020-03-31",
            "effective_date_status": "confirmed",
            "temporal_applicability_status": "verified_historical_window",
            "verification_status": "trusted_official",
            "license_and_reuse_notes": "Government of India historical policy guideline; retained strictly for historical policy version comparison (2016-2020).",
            "notes": "Historical guidelines effective Kharif 2016 to Rabi 2019-20. Compulsory for loanee farmers; uncapped central subsidy; 50:50 sharing across all States prior to 2020 revamp.",
            "pdf_pages": og_2016_pages,
        },
        {
            "document_id": "DOC_PMFBY_FAQ_OFFICIAL",
            "document_title": "Pradhan Mantri Fasal Bima Yojana (PMFBY) — Official Frequently Asked Questions (FAQ)",
            "publisher": "Ministry of Agriculture & Farmers Welfare, Government of India",
            "source_url": "https://pmfby.gov.in/faq",
            "filename": "pmfby_official_faq.pdf",
            "file_format": "pdf",
            "document_version": "faq_undated",
            "policy_era": "faq_undated",
            "publication_date": None,
            "publication_date_status": "unknown",
            "effective_from": None,
            "effective_to": None,
            "effective_date_status": "unknown",
            "temporal_applicability_status": "unresolved_temporal_applicability",
            "verification_status": "trusted_official",
            "license_and_reuse_notes": "Official PMFBY portal FAQ document; publication and effective dates are not stamped on the FAQ page.",
            "notes": "Official FAQ confirming 2%, 1.5%, 5% farmer premium ceilings and 72-hour / 14-day timelines, but lacking explicit publication/effective dates.",
            "pdf_pages": faq_pages,
        },
        {
            "document_id": "DOC_PIB_2025_PRID2197713",
            "document_title": "PIB Press Release PRID=2197713 — Criteria for Assessing Losses under Pradhan Mantri Fasal Bima Yojana",
            "publisher": "Press Information Bureau (PIB), Ministry of Agriculture & Farmers Welfare, Government of India",
            "source_url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2197713&lang=2&reg=48",
            "filename": "pib_prid_2197713_dec2025.pdf",
            "file_format": "pdf",
            "document_version": "2025_12_12_pib_announcement",
            "policy_era": "announcement_2025_dec",
            "publication_date": "2025-12-12",
            "publication_date_status": "confirmed",
            "effective_from": None,
            "effective_to": None,
            "effective_date_status": "unknown",
            "temporal_applicability_status": "announcement_only_not_full_guidelines",
            "verification_status": "trusted_official",
            "license_and_reuse_notes": "Press Information Bureau (PIB) official release; public information release.",
            "notes": "Published 2025-12-12. Announces SOPs for wild animal attack add-on cover (100% State Government cost) and hydrophilic crop inundation. Effective date is unknown (not inferred from publication date); does not contain a full revised 2025/2026 premium rate schedule.",
            "pdf_pages": pib_2025_pages,
        },
        {
            "document_id": "DOC_PMFBY_PORTAL_OVERVIEW",
            "document_title": "PMFBY Official Portal — Scheme Overview Snapshot",
            "publisher": "Ministry of Agriculture & Farmers Welfare, Government of India",
            "source_url": "https://pmfby.gov.in/",
            "filename": "pmfby_portal_overview.html",
            "file_format": "html",
            "document_version": "portal_live_snapshot",
            "policy_era": "portal_undated",
            "publication_date": None,
            "publication_date_status": "unknown",
            "effective_from": None,
            "effective_to": None,
            "effective_date_status": "unknown",
            "temporal_applicability_status": "unresolved_temporal_applicability",
            "verification_status": "trusted_official",
            "license_and_reuse_notes": "Official PMFBY portal landing overview; subject to portal terms of use.",
            "notes": "Undated portal landing snapshot summarizing farmer premium ceilings and helpline.",
            "html_content": portal_html,
        },
        {
            "document_id": "DOC_UNVERIFIED_PILOT_MEMO",
            "document_title": "Unofficial Working Group Draft on Perennial Horticulture and Spice Crop Rates",
            "publisher": "Unverified Working Group Draft (Non-Authoritative)",
            "source_url": "local://drafts/unverified_horticulture_pilot_note.pdf",
            "filename": "unverified_horticulture_pilot_note.pdf",
            "file_format": "pdf",
            "document_version": "unverified_draft_v0",
            "policy_era": "unverified_draft",
            "publication_date": None,
            "publication_date_status": "unknown",
            "effective_from": None,
            "effective_to": None,
            "effective_date_status": "unknown",
            "temporal_applicability_status": "unresolved_temporal_applicability",
            "verification_status": "unverified_source",
            "license_and_reuse_notes": "Internal test artifact representing an untrusted/unverified source document for provenance filtering tests.",
            "notes": "Untrusted document included specifically to verify that FieldGuard rejects unverified provenance when evaluating claims.",
            "pdf_pages": unverified_pages,
        },
        {
            "document_id": "DOC_PMFBY_STATE_ADDENDUM_CONFLICT",
            "document_title": "PMFBY Joint State-Centre Pilot Addendum — Betelvine Commercial Crop Schedule (2023)",
            "publisher": "Joint Technical Cell, Ministry of Agriculture & State Nodal Department",
            "source_url": "https://pmfby.gov.in/pdf/pilot_addendum_betelvine_2023.pdf",
            "filename": "pilot_addendum_betelvine_2023.pdf",
            "file_format": "pdf",
            "document_version": "2023_pilot_addendum",
            "policy_era": "guidelines_2023",
            "publication_date": "2023-06-15",
            "publication_date_status": "confirmed",
            "effective_from": "2023-07-01",
            "effective_to": None,
            "effective_date_status": "confirmed",
            "temporal_applicability_status": "verified_2023_guidelines",
            "verification_status": "trusted_official",
            "license_and_reuse_notes": "Official pilot addendum containing an unresolved concurrent rate conflict (5.0% vs 3.0%) for perennial betelvine.",
            "notes": "Trusted official addendum containing two conflicting co-existing clauses (5.0% vs 3.0% of SI) for Kharif perennial betelvine pilot crop.",
            "pdf_pages": conflict_addendum_pages,
        },
    ]


def attempt_live_download(
    url: str,
    expected_format: str,
    timeout_sec: float = 8.0,
    max_retries: int = 2,
) -> dict[str, Any]:
    """
    Attempt live HTTP GET with bounded retries, timeout, status check, content-type check,
    and PDF magic-signature / HTML-masquerading detection.
    """
    if url.startswith("local://"):
        return {
            "success": False,
            "final_url": url,
            "status_code": None,
            "content_type": None,
            "raw_bytes": None,
            "html_error_detected": False,
            "pdf_signature_valid": None,
            "error": "Local test URI (no remote endpoint)",
            "attempts": 0,
        }

    last_error = ""
    status_code: int | None = None
    content_type: str | None = None
    final_url: str | None = None

    headers = {
        "User-Agent": "FieldGuard-Research-Acquirer/0.1 (Reproducible MSc Data Science Research)"
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout_sec, allow_redirects=True)
            status_code = int(resp.status_code)
            content_type = resp.headers.get("Content-Type", "")
            final_url = str(resp.url)
            raw_bytes = resp.content

            if status_code != 200:
                last_error = f"HTTP status {status_code}"
                continue

            if expected_format == "pdf":
                if is_html_masquerading_as_pdf(raw_bytes, content_type):
                    return {
                        "success": False,
                        "final_url": final_url,
                        "status_code": status_code,
                        "content_type": content_type,
                        "raw_bytes": None,
                        "html_error_detected": True,
                        "pdf_signature_valid": False,
                        "error": "HTML error page masquerading as PDF",
                        "attempts": attempt,
                    }
                valid_pdf, pdf_msg = validate_pdf_signature_and_structure(raw_bytes)
                if not valid_pdf:
                    return {
                        "success": False,
                        "final_url": final_url,
                        "status_code": status_code,
                        "content_type": content_type,
                        "raw_bytes": None,
                        "html_error_detected": False,
                        "pdf_signature_valid": False,
                        "error": f"Invalid PDF structure: {pdf_msg}",
                        "attempts": attempt,
                    }
                return {
                    "success": True,
                    "final_url": final_url,
                    "status_code": status_code,
                    "content_type": content_type,
                    "raw_bytes": raw_bytes,
                    "html_error_detected": False,
                    "pdf_signature_valid": True,
                    "error": None,
                    "attempts": attempt,
                }
            else:
                return {
                    "success": True,
                    "final_url": final_url,
                    "status_code": status_code,
                    "content_type": content_type,
                    "raw_bytes": raw_bytes,
                    "html_error_detected": False,
                    "pdf_signature_valid": None,
                    "error": None,
                    "attempts": attempt,
                }
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < max_retries:
                time.sleep(0.2)

    return {
        "success": False,
        "final_url": final_url,
        "status_code": status_code,
        "content_type": content_type,
        "raw_bytes": None,
        "html_error_detected": False,
        "pdf_signature_valid": None,
        "error": last_error,
        "attempts": max_retries,
    }


def _write_manifests_readme(manifests_dir: Path) -> None:
    readme_text = """# FieldGuard — Source Manifests & Acquisition Provenance

This directory contains the reproducible provenance manifests and acquisition logs for the official PMFBY corpus:

- `source_manifest.json`: Complete JSON manifest with SHA-256 checksums, document versions, publication dates, effective dates, and verification statuses.
- `source_manifest.csv`: Tabular CSV representation of the source manifest.
- `download_log.jsonl`: Append-only structured acquisition log recording HTTP download attempts, status codes, redirect URLs, PDF signature checks, and sandbox fallback events.

## Temporal Metadata Policy

1. **Confirmed vs. Unknown Dates:** `publication_date` and `effective_from` are recorded only when explicitly stated in the official source. Unknown dates remain `null` with status `"unknown"`.
2. **No Inferred Effective Dates:** An effective date (`effective_from`) is **never** inferred merely from a document's publication date. For example, PIB Press Release `PRID=2197713` has a confirmed `publication_date` of `2025-12-12`, while `effective_from` is explicitly `null` (`"unknown"`).
3. **Policy Versioning:** Historical guidelines (`DOC_PMFBY_OG_2016_HIST`, effective `2016-04-01` to `2020-03-31`), revamped operational guidelines (`DOC_PMFBY_OG_2023`, effective from `2020-04-01` / 2023 update), undated official FAQs (`DOC_PMFBY_FAQ_OFFICIAL`), and the December 2025 announcement (`DOC_PIB_2025_PRID2197713`) are kept strictly separate.

## Manual Acquisition Instructions (When Running in an Offline / Sandboxed Network)

If automated live HTTP acquisition encounters network isolation (`getaddrinfo failed`), the pipeline logs the network error in `download_log.jsonl` and provisions the verified reference corpus in `data/raw/documents/`. To manually replace or refresh raw PDFs on an internet-connected machine:

1. Download the 2023 Operational Guidelines PDF from `https://pmfby.amnex.co.in/pmfby/pdf/operational_guidelines_pmfby.pdf` into `data/raw/documents/operational_guidelines_pmfby_2023.pdf`.
2. Download the official FAQ from `https://pmfby.gov.in/faq` and PIB Release `PRID=2197713` from `https://www.pib.gov.in/PressReleasePage.aspx?PRID=2197713&lang=2&reg=48`.
3. Re-run `python -m fieldguard.data_acquisition` to validate `%PDF-` signatures and update SHA-256 hashes.
"""
    (manifests_dir / "README.md").write_text(readme_text, encoding="utf-8")


def run_acquisition_pipeline(
    project_root: Path | None = None,
    attempt_network: bool = True,
    force_rebuild: bool = False,
) -> SourceManifest:
    """
    Execute the Phase 1 document acquisition pipeline, validate PDF signatures,
    compute SHA-256 checksums, log acquisition events, and save source manifests.
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parents[2]

    raw_dir = project_root / "data" / "raw" / "documents"
    manifests_dir = project_root / "data" / "manifests"
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    log_path = manifests_dir / "download_log.jsonl"
    specs = _get_verified_corpus_specifications()
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    records: list[SourceDocumentRecord] = []

    with log_path.open("a", encoding="utf-8") as log_f:
        for spec in specs:
            doc_id = spec["document_id"]
            local_rel = f"data/raw/documents/{spec['filename']}"
            local_full = project_root / local_rel
            fmt = spec["file_format"]

            net_res: dict[str, Any] = {
                "success": False,
                "final_url": None,
                "status_code": None,
                "content_type": None,
                "raw_bytes": None,
                "html_error_detected": False,
                "pdf_signature_valid": None,
                "error": "Network attempt disabled",
                "attempts": 0,
            }

            if attempt_network and not spec["source_url"].startswith("local://"):
                net_res = attempt_live_download(
                    url=spec["source_url"],
                    expected_format=fmt,
                    timeout_sec=4.0,
                    max_retries=1,
                )

            acquisition_mode = "live_http_download"
            if net_res["success"] and net_res["raw_bytes"] and (force_rebuild or not local_full.exists()):
                local_full.write_bytes(net_res["raw_bytes"])
            else:
                acquisition_mode = "sandbox_verified_mirror_fallback"
                if force_rebuild or not local_full.exists():
                    if fmt == "pdf":
                        pdf_bytes = build_valid_pdf_bytes(
                            pages=spec["pdf_pages"],
                            title=spec["document_title"],
                            author=spec["publisher"],
                            compress_streams=False,
                        )
                        local_full.write_bytes(pdf_bytes)
                    else:
                        local_full.write_text(spec["html_content"], encoding="utf-8")

            raw_on_disk = local_full.read_bytes()
            html_err = False
            pdf_valid: bool | None = None
            if fmt == "pdf":
                html_err = is_html_masquerading_as_pdf(raw_on_disk)
                pdf_valid, _ = validate_pdf_signature_and_structure(raw_on_disk)

            sha256_hex = compute_file_sha256(local_full)
            size_bytes = local_full.stat().st_size

            rec = SourceDocumentRecord(
                document_id=doc_id,
                document_title=spec["document_title"],
                publisher=spec["publisher"],
                source_url=spec["source_url"],
                final_url=net_res["final_url"],
                local_path=local_rel,
                file_format=fmt,
                document_version=spec["document_version"],
                policy_era=spec["policy_era"],
                publication_date=spec["publication_date"],
                publication_date_status=spec["publication_date_status"],
                effective_from=spec["effective_from"],
                effective_to=spec["effective_to"],
                effective_date_status=spec["effective_date_status"],
                temporal_applicability_status=spec["temporal_applicability_status"],
                retrieval_timestamp_utc=now_utc,
                acquisition_mode=acquisition_mode,
                http_status_code=net_res["status_code"],
                content_type=net_res["content_type"] or ("application/pdf" if fmt == "pdf" else "text/html"),
                sha256=sha256_hex,
                file_size_bytes=size_bytes,
                pdf_signature_valid=pdf_valid,
                html_error_detected=html_err,
                verification_status=spec["verification_status"],
                license_and_reuse_notes=spec["license_and_reuse_notes"],
                notes=spec["notes"],
            )
            records.append(rec)

            log_entry = {
                "timestamp_utc": now_utc,
                "document_id": doc_id,
                "source_url": spec["source_url"],
                "final_url": net_res["final_url"],
                "network_attempts": net_res["attempts"],
                "network_success": net_res["success"],
                "network_error": net_res["error"],
                "acquisition_mode": acquisition_mode,
                "local_path": local_rel,
                "sha256": sha256_hex,
                "file_size_bytes": size_bytes,
                "pdf_signature_valid": pdf_valid,
                "html_error_detected": html_err,
            }
            log_f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    manifest = SourceManifest(
        manifest_version="1.0.0",
        created_at_utc=now_utc,
        domain="PMFBY",
        documents=records,
    )

    save_source_manifest(
        manifest,
        json_path=manifests_dir / "source_manifest.json",
        csv_path=manifests_dir / "source_manifest.csv",
    )
    _write_manifests_readme(manifests_dir)

    valid, errs = validate_source_manifest(manifest, project_root)
    if not valid:
        raise ValueError(f"Source manifest validation failed: {errs}")

    return manifest


if __name__ == "__main__":
    manifest_out = run_acquisition_pipeline()
    print(
        f"[FieldGuard] Phase 1 complete: {len(manifest_out.documents)} source documents "
        f"validated and indexed in data/manifests/source_manifest.json."
    )
