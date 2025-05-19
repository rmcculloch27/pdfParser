import re
import pandas as pd
from pathlib import Path
from typing import Union

def buffer_blocks_linkedin(text_dict: dict) -> list[str]:
    """
    Split detail blocks by campaign line triggers like 'Campaign:'.
    This works similarly to DV360/CM360 strategies.
    """
    all_text = "\n".join(page.get("text", "") for page in text_dict.values())
    lines = [line.strip() for line in all_text.splitlines() if line.strip()]
    blocks = []
    buffer = []

    for line in lines:
        if re.match(r"^\d+\s+Campaign:", line) or line.startswith("Campaign:"):
            if buffer:
                blocks.append("\n".join(buffer))
                buffer = []
        buffer.append(line)

    if buffer:
        blocks.append("\n".join(buffer))

    print(f"[DEBUG] Buffered {len(blocks)} LinkedIn campaign blocks.")
    for i, block in enumerate(blocks):
        print(f"\n[BLOCK {i+1}]\n{'='*60}\n{block[:500]}\n{'='*60}") 
    return blocks

def extract_linkedin(text_dict, invoice_num: str, filename: str, invoice_month: str) -> Union[pd.DataFrame, None]:
    rows = []
    summary_text = ""
    full_text = "\n".join(p.get("text", "") for p in text_dict.values())
    page_one_text = text_dict.get("page_1", {}).get("text", "")
    print(f"\n[DEBUG] Summary text from page_1:\n{page_one_text}")


    print("\n[DEBUG] Full text dictionary content:")
    for k, v in text_dict.items():
        print(f"--- {k} ---\n{v.get('text', '')}\n")
    
    for page_num, page in text_dict.items():
        if "Special Instructions" in page.get("text", ""):
            summary_text = page.get("text", "")
            break
    print(f"\n[DEBUG] full summary content:\n{summary_text}")

    fein_match = re.search(r'FEIN:\s*([\d\-]+)', page_one_text)
    fein = fein_match.group(1) if fein_match else None

    due_date_match = re.search(r'Due\s+Date\s*[:：]\s*(\d{1,2}-[A-Z]{3}-\d{4})', page_one_text)
    due_date = due_date_match.group(1) if due_date_match else None
    



    advertiser_campaign_match = re.search(r'Advertiser Campaign\s:\s\w+:\d{9}', summary_text)
    advertiser_campaign = advertiser_campaign_match.group(1) if advertiser_campaign_match else None

    # Summary row extraction
    match = re.search(r'Total\s+([\d,]+\.\d{2})', summary_text)
    if match:
        amount = float(match.group(1).replace(",", ""))
        rows.append({
            "InvoiceType": "LinkedIn",
            "FEIN": fein, 
            "Invoice#": invoice_num,
            "Month": invoice_month,
            "DueDate": due_date, 
            "filename": Path(filename).name,
            "RowType": "summary",
            "Quantity": "summary",
            "UOM": "summary",
            "Campaign": "TOTAL",
            "Amount($)": amount, 
            "BillingPeriod": "summary",
            "BillingRate": "summary"
        })

    # Detail block parsing
    blocks = buffer_blocks_linkedin(text_dict)

    for block in blocks:
        # Primary: Try to extract normally
        campaign_match = re.search(r"Campaign:\s*(.+?)\s+\d", block)
        if campaign_match:
            candidate = campaign_match.group(1).strip()
            # Reject numeric-only campaign values like "349.36"
            if not re.match(r"^\d+(\.\d+)?$", candidate):
                campaign = candidate
            else:
                campaign = None
        else:
            campaign = None


        # Fallback: campaign name is on next line (after numeric line)
        if not campaign:
            lines = block.splitlines()
            for i, line in enumerate(lines):
                if "Campaign:" in line:
                    next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                    if re.search(r"[A-Za-z_]{4,}", next_line):
                        campaign = next_line.strip()
                    break


        billed_match = re.search(r'\b1\s+([\d,]+\.\d{2})\s+0\.00', block)
        alt_match = re.search(r'Qty\s+1\s+([\d,]+\.\d{2})', block)
        billed_amount = billed_match.group(1) if billed_match else alt_match.group(1) if alt_match else None
        if not campaign or not billed_amount:
            continue

        billing_period_match = re.search(r"Billing\sPeriod\sFrom\s(\d+-\w{3}-\d+)\sTo\s(\d+-\w{3}-\d+)", block)
        if billing_period_match:
            billing_period = f"{billing_period_match.group(1)} - {billing_period_match.group(2)}"
        else:
            billing_period = ""

        uom_match = re.search(r"(CPM|CPC)\s(Rate)", block)
    
        if uom_match:
            uom = uom_match.group(1)
        else:
            uom = "CPM"

        quantity_match = re.search(r"Sponsored Content\s*:\s*(\d+)\s+of\s+\d+", block)
        quantity = int(quantity_match.group(1)) if quantity_match else 1


        billing_rate_match = re.search(r"USD\s+([\d,]+)", block)
        billing_rate = float(billing_rate_match.group(1).replace(",", "")) if billing_rate_match else None

        

        rows.append({
            "InvoiceType": "LinkedIn",
            "Invoice#": invoice_num,
            "Month": invoice_month, #this will be null
            "BillingPeriod": billing_period, 
            "filename": Path(filename).name,
            "RowType": "detail",
            "Quantity": quantity,
            "UOM": uom,
            "BillingRate": billing_rate, 
            "Campaign": campaign,
            "Amount($)": float(billed_amount.replace(",", ""))
        })

    return pd.DataFrame(rows) if rows else None
