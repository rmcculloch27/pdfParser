from pathlib import Path
import re
import pandas as pd

def extract_google_workspace(text_dict, invoice_num, filename, invoice_month):
    rows = []

    summary_text = text_dict.get("page_1", {}).get("text", "")
    detail_text = "\n".join([v.get("text", "") for k, v in text_dict.items() if k != "page_1"])

    ### Use this print block for debugging
    # print("\n[DEBUG] summary_text (Page 1):\n" + "-"*40)
    # print(summary_text)
    # print("-"*40 + "\n")

    # Month
    month_match = re.search(r"Summary for (.+? \d{4}\s*[-–]\s*.+? \d{4})", summary_text)
    month_range = month_match.group(1) if month_match else invoice_month or "N/A"

    # Invoice Number
    invoice_match = re.search(r"Invoice number[:\s]*(\d+)", summary_text)
    invoice_number = invoice_match.group(1) if invoice_match else invoice_num or "N/A"

    # Subtotal
    subtotal_match = re.search(r"Subtotal in USD \$([\d,]+\.\d{2})", summary_text)
    subtotal = subtotal_match.group(1).replace(",", "") if subtotal_match else "0.00"

    # Primary extraction
    billing_id_match = re.search(r"\b(\d{4}-\d{4}-\d{4})\b", summary_text)
    billing_id = billing_id_match.group(1) if billing_id_match else ""

    domain_match = re.search(r"\b([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b", summary_text)
    domain_name = domain_match.group(1) if domain_match else ""

    # --- Fallback extraction (for dotted OCR formats) ---
    if not billing_id or not domain_name:
        cleaned_summary = re.sub(r"[.\\s]+", "", summary_text)  # remove dots/spaces

        if not billing_id:
            fallback_id_match = re.search(r"(\d{4}-\d{4}-\d{4})", cleaned_summary)
            if fallback_id_match:
                billing_id = fallback_id_match.group(1)

        if not domain_name:
            domain_candidates = re.findall(
                r"[a-zA-Z0-9-]+\.(com|org|net|edu|gov|co\.uk|io|ai)",  # safe known TLDs
                cleaned_summary,
                re.IGNORECASE
            )
            for cand in domain_candidates:
                if len(cand) > 4 and "invoic" not in cand.lower():
                    domain_name = cand
                    break





    # --- Summary Row ---
    rows.append({
        "InvoiceType": "Google Workspace",
        "Invoice#": invoice_number,
        "Month": month_range,
        "Amount($)": subtotal,
        "BillingID": billing_id,
        "Domain": domain_name,
        "filename": Path(filename).name,
        "RowType": "summary"
    })

    # --- Detail Rows ---
    detail_lines = detail_text.splitlines()
    for line in detail_lines:
        match = re.match(r"(Google Workspace Enterprise Standard Usage.*?)\s+(\d+)\s+([\d,]+\.\d{2})$", line)
        if match:
            description = match.group(1).strip()
            quantity = match.group(2)
            amount = match.group(3).replace(",", "")
            rows.append({
                "InvoiceType": "Google Workspace",
                "Invoice#": invoice_number,
                "Month": month_range,
                "Description": description,
                "Quantity": quantity,
                "UOM": "users",
                "Amount($)": amount,
                "BillingID": billing_id,
                "Domain": domain_name,
                "filename": Path(filename).name,
                "RowType": "detail"
            })
    # Enforce uniform schema
    expected_cols = [
        "InvoiceType", "Invoice#", "Month", "Amount($)", "BillingID", "Domain",
        "Description", "Quantity", "UOM", "RowType", "filename"
    ]
    df = pd.DataFrame(rows)
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""

    return df[expected_cols]

