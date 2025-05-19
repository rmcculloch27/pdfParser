import re
import pandas as pd
from pathlib import Path
from typing import Union

def buffer_blocks_dv360(detail_text: str) -> list[str]:
    fee_starts = (
        "Media Cost", "Platform Fee", "Data Fee",
        "Overdelivery", "Previous month"
    )

    lines = [line.strip() for line in detail_text.splitlines() if line.strip()]
    blocks = []
    buffer = []
    in_block = False

    for line in lines:
        if any(line.startswith(keyword) for keyword in fee_starts):
            if buffer:
                blocks.append("\n".join(buffer).strip())
            buffer = [line]
            in_block = True
            continue

        if in_block:
            buffer.append(line)
            if re.search(r"\b\d{10}\b", line):
                blocks.append("\n".join(buffer).strip())
                buffer = []
                in_block = False

    if buffer:
        blocks.append("\n".join(buffer).strip())

    print(f"\n[DEBUG] DV360 buffered {len(blocks)} blocks (using fee-type and advertiser ID logic).")
    for j, b in enumerate(blocks[:12]):
        print(f"\n[BLOCK {j+1}]\n{'='*60}\n{b}\n{'='*60}")

    return blocks


def extract_dv360(text_dict, invoice_num: str, filename: str, invoice_month: str) -> Union[pd.DataFrame, None]:
    rows = []
    summary_text = text_dict.get("page_1", {}).get("text", "")
    detail_text = "\n".join(
        text_dict.get(k, {}).get("text", "") for k in sorted(text_dict) if k != "page_1"
    )

    invoice_number_match = re.search(r"Invoice number[:\s]*([\d\-]+)", summary_text, re.IGNORECASE)
    date_range_match = re.search(r"Summary for\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\s*[-–]\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})", summary_text)
    amount_match = re.search(r"Total amount due.*?\$([\d,]+\.\d{2})", summary_text)
    due_date_match = re.search(r"Due\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})", summary_text)

    invoice_number = invoice_number_match.group(1) if invoice_number_match else invoice_num
    month = f"{date_range_match.group(1)} - {date_range_match.group(2)}" if date_range_match else invoice_month
    total_amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0.0
    due_date = due_date_match.group(1) if due_date_match else ""

    summary_text_clean = re.sub(r'[\s\.]+', '', summary_text)
    billing_code_match = re.search(r'BillingID[:\s]*([\d]{4}-[\d]{4}-[\d]{4})', summary_text_clean)
    billing_id = billing_code_match.group(1) if billing_code_match else None

    rows.append({
        "InvoiceType": "Display and Video 360",
        "Invoice#": invoice_number,
        "Month": month,
        "DueDate": due_date,
        "filename": Path(filename).name,
        "RowType": "summary",
        "FeeType": "Total",
        "Partner": "SUMMARY",
        "PartnerID": "SUMMARY",
        "AdvertiserName": "SUMMARY",
        "AdvertiserID": "SUMMARY",
        "BillingCode": billing_id,
        "Amount($)": total_amount
    })

    page_text_map = {
        k: v.get("text", "") 
        for k, v in sorted(text_dict.items()) 
        if k != "page_1" and "page_" in k
    }

    all_blocks = []
    for page_id, text in page_text_map.items():
        print(f"\n[DEBUG] Processing {page_id}")
        page_blocks = buffer_blocks_dv360(text)
        for b in page_blocks:
            all_blocks.append((page_id, b))

    for i, (page, block) in enumerate(all_blocks):
        if not block.strip():
            continue

        print(f"\n[DEBUG] Parsing Block {i}:\n{'='*60}\n{block}\n{'='*60}")

        fee_type_match = re.match(r"(Media Cost|Platform Fee|Data Fee|Overdelivery.*?|Previous month.*?)\b", block, re.IGNORECASE)
        partner_match = re.search(r"Partner:\s*(.+?)\s*-\s*(?:US|Constellation)\s+ID", block)
        partner_id_match = re.search(r'Partner:.*?-\s*(?:US|Constellation)\s+ID[:\s]*(\d{5,})', block, re.IGNORECASE)

        partner = partner_match.group(1).strip() if partner_match else None
        partner_id = partner_id_match.group(1).strip() if partner_id_match else None

        if not partner_id:
            lines = block.splitlines()
            for idx, line in enumerate(lines):
                match_inline = re.search(r"\b(\d{6,})\b\s*-\s*Advertiser", line)
                if match_inline:
                    partner_id = match_inline.group(1)
                    break
                if idx + 1 < len(lines) and "Advertiser" in lines[idx + 1]:
                    alt_match = re.search(r"\b(\d{10})\b", line)
                    if alt_match:
                        partner_id = alt_match.group(1)
                        break

        quantity_match = re.search(r"(\d+)\s+EA", block)
        quantity = int(quantity_match.group(1)) if quantity_match else None

        amount_match = re.search(r"(-?\$?[\d,]+\.\d{2})", block)
        amount = float(amount_match.group(1).replace(",", "")) if amount_match else None

        advertiser_match = re.search(r"Advertiser:\s*([\w\s&\-]+?)\s*ID", block)
        advertiser_id_match = re.search(r"Advertiser.*?ID:\s*(\d{6,})", block)

        advertiser_id = advertiser_id_match.group(1) if advertiser_id_match else None
        advertiser_name = advertiser_match.group(1).strip() if advertiser_match else None

        if not advertiser_id or not advertiser_name:
            lines = block.splitlines()
            for i, line in enumerate(lines):
                if "Advertiser:" in line:
                    name_fragment = line.replace("Advertiser:", "").strip()
                    candidate_lines = lines[i+1:i+4]
                    for cline in candidate_lines:
                        if "ID" in cline and re.search(r"\d{6,}", cline):
                            break
                        name_fragment += " " + cline.strip()
                    advertiser_name = advertiser_name or name_fragment.strip(" -")
                    for cline in candidate_lines:
                        match = re.search(r"ID[:\s]*(\d{6,})", cline)
                        if match:
                            advertiser_id = advertiser_id or match.group(1)
                            break
                    break

            # Promoted fallback: Look for 10-digit advertiser ID after 'Advertiser ... ID'
            for idx, line in enumerate(lines):
                if "Advertiser" in line and "ID" in line:
                    for lookahead in lines[idx+1:idx+5]:
                        if re.fullmatch(r"\d{10}", lookahead.strip()):
                            candidate_id = lookahead.strip()
                            if candidate_id != partner_id:
                                advertiser_id = candidate_id
                                print(f"[DEBUG] Promoted fallback advertiser ID found: {advertiser_id}")
                                break
                    break

            if not advertiser_id:
                match = re.search(r"(?<!\d)(\d{10})(?!\d)", block)
                if match:
                    candidate_id = match.group(1)
                    if candidate_id != partner_id:
                        advertiser_id = candidate_id

        row = {
            "InvoiceType": "Display and Video 360",
            "Invoice#": invoice_number,
            "SourcePage": page,
            "Month": month,
            "DueDate": due_date,
            "filename": Path(filename).name,
            "RowType": "detail",
            "FeeType": fee_type_match.group(1) if fee_type_match else None,
            "Partner": partner,
            "PartnerID": partner_id,
            "AdvertiserName": advertiser_name,
            "AdvertiserID": advertiser_id,
            "Quantity": quantity,
            "UOM": "EA" if quantity_match else None,
            "Amount($)": amount,
        }

        rows.append(row)

    return pd.DataFrame(rows)


