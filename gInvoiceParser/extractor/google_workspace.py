# import re
# import pandas as pd
# from datetime import datetime

# def extract_google_workspace(summary_text, tables, detail_text, filename):
#     # Extract month range directly from summary_text
#     month_match = re.search(r"Summary for (.+?\d{4})", summary_text)
#     month_range = month_match.group(1) if month_match else "N/A"

#     # Extract invoice number and subtotal amount
#     invoice_match = re.search(r"Invoice number: (\d+)", summary_text)
#     subtotal_match = re.search(r"Subtotal in USD \$([\d,.]+)", summary_text)

#     invoice_number = invoice_match.group(1) if invoice_match else "N/A"
#     subtotal = subtotal_match.group(1) if subtotal_match else "N/A"

#     summary_df = pd.DataFrame([{
#         "InvoiceType": "Google Workspace",
#         "Invoice#": invoice_number,
#         "Month": month_range,
#         "Amount($)": subtotal,
#         "filename": filename,
#         "RowType": "summary"
#     }])

#     # Parse detail rows
#     detail_lines = detail_text.splitlines()
#     detail_rows = []
#     for line in detail_lines:
#         match = re.match(
#             r"(Google Workspace Enterprise Standard Usage .+?)\s+(\d+)\s+([\d,]+\.\d{2})$", line)
#         if match:
#             description = match.group(1)
#             quantity = match.group(2)
#             amount = match.group(3)
#             detail_rows.append({
#                 "InvoiceType": "Google Workspace",
#                 "Invoice#": invoice_number,
#                 "Month": month_range,
#                 "Description": description,
#                 "Quantity": quantity,
#                 "UOM": "users",
#                 "Amount($)": amount,
#                 "filename": filename,
#                 "RowType": "detail"
#             })

#     detail_df = pd.DataFrame(detail_rows)

#     return summary_df, detail_df
from pathlib import Path
import re
import pandas as pd

def extract_google_workspace(text_dict, invoice_num, filename, invoice_month):
    rows = []

    # Reconstruct full text from text_dict
    full_text = "\n".join(p.get("text", "") for p in text_dict.values())

    # Define summary_text and detail_text
    summary_text = text_dict.get("page_1", {}).get("text", "")
    detail_text = "\n".join([v.get("text", "") for k, v in text_dict.items() if k != "page_1"])

    # Extract month range from summary_text
    month_match = re.search(r"Summary for (.+?\d{4})", summary_text)
    month_range = month_match.group(1) if month_match else invoice_month or "N/A"

    # Extract invoice number and subtotal
    invoice_match = re.search(r"Invoice number: (\d+)", summary_text)
    subtotal_match = re.search(r"Subtotal in USD \$([\d,.]+)", summary_text)

    invoice_number = invoice_match.group(1) if invoice_match else invoice_num or "N/A"
    subtotal = subtotal_match.group(1) if subtotal_match else "N/A"

    # Summary row
    rows.append({
        "InvoiceType": "Google Workspace",
        "Invoice#": invoice_number,
        "Month": month_range,
        "Amount($)": subtotal,
        "filename": Path(filename).name,
        "RowType": "summary"
    })

    # Parse detail lines
    for line in detail_text.splitlines():
        match = re.match(r"(Google Workspace Enterprise Standard Usage .+?)\s+(\d+)\s+([\d,]+\.\d{2})$", line)
        if match:
            description = match.group(1)
            quantity = match.group(2)
            amount = match.group(3)
            rows.append({
                "InvoiceType": "Google Workspace",
                "Invoice#": invoice_number,
                "Month": month_range,
                "Description": description,
                "Quantity": quantity,
                "UOM": "users",
                "Amount($)": amount,
                "filename": Path(filename).name,
                "RowType": "detail"
            })

    return pd.DataFrame(rows) if rows else None
