# import re
# import pandas as pd
# from pathlib import Path
# from typing import Union

# def extract_dv360(text_dict, invoice_num, filename, invoice_month) -> Union[pd.DataFrame, None]:
#     summary_text = text_dict.get("page_1", {}).get("text", "")
#     detail_text = "\n".join(p.get("text", "") for k, p in text_dict.items() if k != "page_1")
#     rows = []

#     # --- Summary metadata ---
#     invoice_number_match = re.search(r"Invoice number[:\s]*([\d\-]+)", summary_text, re.IGNORECASE)
#     date_range_match = re.search(r"Summary for\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\s*[-–]\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})", summary_text)
#     amount_match = re.search(r"Total amount due.*?\$([\d,]+\.\d{2})", summary_text)

#     invoice_number = invoice_number_match.group(1) if invoice_number_match else invoice_num
#     month = f"{date_range_match.group(1)} - {date_range_match.group(2)}" if date_range_match else invoice_month
#     total_amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0.0

#     rows.append({
#         "InvoiceType": "Display and Video 360",
#         "Invoice#": invoice_number,
#         "Month": month,
#         "filename": Path(filename).name,
#         "RowType": "summary",
#         "FeeType": "Total",
#         "Partner": "SUMMARY",
#         "PartnerID": "SUMMARY",
#         "AdvertiserName": "SUMMARY",
#         "AdvertiserID": "SUMMARY",
#         "Quantity": "",
#         "UOM": "",
#         "Unit Price": "",
#         "Amount($)": total_amount
#     })

#     # --- Reformat broken lines in detail_text ---
#     lines = detail_text.splitlines()
#     merged_lines = []
#     buffer = ""

#     for line in lines:
#         line = line.strip()
#         if not line:
#             continue
#         if re.search(r"(Media Cost|Platform Fee|Data Fee|Adjustment|Advertiser)", line):
#             if buffer:
#                 merged_lines.append(buffer.strip())
#             buffer = line
#         else:
#             buffer += " " + line
#     if buffer:
#         merged_lines.append(buffer.strip())

#     # --- Pattern match after cleanup ---
#     pattern = re.compile(
#         r"(?P<fee_type>.*?) - Partner: (?P<partner_name>.*?) ID: (?P<partner_id>\d+)\s*-\s*Advertiser: (?P<advertiser_name>.*?) ID: (?P<advertiser_id>\d+)\s+(?P<quantity>[-\d,]+)\s+(?P<uom>\w+)\s+(?P<amount>[-\d,.]+)"
#     )

#     for line in merged_lines:
#         match = pattern.search(line)
#         if match:
#             try:
#                 quantity = int(match.group("quantity").replace(",", ""))
#                 amount = float(match.group("amount").replace(",", ""))
#                 unit_price = round(amount / quantity, 4) if quantity != 0 else None

#                 rows.append({
#                     "InvoiceType": "Display and Video 360",
#                     "Invoice#": invoice_number,
#                     "Month": month,
#                     "filename": Path(filename).name,
#                     "RowType": "detail",
#                     "FeeType": match.group("fee_type").strip(),
#                     "Partner": match.group("partner_name").strip(),
#                     "PartnerID": match.group("partner_id"),
#                     "AdvertiserName": match.group("advertiser_name").strip(),
#                     "AdvertiserID": match.group("advertiser_id"),
#                     "Quantity": quantity,
#                     "UOM": match.group("uom"),
#                     "Unit Price": unit_price,
#                     "Amount($)": amount
#                 })
#             except Exception as e:
#                 print(f"[WARN] Skipped malformed DV360 line: {e}")

#     print(f"[INFO] Parsed {len(rows) - 1} DV360 detail rows from {filename}")
#     return pd.DataFrame(rows)

import re
import pandas as pd
from pathlib import Path
from typing import Union

def buffer_and_merge_lines(text_dict):
    """
    Smartly merge broken lines across pages if needed.
    Returns a list of fully reconstructed logical lines.
    """
    lines = []
    for page_num, page_data in text_dict.items():
        page_text = page_data.get("text", "")
        if page_text:
            lines.extend(page_text.splitlines())

    lines = [line.strip() for line in lines if line.strip()]

    merged_lines = []
    buffer = ""

    for idx, line in enumerate(lines):
        if any(
            keyword in line
            for keyword in ["Media Cost", "Platform Fee", "Data Fee", "Adjustment"]
        ):
            if buffer:
                merged_lines.append(buffer.strip())
            buffer = line
        else:
            buffer += " " + line

    if buffer:
        merged_lines.append(buffer.strip())

    return merged_lines

