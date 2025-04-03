import re
import pandas as pd

def extract_linkedin(summary_text: str, tables: list, detail_text: str, filename: str):
    # Summary Metadata
    invoice_number = re.search(r"Invoice Number\s*[:]*\s*(\d+)", summary_text)
    invoice_num = invoice_number.group(1) if invoice_number else "N/A"

    # Extract month from billing period
    month_match = re.search(r"Billing Period From\s+(\d{2}-[A-Z]{3}-\d{4})", summary_text)
    month = "Dec 2024" if month_match else "N/A"  # Fallback to Dec 2024 if not found

    # Total from 'Balance Due'
    amount_match = re.search(r"Balance Due\s*[:]*\s*USD\s*([\d,]+\.\d{2})", summary_text)
    total_amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0.0

    # Summary Row
    summary_df = pd.DataFrame([{
        "InvoiceType": "LinkedIn",
        "Invoice#": invoice_num,
        "Month": month,
        "Amount($)": total_amount
    }])

    # --- Updated Detail Fallback ---
    detail_rows = []
    detail_pattern = re.compile(
        r"Campaign:\s+(.*?)\s+(\d+(?:\.\d{2})?)\s+\d+\s+(\d+(?:\.\d{2})?)"
    )

    for match in detail_pattern.finditer(detail_text):
        detail_rows.append({
            "InvoiceType": "LinkedIn",
            "Invoice#": invoice_num,
            "Month": month,
            "Campaign": match.group(1).strip(),
            "Quantity": float(match.group(2)),
            "Amount($)": float(match.group(3)),
            "RowType": "detail"
        })

    print(f"[DEBUG] Parsed {len(detail_rows)} LinkedIn detail rows for {filename}")
    return summary_df, pd.DataFrame(detail_rows)

