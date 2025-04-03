import re
import pandas as pd

def extract_google_workspace(summary_text: str, tables: list, detail_text: str, filename: str):
    # --- Clean and normalize the summary text ---
    cleaned_summary = re.sub(r"[^\x20-\x7E]+", " ", summary_text)

    # --- Extract summary metadata ---
    invoice_number_match = re.search(r"Invoice number[:\s]*([0-9]+)", cleaned_summary, re.IGNORECASE)
    month_match = re.search(
        r"Period[:\s]*([A-Za-z]+\s+\d{1,2},\s+\d{4})\s*-\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})",
        cleaned_summary,
        re.IGNORECASE
    )

    invoice_number = invoice_number_match.group(1) if invoice_number_match else "N/A"
    if month_match:
        month = f"{month_match.group(1)} - {month_match.group(2)}"
    else:
        month = "N/A"

    detail_rows = []

    # --- Attempt structured table parsing ---
    if tables:
        print(f"[DEBUG] Google Workspace: Found {len(tables)} tables in {filename}")
        for table in tables:
            if not table or len(table) < 2:
                continue
            for row in table[1:]:
                if not row or len(row) < 4:
                    continue
                try:
                    detail_rows.append({
                        "InvoiceType": "Google Workspace",
                        "Invoice#": invoice_number,
                        "Month": month,
                        "Description": row[0],
                        "Quantity": row[1],
                        "UOM": row[2],
                        "Amount($)": float(row[-1].replace(",", ""))
                    })
                except Exception:
                    continue

    # --- Fallback to raw text parsing if no valid tables ---
    if not detail_rows:
        print(f"[DEBUG] No valid tables for {filename}. Using fallback text parsing.")
        print(f"[DEBUG] Detail text snippet:\n{detail_text[:500]}")

        fallback_pattern = re.compile(
            r"(?P<desc>.+?)\s+(?P<qty>\d{1,5})\s+\$?(?P<amount>[\d,]+\.\d{2})"
        )

        for line in detail_text.splitlines():
            match = fallback_pattern.match(line.strip())
            if match:
                try:
                    detail_rows.append({
                        "InvoiceType": "Google Workspace",
                        "Invoice#": invoice_number,
                        "Month": month,
                        "Description": match.group("desc").strip(),
                        "Quantity": int(match.group("qty").replace(",", "")),
                        "UOM": "users",  # assumed default UOM
                        "Amount($)": float(match.group("amount").replace(",", ""))
                    })
                except Exception:
                    continue

    # --- Summary total from detail (or 0.0 if none) ---
    total_amount = sum(float(row["Amount($)"]) for row in detail_rows if row.get("Amount($)"))

    summary_df = pd.DataFrame([{
        "InvoiceType": "Google Workspace",
        "Invoice#": invoice_number,
        "Month": month,
        "Amount($)": round(total_amount, 2)
    }])

    detail_df = pd.DataFrame(detail_rows)
    print(f"[DEBUG] Parsed {len(detail_df)} Workspace detail rows for {filename}")
    print(f"[DEBUG] Detail text preview for {filename}:\n{detail_text[:1000]}")
    return summary_df, detail_df