def extract_dv360(text_dict, invoice_num, filename, invoice_month) -> Union[pd.DataFrame, None]:
    summary_text = text_dict.get("page_1", {}).get("text", "")
    rows = []

    # --- Summary metadata ---
    invoice_number_match = re.search(r"Invoice number[:\s]*([\d\-]+)", summary_text, re.IGNORECASE)
    date_range_match = re.search(r"Summary for\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\s*[-–]\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})", summary_text)
    amount_match = re.search(r"Total amount due.*?\$([\d,]+\.\d{2})", summary_text)

    invoice_number = invoice_number_match.group(1) if invoice_number_match else invoice_num
    month = f"{date_range_match.group(1)} - {date_range_match.group(2)}" if date_range_match else invoice_month
    total_amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0.0

    # Add summary row
    rows.append({
        "InvoiceType": "Display and Video 360",
        "Invoice#": invoice_number,
        "Month": month,
        "filename": Path(filename).name,
        "RowType": "summary",
        "FeeType": "Total",
        "Partner": "SUMMARY",
        "PartnerID": "SUMMARY",
        "AdvertiserName": "SUMMARY",
        "AdvertiserID": "SUMMARY",
        "Quantity": "",
        "UOM": "",
        "Unit Price": "",
        "Amount($)": total_amount
    })

    # --- Process detail lines ---
    merged_lines = buffer_and_merge_lines(text_dict)

    # Define patterns
    primary_pattern = re.compile(
        r"(?P<fee_type>.*?) - Partner: (?P<partner_name>.*?) ID: (?P<partner_id>\d+)\s*-\s*Advertiser: (?P<advertiser_name>.*?) ID: (?P<advertiser_id>\d+)\s+(?P<quantity>[-\d,]+)\s+(?P<uom>\w+)\s+(?P<amount>[-\d,.]+)"
    )

    fallback1_pattern = re.compile(
        r"(?P<fee_type>.*?) - Partner: (?P<partner_name>.*?) ID: (?P<partner_id>\d+)\s*-\s*Advertiser: (?P<advertiser_name>.*?) ID: (?P<advertiser_id>\d+)\s+(?P<quantity>[-\d,]+)\s+(?P<uom>\w+)"
    )

    fallback2_pattern = re.compile(
        r"(?P<fee_type>.*?) - Partner: (?P<partner_name>.*?) ID: (?P<partner_id>\d+)"
    )

    for idx, line in enumerate(merged_lines):
        match = primary_pattern.search(line)

        if not match:
            match = fallback1_pattern.search(line)

        if not match:
            match = fallback2_pattern.search(line)

        if match:
            row = {
                "InvoiceType": "Display and Video 360",
                "Invoice#": invoice_number,
                "Month": month,
                "filename": Path(filename).name,
                "RowType": "detail",
                "FeeType": match.group("fee_type").strip() if match.groupdict().get("fee_type") else "",
                "Partner": match.group("partner_name").strip() if match.groupdict().get("partner_name") else "",
                "PartnerID": match.group("partner_id").strip() if match.groupdict().get("partner_id") else "",
                "AdvertiserName": match.group("advertiser_name").strip() if match.groupdict().get("advertiser_name") else "",
                "AdvertiserID": match.group("advertiser_id").strip() if match.groupdict().get("advertiser_id") else "",
                "Quantity": match.group("quantity").replace(",", "") if match.groupdict().get("quantity") else "",
                "UOM": match.group("uom") if match.groupdict().get("uom") else "",
                "Amount($)": match.group("amount").replace(",", "") if match.groupdict().get("amount") else "",
                "Unit Price": "",
            }

            # --- If missing Amount, look to next line
            if not row["Amount($)"] and idx + 1 < len(merged_lines):
                next_line = merged_lines[idx + 1]
                amt_match = re.search(r"([-]?\d{1,3}(?:,\d{3})*(?:\.\d{2}))", next_line)
                if amt_match:
                    row["Amount($)"] = amt_match.group(1).replace(",", "")

            # --- Calculate Unit Price if possible
            try:
                if row["Quantity"] and row["Amount($)"]:
                    quantity_val = int(row["Quantity"])
                    amount_val = float(row["Amount($)"])
                    row["Unit Price"] = round(amount_val / quantity_val, 4) if quantity_val != 0 else ""
            except Exception:
                pass  # don't crash if weird data

            rows.append(row)

    print(f"[INFO] Parsed {len(rows)-1} DV360 detail rows from {filename}")
    return pd.DataFrame(rows)
