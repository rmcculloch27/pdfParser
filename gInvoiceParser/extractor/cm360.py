import re
import pandas as pd
from typing import Union


def normalize_spacing(text):
    """
    Removes single-character spaces in words, e.g.:
    'H o r i z a n t' → 'Horizant'
    """
    return re.sub(r'(?<=\w)\s(?=\w)', '', text)


def extract_cm360(text_dict, invoice_num: str, filename: str, invoice_month: str) -> Union[pd.DataFrame, None]:
    rows = []

    full_text = "\n".join(p.get("text", "") for p in text_dict.values())
    summary_text = text_dict.get("page_1", {}).get("text", "")

    # ---------- Primary Regex ----------
    primary_pattern = re.compile(
        r'Advertiser: "(.*?)", ID:\s*(\d+)\s*-\s*Campaign:\s*"(.*?)", ID:\s*(\d+).*?Billing Code:\s*(.*?)\s*-\s*Fee:\s*(.*?)\s+(CPM|CPC)\s+([\d.]+)\s+([\d,]+)\s+([\d.]+)',
        re.DOTALL
    )
    rows_before = len(rows)
    for match in primary_pattern.finditer(full_text):
        advertiser_name, advertiser_id, campaign_name, campaign_id, billing_code, fee, uom, unit_price, quantity, amount = match.groups()
        rows.append({
            "InvoiceType": "Campaign Manager 360",
            "Invoice#": invoice_num,
            "Month": invoice_month,
            "filename": filename,
            "RowType": "detail",
            "AdvertiserName": advertiser_name.strip(),
            "AdvertiserID": advertiser_id.strip(),
            "Campaign": campaign_name.strip(),
            "CampaignID": campaign_id.strip(),
            "BillingCode": billing_code.strip(),
            "Fee": fee.strip(),
            "UoM": uom.strip(),
            "Unit Price": float(unit_price),
            "Quantity": int(quantity.replace(",", "")),
            "Amount($)": float(amount.replace(",", "")),
        })
    if len(rows) == rows_before:
        print(f"[INFO] Primary regex failed for {filename}, trying fallback strategy...")

    # ---------- Fallback 1: Line-by-line Merge ----------
    if len(rows) == rows_before:
        detail_text = "\n".join(
            text_dict.get(k, {}).get("text", "")
            for k in sorted(text_dict.keys()) if k != "page_1"
        )
        lines = detail_text.splitlines()
        merged_lines = []
        buffer = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if "Advertiser:" in line and buffer:
                merged_lines.append(buffer.strip())
                buffer = line
            else:
                buffer += " " + line
        if buffer:
            merged_lines.append(buffer.strip())

        fallback_pattern = re.compile(
            r'Advertiser: "(.*?)", ID:\s*(\d+)\s*-\s*Campaign:\s*"(.*?)", ID:\s*(\d+).*?Billing Code:\s*(.*?)\s*-\s*Fee:\s*(.*?)\s+(CPM|CPC)\s+([\d.]+)\s+([\d,]+)\s+([\d.]+)',
            re.DOTALL
        )
        for line in merged_lines:
            match = fallback_pattern.search(line)
            if match:
                advertiser_name, advertiser_id, campaign_name, campaign_id, billing_code, fee, uom, unit_price, quantity, amount = match.groups()
                rows.append({
                    "InvoiceType": "Campaign Manager 360",
                    "Invoice#": invoice_num,
                    "Month": invoice_month,
                    "filename": filename,
                    "RowType": "detail",
                    "AdvertiserName": advertiser_name.strip(),
                    "AdvertiserID": advertiser_id.strip(),
                    "Campaign": campaign_name.strip(),
                    "CampaignID": campaign_id.strip(),
                    "BillingCode": billing_code.strip(),
                    "Fee": fee.strip(),
                    "UoM": uom.strip(),
                    "Unit Price": float(unit_price),
                    "Quantity": int(quantity.replace(",", "")),
                    "Amount($)": float(amount.replace(",", "")),
                })

    # ---------- Fallback 2: Without Billing Code ----------
    if len(rows) == rows_before:
        print(f"[INFO] Trying fallback 2 for {filename}")
        pattern = re.compile(
            r'Advertiser: "(.*?)", ID:\s*(\d+)\s*-\s*Campaign:\s*"(.*?)", ID:\s*(\d+)\s*-\s*Fee:\s*(.*?)\s+(CPM|CPC)\s+([\d.]+)\s+([\d,]+)\s+([\d.]+)',
            re.DOTALL
        )
        for match in pattern.finditer(full_text):
            advertiser_name, advertiser_id, campaign_name, campaign_id, fee, uom, unit_price, quantity, amount = match.groups()
            rows.append({
                "InvoiceType": "Campaign Manager 360",
                "Invoice#": invoice_num,
                "Month": invoice_month,
                "filename": filename,
                "RowType": "detail",
                "AdvertiserName": advertiser_name.strip(),
                "AdvertiserID": advertiser_id.strip(),
                "Campaign": campaign_name.strip(),
                "CampaignID": campaign_id.strip(),
                "BillingCode": None,
                "Fee": fee.strip(),
                "UoM": uom.strip(),
                "Unit Price": float(unit_price),
                "Quantity": int(quantity.replace(",", "")),
                "Amount($)": float(amount.replace(",", "")),
            })

    # ---------- Fallback 3: Campaign line broken with trailing ID ----------
    if len(rows) == rows_before:
        print(f"[INFO] Trying fallback 3 for {filename}")
        pattern = re.compile(
            r'Advertiser: "(.*?)", ID:\s*(\d+)\s*-\s*Campaign:\s*"(.*?)"\s*, ID:\s*(\d+)\s*-\s*Fee:\s*(.*?)\s+(CPM|CPC)\s+([\d.]+)\s+([\d,]+)\s+([\d.]+)',
            re.DOTALL
        )
        for match in pattern.finditer(full_text):
            advertiser_name, advertiser_id, campaign_name, campaign_id, fee, uom, unit_price, quantity, amount = match.groups()
            rows.append({
                "InvoiceType": "Campaign Manager 360",
                "Invoice#": invoice_num,
                "Month": invoice_month,
                "filename": filename,
                "RowType": "detail",
                "AdvertiserName": advertiser_name.strip(),
                "AdvertiserID": advertiser_id.strip(),
                "Campaign": campaign_name.strip(),
                "CampaignID": campaign_id.strip(),
                "BillingCode": None,
                "Fee": fee.strip(),
                "UoM": uom.strip(),
                "Unit Price": float(unit_price),
                "Quantity": int(quantity.replace(",", "")),
                "Amount($)": float(amount.replace(",", "")),
            })

    # ---------- Fallback 4: Token-wise cleanup ----------
    # ---------- Fallback 4: Token-wise cleanup ----------
    if len(rows) == rows_before:
        print(f"[INFO] Triggering token-wise fallback for {filename}")
        tokens = full_text.replace("\n", " ").split("Advertiser:")
        for token in tokens:
            token = "Advertiser:" + token.strip()
            if "Campaign:" not in token or "Fee:" not in token:
                continue
            normalized_token = normalize_spacing(token)

            print(f"[DEBUG] Unmatched token block:\n{token}\n---")
            
            # You can try matching here again if needed (e.g., with fallback_pattern)
            token_pattern = re.compile(
                r'Advertiser:\s*"(.*?)",\s*ID:\s*(\d+)\s*-\s*Campaign:\s*"(.*?)",\s*ID:\s*(\d+)\s*-\s*Fee:\s*(.*?)\s+(CPM|CPC)\s+([\d.]+)\s+([\d,]+)\s+([\d.]+)',
                re.DOTALL
            )
            match = token_pattern.search(normalized_token)
            if match:
                advertiser_name, advertiser_id, campaign_name, campaign_id, fee, uom, unit_price, quantity, amount = match.groups()
                rows.append({
                    "InvoiceType": "Campaign Manager 360",
                    "Invoice#": invoice_num,
                    "Month": invoice_month,
                    "filename": filename,
                    "RowType": "detail",
                    "AdvertiserName": advertiser_name.strip(),
                    "AdvertiserID": advertiser_id.strip(),
                    "Campaign": campaign_name.strip(),
                    "CampaignID": campaign_id.strip(),
                    "BillingCode": None,
                    "Fee": fee.strip(),
                    "UoM": uom.strip(),
                    "Unit Price": float(unit_price),
                    "Quantity": int(quantity.replace(",", "")),
                    "Amount($)": float(amount.replace(",", "")),
                })


    # ---------- Fallback 5: Spaced-out Campaign Pattern ----------
    # ---------- Fallback 5: Spaced-out Campaign Pattern ----------
    if len(rows) == rows_before:
        print(f"[INFO] Triggering spaced-out fallback for {filename}")
        normalized_text = normalize_spacing(full_text)
        spaced_pattern = re.compile(
            r'Advertiser:\s*"(.*?)",\s*ID:\s*(\d+)\s*-\s*Campaign:\s*"(.*?)",\s*ID:\s*(\d+)\s*-\s*Fee:\s*([A-Z\s]+)\s+(CPM|CPC)\s+([\d.]+)\s+([\d,]+)\s+([\d.]+)',
            re.DOTALL
        )
        for match in spaced_pattern.finditer(normalized_text):
            advertiser_name, advertiser_id, campaign_name, campaign_id, fee, uom, unit_price, quantity, amount = match.groups()
            rows.append({
                "InvoiceType": "Campaign Manager 360",
                "Invoice#": invoice_num,
                "Month": invoice_month,
                "filename": filename,
                "RowType": "detail",
                "AdvertiserName": advertiser_name.strip(),
                "AdvertiserID": advertiser_id.strip(),
                "Campaign": campaign_name.strip(),
                "CampaignID": campaign_id.strip(),
                "BillingCode": None,
                "Fee": fee.strip(),
                "UoM": uom.strip(),
                "Unit Price": float(unit_price),
                "Quantity": int(quantity.replace(",", "")),
                "Amount($)": float(amount.replace(",", "")),
            })


    # ---------- Summary Row ----------
    summary_match = re.search(r'Subtotal in USD \$([\d,]+\.\d{2})', summary_text, re.IGNORECASE)
    if summary_match:
        amount = float(summary_match.group(1).replace(",", ""))
        rows.append({
            "InvoiceType": "Campaign Manager 360",
            "Invoice#": invoice_num,
            "Month": invoice_month,
            "filename": filename,
            "RowType": "summary",
            "AdvertiserName": None,
            "AdvertiserID": None,
            "Campaign": None,
            "CampaignID": None,
            "BillingCode": None,
            "Fee": "Subtotal",
            "UoM": None,
            "Unit Price": None,
            "Quantity": None,
            "Amount($)": amount,
        })

    if not rows:
        print(f"[INFO] No CM360 rows found in {filename}")
        return None

    return pd.DataFrame(rows)
