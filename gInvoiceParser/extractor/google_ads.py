import re
import pandas as pd
from pathlib import Path
from typing import Union

def buffer_blocks_google_ads(full_text: str) -> list[str]:
    """
    Split blocks using the 'For questions about this invoice' footer
    to prevent account metadata from leaking between sections.
    """
    # Split on each occurrence of the footer line
    pattern = r"For questions about this invoice.*?Page \d+ of \d+"
    parts = re.split(pattern, full_text)

    blocks = [part.strip() for part in parts if part.strip()]
    print(f"[DEBUG] Buffered {len(blocks)} blocks from full text using page footer strategy.")
    for i, block in enumerate(blocks):
        print(f"\n[BLOCK {i+1}]\n{'='*60}\n{block[:500]}\n{'='*60}")  # Truncated for readability
    return blocks


def extract_google_ads(text_dict, invoice_num: str, filename: str, invoice_month: str) -> Union[pd.DataFrame, None]:
    summary_text = text_dict.get("page_1", {}).get("text", "")
    full_text = "\n".join(p.get("text", "") for p in text_dict.values())

    print("\n[DEBUG] Full text dictionary content:")
    for k, v in text_dict.items():
        print(f"--- {k} ---\n{v.get('text', '')}\n")

    # Summary metadata
    # summary text clean eliminates white space for cleaner extraction
    summary_text_clean = re.sub(r'[\s\.]+', '', summary_text)
    print("\n[DEBUG] Cleaned summary_text:\n", summary_text_clean)


    invoice_number_match = re.search(r"Invoice number[:\s]*([0-9]+)", summary_text, re.IGNORECASE)
    date_range_match = re.search(
        r"Summary for\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\s*[-\u2013]\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})",
        summary_text,
        re.IGNORECASE
    )
    amount_match = re.search(r"TotalamountdueinUSD\$([\d,]+\.\d{2})", summary_text_clean, re.IGNORECASE)
    due_date_match = re.search(r"Due([A-Za-z]+\d{1,2},\d{4})", summary_text_clean, re.IGNORECASE)
    billing_id_match = re.search(r"BillingID[:]*([\d]{4}-[\d]{4}-[\d]{4})", summary_text_clean, re.IGNORECASE)
    print("\n[DEBUG] billng id match:\n", billing_id_match)
    print("\n[DEBUG] due date match:\n", due_date_match)

    billing_code = billing_id_match.group(1) if billing_id_match else None
    due_date = due_date_match.group(1) if due_date_match else ""
    invoice_number = invoice_number_match.group(1) if invoice_number_match else invoice_num
    month = f"{date_range_match.group(1)} - {date_range_match.group(2)}" if date_range_match else invoice_month
    total_amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0.0

    rows = []

    # Summary row
    rows.append({
        "InvoiceType": "Google Ads",
        "Invoice#": invoice_number,
        "Month": month,
        "DueDate": due_date,
        "BillingCode": billing_code,
        "filename": Path(filename).name,
        "RowType": "summary",
        "Account ID": "SUMMARY",
        "Account": "SUMMARY",
        "Account budget": "SUMMARY",
        "Description": "",
        "Quantity": "",
        "UOM": "",
        "Amount($)": total_amount
    })

    # Block parsing
    blocks = buffer_blocks_google_ads(full_text)

    for block in blocks:
        account_id_match = re.search(r"Account ID: (\S+)", block)
        account_name_match = re.search(r"Account: (.+)", block)
        account_budget_match = re.search(r"Account budget: (.+)", block)

        account_id = account_id_match.group(1).strip() if account_id_match else None
        account_name = account_name_match.group(1).strip() if account_name_match else None
        account_budget = account_budget_match.group(1).strip() if account_budget_match else None

        flines = block.splitlines()
        i = 0
        while i < len(flines):
            line = flines[i].strip()
            next_line = flines[i + 1].strip() if i + 1 < len(flines) else ""

            # Init default row fields
            desc = ""
            qty = ""
            uom = ""
            amount = None

            # --- Case 1: Standard Clicks/Impressions ---
            detail_match = re.match(r"(.+?)\s+(\d+)\s+(Clicks|Impressions)\s+([\d,.]+)", line)
            if detail_match:
                desc, qty, uom, amount = detail_match.groups()
                i += 1

            # --- Case 2: Multiline fallback for Invalid activity ---
            elif "Invalid activity" in line and re.match(r"^-?\$?[\d,.]+$", next_line):
                desc = line
                amount = next_line
                i += 2

            else:
                i += 1
                continue

            try:
                rows.append({
                    "InvoiceType": "Google Ads",
                    "Invoice#": invoice_number,
                    "Month": month,
                    "filename": Path(filename).name,
                    "RowType": "detail",
                    "Account ID": account_id,
                    "Account": account_name,
                    "Account budget": account_budget,
                    "Description": desc.strip(),
                    "Quantity": int(qty) if qty else "",
                    "UOM": uom,
                    "Amount($)": float(str(amount).replace(",", "").replace("$", "")) if amount else None
                })
            except Exception as e:
                print(f"[ERROR] Failed to parse row from line: '{line}'\n{e}")



    print(f"\n[DEBUG] Parsed {len(rows)-1} detail rows + 1 summary row for {filename}")
    return pd.DataFrame(rows) if rows else None
