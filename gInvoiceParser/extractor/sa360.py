import re
import pandas as pd
from typing import Union

def extract_sa360(text_dict, invoice_num, filename, invoice_month) -> Union[pd.DataFrame, None]:
    rows = []

    # Combine all page text
    lines = []
    for page in text_dict.values():
        text = page.get("text", "")
        lines.extend(text.splitlines())

    lines = [line.strip() for line in lines if line.strip()]
    full_text = "\n".join(lines)

    # Extract due date
    due_date_match = re.search(r"Due Date[:\s]+(\d{2}/\d{2}/\d{4})", full_text, re.IGNORECASE)
    due_date_value = due_date_match.group(1) if due_date_match else ""

    # Buffer blocks until the next "% Media Spend"
    blocks = []
    current_block = []
    for line in lines:
        if "% Media Spend" in line:
            if current_block:
                blocks.append(" ".join(current_block).strip())
            current_block = [line]
        else:
            current_block.append(line)
    if current_block:
        blocks.append(" ".join(current_block).strip())

    # Extract fields per block
    for block in blocks:

        # Normalize characters
        cleaned = block.replace("–", "-").replace("—", "-")

        # Financials
        fin_match = re.search(r"([\d,]+)\s+([\d.]+)\s+([\d,]+\.\d{2})", cleaned)
        quantity = fin_match.group(1).replace(",", "") if fin_match else ""
        unit_price = fin_match.group(2) if fin_match else ""
        amount = fin_match.group(3).replace(",", "") if fin_match else ""

        # Account ID
        account_match = re.search(r"Account ID[:\s]+([\d\-]{7,})", cleaned)
        account_id = account_match.group(1) if account_match else ""

        # Advertiser
        adv_match = re.search(r"Advertiser:\s*(.*?)\s+ID:\s*(\d{12,})", cleaned)
        if adv_match:
            advertiser_name = adv_match.group(1).strip()
            advertiser_id = adv_match.group(2).strip()
        else:
            # Fallback for advertiser name
            adv_fallback = re.search(r"Advertiser:\s*(.*?)(?=ID:|Account ID|[\d]{1,3}[,\d]{3})", cleaned)
            advertiser_name = adv_fallback.group(1).strip() if adv_fallback else ""

            # Fallback for advertiser ID
            id_fallback = re.search(r"\b(\d{12,})\b", cleaned)
            advertiser_id = id_fallback.group(1).strip() if id_fallback else ""


        rows.append({
            "InvoiceType": "Search Ads 360",
            "Invoice#": invoice_num,
            "Month": invoice_month,
            "DueDate": due_date_value,
            "filename": filename,
            "RowType": "detail",
            "AdvertiserName": advertiser_name,
            "AdvertiserID": advertiser_id,
            "Campaign": "",
            "CampaignID": account_id,
            "BillingCode": "",
            "Fee": "% Media Spend",
            "UoM": "",
            "Unit Price": unit_price,
            "Quantity": quantity,
            "Amount($)": amount,
        })

    # Summary
    subtotal_match = re.search(r"TOTAL AMOUNT \(USD\)\s*\$?([\d,]+\.\d{2})", full_text, re.IGNORECASE)
    subtotal_value = subtotal_match.group(1).replace(",", "") if subtotal_match else ""
    rows.append({
        "InvoiceType": "Search Ads 360",
        "Invoice#": invoice_num,
        "Month": invoice_month,
        "DueDate": due_date_value,
        "filename": filename,
        "RowType": "summary",
        "AdvertiserName": "",
        "AdvertiserID": "",
        "Campaign": "",
        "CampaignID": "",
        "BillingCode": "",
        "Fee": "Subtotal",
        "UoM": "",
        "Unit Price": "",
        "Quantity": "",
        "Amount($)": subtotal_value
    })
    
    df = pd.DataFrame(rows)

    # Remove any completely empty or junk rows
    df = df[~((df["Amount($)"] == "") & 
            (df["AdvertiserName"] == "") & 
            (df["AdvertiserID"] == "") & 
            (df["CampaignID"] == ""))]

    return df

