import re
import pandas as pd
from typing import Union

def normalize_spacing(text):
    return re.sub(r'(?<=\w)\s(?=\w)', '', text)

def buffer_blocks(text: str) -> list:
    lines = text.splitlines()
    blocks, buffer = [], []
    for line in lines:
        if 'Advertiser:' in line:
            if buffer:
                blocks.append("\n".join(buffer))
                buffer = []
        buffer.append(line)
    if buffer:
        blocks.append("\n".join(buffer))
    return blocks

def clean_campaign(raw: str) -> str:
    if not raw:
        return None
    junk_pattern = r'\b(?:CPM|CPC|Impressions|Clicks)\b\s*[\d.,]+\s*[\d,]+\s*[\d.,]+'
    cleaned = re.sub(junk_pattern, '', raw)
    cleaned = re.sub(r'[\d.,]{3,}', '', cleaned)
    return re.sub(r'\s+', ' ', cleaned).strip()

def extract_cm360(text_dict, invoice_num: str, filename: str, invoice_month: str) -> Union[pd.DataFrame, None]:
    rows = []
    full_text = "\n".join(p.get("text", "") for p in text_dict.values())
    summary_text = text_dict.get("page_1", {}).get("text", "")

    summary_text_clean = re.sub(r'[\s\.]+', '', summary_text)
    billing_code_match = re.search(r'BillingID[:\s]*([\d]{4}-[\d]{4}-[\d]{4})', summary_text_clean)
    billing_code = billing_code_match.group(1) if billing_code_match else None

    detail_text = "\n".join(text_dict.get(k, {}).get("text", "") for k in sorted(text_dict) if k != "page_1")
    buffered_blocks = buffer_blocks(detail_text)

    for block in buffered_blocks:
        print(f"\n[DEBUG] Raw Block:\n{'='*60}\n{block}\n{'='*60}")

        # Extract financials BEFORE normalizing whitespace
        financial_match = re.search(r'\b(CPM|CPC|Impressions|Clicks)\b\s*([\d.]+)\s*([\d,]+)\s*([\d.]+)', block)
        if financial_match:
            uom = financial_match.group(1)
            try:
                unit_price = float(financial_match.group(2))
                quantity = int(financial_match.group(3).replace(",", ""))
                amount = float(financial_match.group(4))
            except:
                unit_price = quantity = amount = None
        else:
            print(f"[DEBUG] No amount match in block:\n{block}")
            unit_price = quantity = amount = uom = None

        # Normalize block
        block = normalize_spacing(block)

        advertiser_match = re.search(r'Advertiser:\s*\"(.*?)\"', block)
        campaign_match = re.search(r'Campaign:\s*\"(.*?)\"', block, re.DOTALL)
        fee_match = re.search(r'Fee:\s*([A-Z /\-]+)', block)

        if not advertiser_match or not campaign_match or not fee_match:
            continue

        # Match AdvertiserID and CampaignID separately
        id_matches = re.findall(r'ID:\s*(\d{6,})', block)
        advertiser_id = id_matches[0] if len(id_matches) > 0 else None
        campaign_id = id_matches[1] if len(id_matches) > 1 else None
        print(f"[DEBUG] ID Matches: {id_matches} → AdvertiserID: {advertiser_id}, CampaignID: {campaign_id}")

        campaign_clean = clean_campaign(campaign_match.group(1))

        print(f"[DEBUG] Parsed values — Unit Price: {unit_price}, Quantity: {quantity}, Amount: {amount}")
        print(f"[DEBUG] Extracted Amount = {amount} for Campaign = {campaign_clean}")

        row = {
            "InvoiceType": "Campaign Manager 360",
            "Invoice#": invoice_num,
            "Month": invoice_month,
            "filename": filename,
            "RowType": "detail",
            "BillingCode": None,
            "AdvertiserName": advertiser_match.group(1),
            "AdvertiserID": advertiser_id,
            "Campaign": campaign_clean,
            "CampaignID": campaign_id,
            "Fee": fee_match.group(1).strip(),
            "UoM": uom,
            "Amount($)": amount
        }

        rows.append(row)

    if not rows:
        print("[INFO] No detail rows found in blocks. Trying fallback parsing from full_text...")
        flex_pattern = re.compile(r'(CPM|Impressions|Clicks)\s+([\d.]+)\s+([\d,]+)\s+([\d,]+\.[\d]{2})')
        for match in flex_pattern.finditer(full_text):
            context = full_text[max(0, match.start() - 1000):match.start()]
            advertiser_match = re.search(r'Advertiser:\s*\"(.*?)\", ID:\s*(\d+)', context)
            campaign_match = re.search(r'Campaign:\s*\"(.*?)\"', context)
            campaign_id_match = re.search(r'ID:\s*(\d{6,})', context)
            fee_match = re.search(r'Fee:\s*([A-Z /\-]+)', context)

            campaign_clean = clean_campaign(campaign_match.group(1)) if campaign_match else None
            print(f"[DEBUG] Fallback Row — Amount: {match.group(4)}, Campaign: {campaign_clean}")

            rows.append({
                "InvoiceType": "Campaign Manager 360",
                "Invoice#": invoice_num,
                "Month": invoice_month,
                "filename": filename,
                "RowType": "detail",
                "BillingCode": None,
                "AdvertiserName": advertiser_match.group(1) if advertiser_match else None,
                "AdvertiserID": advertiser_match.group(2) if advertiser_match else None,
                "Campaign": campaign_clean,
                "CampaignID": campaign_id_match.group(1) if campaign_id_match else None,
                "Fee": fee_match.group(1).strip() if fee_match else None,
                "UoM": match.group(1),
                "Unit Price": float(match.group(2)),
                "Quantity": int(match.group(3).replace(",", "")),
                "Amount($)": float(match.group(4).replace(",", ""))
            })

    match = re.search(r'Subtotal in USD \$([\d,]+\.[\d]{2})', summary_text)
    if match:
        rows.append({
            "InvoiceType": "Campaign Manager 360",
            "Invoice#": invoice_num,
            "Month": invoice_month,
            "filename": filename,
            "RowType": "summary",
            "BillingCode": billing_code,
            "Fee": "Subtotal",
            "Amount($)": float(match.group(1).replace(",", ""))
        })

    return pd.DataFrame(rows) if rows else None
