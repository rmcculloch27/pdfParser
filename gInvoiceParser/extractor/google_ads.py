import re
import pandas as pd

def extract_google_ads(summary_text: str, tables: list, detail_text: str, filename: str):
    # --- Step 1: Metadata extraction ---
    invoice_number_match = re.search(r"Invoice number[:\s]*([0-9]+)", summary_text, re.IGNORECASE)
    date_range_match = re.search(
        r"Summary for\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\s*-\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})",
        summary_text,
        re.IGNORECASE
    )
    amount_match = re.search(r"Total amount due.*?\$([\d,]+\.\d{2})", summary_text, re.IGNORECASE)

    invoice_number = invoice_number_match.group(1) if invoice_number_match else "N/A"
    month = f"{date_range_match.group(1)} - {date_range_match.group(2)}" if date_range_match else "N/A"
    total_amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0.0

    detail_rows = []

    # --- Step 2: Structured table parsing (if any) ---
    if tables:
        print(f"[DEBUG] Google Ads: Found {len(tables)} tables in {filename}")
        for table in tables:
            if not table or len(table) < 2:
                continue
            for row in table[1:]:
                if not row or len(row) < 4:
                    continue
                try:
                    detail_rows.append({
                        "InvoiceType": "Google Ads",
                        "Invoice#": invoice_number,
                        "Month": month,
                        "Description": row[0],
                        "Quantity": row[1],
                        "UOM": row[2],
                        "Amount($)": float(row[-1].replace(",", ""))
                    })
                except Exception:
                    continue

    # --- Step 3: Fallback parsing from detail_text ---
    if not detail_rows:
        print(f"[DEBUG] No valid tables for {filename}. Using fallback text parsing.")

        # Debug: show snippet
        print(f"[DEBUG] Fallback text snippet for {filename}:\n{detail_text[:500]}")

        fallback_pattern = re.compile(
            r"(?P<desc>.+?)\s+(?P<qty>[\d,]+)\s+(?P<uom>\w+)\s+\$?(?P<amount>[\d,]+\.\d{2})"
        )

        for line in detail_text.splitlines():
            match = fallback_pattern.match(line.strip())
            if match:
                try:
                    detail_rows.append({
                        "InvoiceType": "Google Ads",
                        "Invoice#": invoice_number,
                        "Month": month,
                        "Description": match.group("desc").strip(),
                        "Quantity": int(match.group("qty").replace(",", "")),
                        "UOM": match.group("uom"),
                        "Amount($)": float(match.group("amount").replace(",", ""))
                    })
                except Exception:
                    continue

    # --- Step 4: Return summary + detail ---
    summary_df = pd.DataFrame([{
        "InvoiceType": "Google Ads",
        "Invoice#": invoice_number,
        "Month": month,
        "Amount($)": round(total_amount, 2)
    }])
    detail_df = pd.DataFrame(detail_rows)

    print(f"[DEBUG] Parsed {len(detail_df)} Google Ads line items for {filename}")
    return summary_df, detail_df
