import re
import pandas as pd

def extract_linkedin(text_dict, invoice_num, filename, invoice_month):
    detail_rows = []
    summary_row = {}
    campaign_block = []

    def flush_block(block):
        joined = " ".join(block)
        if "Campaign:" in joined:
            row = parse_campaign_block(joined)
            if row:
                detail_rows.append(row)
        block.clear()

    def parse_campaign_block(joined):
        campaign_match = re.search(r"Campaign:\s*(.+?)\s+(\d{1,3}(?:,\d{3})*|\d+)\.\d{2}", joined)
        if not campaign_match:
            return None

        campaign = campaign_match.group(1).strip()
        # Extract amount ($) after quantity (1)
        billed_match = re.search(r'\b1\s+([\d,]+\.\d{2})\s+0\.00', joined)
        billed_amount = billed_match.group(1).replace(',', '') if billed_match else None

        # Fallback: try to find amount based on other float patterns after "Qty" field
        if not billed_amount:
            alt_match = re.search(r'Qty\s+1\s+([\d,]+\.\d{2})', joined)
            if alt_match:
                billed_amount = alt_match.group(1).replace(',', '')

        return {
            "InvoiceType": "LinkedIn",
            "Invoice#": invoice_num,
            "Month": invoice_month,
            "Amount($)": billed_amount,
            "filename": filename,
            "RowType": "detail",
            "Quantity": 1,
            "UOM": "CPM",
            "FeeType": "",
            "Partner": "",
            "PartnerID": "",
            "AdvertiserName": "",
            "AdvertiserID": "",
            "Campaign": campaign
        }

    for page_num, page in text_dict.items():
        if "Special Instructions" in page.get("text", ""):
            summary_match = re.search(r'Total\s+([\d,]+\.\d{2})', page.get("text", ""))
            if summary_match:
                amount = summary_match.group(1).replace(",", "")
                summary_row = {
                    "InvoiceType": "LinkedIn",
                    "Invoice#": invoice_num,
                    "Month": invoice_month,
                    "Amount($)": amount,
                    "filename": filename,
                    "RowType": "summary",
                    "Description": "Total",
                    "Quantity": "",
                    "UOM": "",
                    "FeeType": "SUMMARY",
                    "Partner": "SUMMARY",
                    "PartnerID": "SUMMARY",
                    "AdvertiserName": "SUMMARY",
                    "AdvertiserID": "SUMMARY",
                    "Campaign": "TOTAL"
                }
        lines = page.get("text", "").splitlines()
        for line in lines:
            if re.match(r"^\d+\s+Campaign:", line) or line.strip().startswith("Campaign:"):
                flush_block(campaign_block)
                campaign_block.append(line)
            elif line.strip() == "":
                flush_block(campaign_block)
            else:
                campaign_block.append(line)
        flush_block(campaign_block)

    all_rows = [summary_row] if summary_row else []
    all_rows.extend(detail_rows)
    return pd.DataFrame(all_rows)
