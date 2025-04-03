# import re
# import pandas as pd

# def extract_dv360(summary_text: str, tables: list, detail_text: str, filename: str):
#     # --- Summary metadata ---
#     invoice_number_match = re.search(r"Invoice number[:\s]*([\d\-]+)", summary_text, re.IGNORECASE)
#     date_range_match = re.search(r"Summary for\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\s*-\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})", summary_text)
#     amount_match = re.search(r"Total amount due.*?\$([\d,]+\.\d{2})", summary_text)

#     invoice_number = invoice_number_match.group(1) if invoice_number_match else "N/A"
#     month = f"{date_range_match.group(1)} - {date_range_match.group(2)}" if date_range_match else "N/A"
#     total_amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0.0

#     summary_df = pd.DataFrame([{
#         "InvoiceType": "Display and Video 360",
#         "Invoice#": invoice_number,
#         "Month": month,
#         "Amount($)": total_amount
#     }])

#     # --- Preprocess detail text to rejoin broken lines ---
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
#     line_items = []
#     pattern = re.compile(
#         r"(?P<fee_type>.+?)\s*-\s*Partner:\s*(?P<partner>.+?)\s*-\s*Constellation ID:\s*(?P<partner_id>\d+)\s*-\s*Advertiser:\s*(?P<advertiser>.+?)\s*ID:\s*(?P<advertiser_id>\d+)\s+(?P<quantity>[-\d,]+)\s+(?P<uom>\w+)\s+(?P<amount>[-\d,.]+)"
#     )

#     for line in merged_lines:
#         match = pattern.search(line)
#         if match:
#             try:
#                 line_items.append({
#                     "InvoiceType": "Display and Video 360",
#                     "Invoice#": invoice_number,
#                     "Month": month,
#                     "FeeType": match.group("fee_type").strip(),
#                     "Partner": match.group("partner").strip(),
#                     "PartnerID": match.group("partner_id"),
#                     "AdvertiserName": match.group("advertiser").strip(),
#                     "AdvertiserID": match.group("advertiser_id"),
#                     "Quantity": int(match.group("quantity").replace(",", "")),
#                     "UOM": match.group("uom"),
#                     "Amount($)": float(match.group("amount").replace(",", ""))
#                 })
#             except Exception:
#                 continue

#     detail_df = pd.DataFrame(line_items)
#     print(f"[DEBUG] Parsed {len(detail_df)} DV360 detail rows for {filename}")
#     return summary_df, detail_df
import re
import pandas as pd

def extract_dv360(summary_text: str, tables: list, detail_text: str, filename: str):
    # --- Summary metadata ---
    invoice_number_match = re.search(r"Invoice number[:\s]*([\d\-]+)", summary_text, re.IGNORECASE)
    date_range_match = re.search(r"Summary for\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\s*-\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})", summary_text)
    amount_match = re.search(r"Total amount due.*?\$([\d,]+\.\d{2})", summary_text)

    invoice_number = invoice_number_match.group(1) if invoice_number_match else "N/A"
    month = f"{date_range_match.group(1)} - {date_range_match.group(2)}" if date_range_match else "N/A"
    total_amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0.0

    summary_df = pd.DataFrame([{
        "InvoiceType": "Display and Video 360",
        "Invoice#": invoice_number,
        "Month": month,
        "Amount($)": total_amount
    }])

    # --- Preprocess detail text to rejoin broken lines ---
    lines = detail_text.splitlines()
    merged_lines = []
    buffer = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.search(r"(Media Cost|Platform Fee|Data Fee|Adjustment|Advertiser)", line):
            if buffer:
                merged_lines.append(buffer.strip())
            buffer = line
        else:
            buffer += " " + line

    if buffer:
        merged_lines.append(buffer.strip())

    # --- Pattern match after cleanup ---
    line_items = []
    pattern = re.compile(
        r"(?P<fee_type>.+?)\s*-\s*Partner:\s*(?P<partner>.+?)\s*-\s*Constellation ID:\s*(?P<partner_id>\d+)\s*-\s*Advertiser:\s*(?P<advertiser>.+?)\s*ID:\s*(?P<advertiser_id>\d+)\s+(?P<quantity>[-\d,]+)\s+(?P<uom>\w+)\s+(?P<amount>[-\d,.]+)"
    )

    for line in merged_lines:
        match = pattern.search(line)
        if match:
            try:
                line_items.append({
                    "InvoiceType": "Display and Video 360",
                    "Invoice#": invoice_number,
                    "Month": month,
                    "FeeType": match.group("fee_type").strip(),
                    "Partner": match.group("partner").strip(),
                    "PartnerID": match.group("partner_id"),
                    "AdvertiserName": match.group("advertiser").strip(),
                    "AdvertiserID": match.group("advertiser_id"),
                    "Quantity": int(match.group("quantity").replace(",", "")),
                    "UOM": match.group("uom"),
                    "Amount($)": float(match.group("amount").replace(",", ""))
                })
            except Exception:
                continue

    detail_df = pd.DataFrame(line_items)
    print(f"[DEBUG] Parsed {len(detail_df)} DV360 detail rows for {filename}")
    return summary_df, detail_df
