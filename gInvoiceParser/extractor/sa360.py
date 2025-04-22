# import re
# import logging
# from typing import List, Dict
# import pandas as pd

# def extract_sa360(text_dict: Dict, invoice_num: str, filename: str, invoice_month: str) -> pd.DataFrame:
#     results = []

#     full_text = "\n".join(p.get("text", "") for p in text_dict.values())
#     text_lines = full_text.splitlines()

#     # Fallback 1: Compact one-line pattern
#     primary_pattern = re.compile(
#         r"Advertiser:\s*(.+?)\s+ID:\s*(\d+)\s*-\s*.*?Account ID:\s*([\d-]+)\s*"
#         r"([\d,]+)\s+([\d.]+)\s+([\d,]+\.\d{2})",
#         re.IGNORECASE,
#     )
#     for match in primary_pattern.finditer(full_text):
#         results.append({
#             "InvoiceType": "Search Ads 360",
#             "Invoice#": invoice_num,
#             "Month": invoice_month,
#             "filename": filename,
#             "RowType": "detail",
#             "AdvertiserName": match.group(1).strip(),
#             "AdvertiserID": match.group(2),
#             "CampaignID": "",
#             "Campaign": "",
#             "BillingCode": "",
#             "Fee": "% Media Spend",
#             "UoM": "",
#             "Unit Price": match.group(5),
#             "Quantity": match.group(4).replace(",", ""),
#             "Amount($)": match.group(6).replace(",", ""),
#         })

#     if results:
#         logging.info(f"[Fallback1] Found {len(results)} via primary pattern")
#         return pd.DataFrame(results)

#     # Fallback 2: Token block with backscan
#     block_pattern = re.compile(r"Advertiser:\s*(.+?)\s+ID:\s*(\d+).*?Account ID:\s*([\d-]+)", re.IGNORECASE)
#     amount_pattern = re.compile(r"([\d,]+)\s+([\d.]+)\s+([\d,]+\.\d{2})")

#     blocks = full_text.split("% Media Spend")
#     for block in blocks:
#         block = "% Media Spend " + block.strip()
#         block_match = block_pattern.search(block)
#         amount_match = amount_pattern.search(block)

#         if block_match and amount_match:
#             results.append({
#                 "InvoiceType": "Search Ads 360",
#                 "Invoice#": invoice_num,
#                 "Month": invoice_month,
#                 "filename": filename,
#                 "RowType": "detail",
#                 "AdvertiserName": block_match.group(1).strip(),
#                 "AdvertiserID": block_match.group(2),
#                 "CampaignID": "",
#                 "Campaign": "",
#                 "BillingCode": "",
#                 "Fee": "% Media Spend",
#                 "UoM": "",
#                 "Unit Price": amount_match.group(2),
#                 "Quantity": amount_match.group(1).replace(",", ""),
#                 "Amount($)": amount_match.group(3).replace(",", ""),
#             })
#         else:
#             logging.debug(f"[Fallback2] Unmatched block:\n{block}\n---")

#     if results:
#         logging.info(f"[Fallback2] Recovered {len(results)} via token backscan")
#         return pd.DataFrame(results)

#     # Fallback 3: Line-by-line
#     current_advertiser = ""
#     current_id = ""
#     current_account = ""

#     for line in text_lines:
#         if "advertiser:" in line.lower():
#             adv_match = re.search(r"Advertiser:\s*(.+?)\s+ID:\s*(\d+)", line, re.IGNORECASE)
#             acc_match = re.search(r"Account ID:\s*([\d-]+)", line)
#             if adv_match:
#                 current_advertiser = adv_match.group(1).strip()
#                 current_id = adv_match.group(2).strip()
#             if acc_match:
#                 current_account = acc_match.group(1).strip()
#         elif re.search(r"\d{1,3}(,\d{3})*\s+\d+\.\d+\s+\d{1,3}(,\d{3})*\.\d{2}", line):
#             parts = re.findall(r"([\d,]+)\s+([\d.]+)\s+([\d,]+\.\d{2})", line)
#             if parts:
#                 qty, rate, amt = parts[0]
#                 results.append({
#                     "InvoiceType": "Search Ads 360",
#                     "Invoice#": invoice_num,
#                     "Month": invoice_month,
#                     "filename": filename,
#                     "RowType": "detail",
#                     "AdvertiserName": current_advertiser,
#                     "AdvertiserID": current_id,
#                     "CampaignID": "",
#                     "Campaign": "",
#                     "BillingCode": "",
#                     "Fee": "% Media Spend",
#                     "UoM": "",
#                     "Unit Price": rate,
#                     "Quantity": qty.replace(",", ""),
#                     "Amount($)": amt.replace(",", ""),
#                 })

#     if results:
#         logging.info(f"[Fallback3] Recovered {len(results)} via line-wise")
#         return pd.DataFrame(results)

#     # Fallback 4: Loose triplets
#     triplets = re.findall(r"([\d,]+)\s+([\d.]+)\s+([\d,]+\.\d{2})", full_text)
#     for qty, rate, amt in triplets:
#         results.append({
#             "InvoiceType": "Search Ads 360",
#             "Invoice#": invoice_num,
#             "Month": invoice_month,
#             "filename": filename,
#             "RowType": "detail",
#             "AdvertiserName": "",
#             "AdvertiserID": "",
#             "CampaignID": "",
#             "Campaign": "",
#             "BillingCode": "",
#             "Fee": "% Media Spend",
#             "UoM": "",
#             "Unit Price": rate,
#             "Quantity": qty.replace(",", ""),
#             "Amount($)": amt.replace(",", ""),
#         })

#     if results:
#         logging.info(f"[Fallback4] Recovered {len(results)} via triplets")
#     else:
#         logging.info(f"No detail rows returned for {filename} (SA360)")

#     return pd.DataFrame(results)







# import re
# import pandas as pd

# def extract_sa360(filename, text_dict, context, full_text):
#     rows = []

#     invoice_type = "Search Ads 360"
#     invoice_num = context.get("invoice_num", "")
#     invoice_month = context.get("invoice_month", "")
#     joined_text = "\n".join(p.get("text", "") for p in text_dict.values())
#     lines = joined_text.splitlines()

#     # --------------------
#     # Primary Pattern
#     # --------------------
#     primary_pattern = re.compile(
#         r"Advertiser:\s*(.*?)\s*ID:\s*(\d+)\s*-\s*02/2025\s*-\s*Account ID:\s*([\d-]+)\s*(.*?)\s*([\d,]+)\s*([\d.]+)\s*([\d,]+)",
#         re.DOTALL
#     )

#     for match in primary_pattern.finditer(joined_text):
#         advertiser, advertiser_id, account_id, campaign, qty, rate, amount = match.groups()
#         row = {
#             "InvoiceType": invoice_type,
#             "Invoice#": invoice_num,
#             "Month": invoice_month,
#             "filename": filename,
#             "RowType": "detail",
#             "AdvertiserName": advertiser.strip(),
#             "AdvertiserID": advertiser_id.strip(),
#             "CampaignID": account_id.strip(),
#             "Campaign": campaign.strip(),
#             "BillingCode": "",
#             "Fee": "% Media Spend",
#             "UoM": "",
#             "Unit Price": rate.strip(),
#             "Quantity": qty.replace(",", "").strip(),
#             "Amount($)": amount.replace(",", "").strip(),
#         }
#         rows.append(row)

#     if rows:
#         return pd.DataFrame(rows)

#     print("[INFO] Primary SA360 pattern failed, trying fallback strategies...")

#     # --------------------
#     # Fallback Strategy 1: Token-wise Block Parse
#     # --------------------
#     blocks = []
#     current_block = []

#     for line in lines:
#         if "% Media Spend" in line:
#             if current_block:
#                 blocks.append("\n".join(current_block))
#             current_block = [line]
#         elif current_block:
#             current_block.append(line)
#     if current_block:
#         blocks.append("\n".join(current_block))

#     fallback_pattern = re.compile(
#         r"Advertiser:\s*(.*?)\s*ID[:\s]*(\d+).*?Account ID[:\s]*(\d{3}-\d{3}-\d{4}).*?([\d,]+)\s+([\d.]+)\s+([\d,]+)",
#         re.DOTALL
#     )

#     for block in blocks:
#         match = fallback_pattern.search(block)
#         if match:
#             advertiser, advertiser_id, account_id, qty, rate, amount = match.groups()
#             row = {
#                 "InvoiceType": invoice_type,
#                 "Invoice#": invoice_num,
#                 "Month": invoice_month,
#                 "filename": filename,
#                 "RowType": "detail",
#                 "AdvertiserName": advertiser.strip(),
#                 "AdvertiserID": advertiser_id.strip(),
#                 "CampaignID": account_id.strip(),
#                 "Campaign": "",
#                 "BillingCode": "",
#                 "Fee": "% Media Spend",
#                 "UoM": "",
#                 "Unit Price": rate.strip(),
#                 "Quantity": qty.replace(",", "").strip(),
#                 "Amount($)": amount.replace(",", "").strip(),
#             }
#             rows.append(row)
#         else:
#             print("[DEBUG] SA360 unmatched block:\n", block.strip(), "\n---")

#     # --------------------
#     # Fallback Strategy 2: Join & Scan
#     # --------------------
#     if not rows:
#         join_scan_pattern = re.compile(
#             r"% Media Spend.*?Advertiser:\s*(.*?)\s*ID:\s*(\d+).*?Account ID:\s*([\d-]+).*?\n([\d,]+)\s+([\d.]+)\s+([\d,]+)",
#             re.DOTALL
#         )
#         for match in join_scan_pattern.finditer(joined_text):
#             advertiser, advertiser_id, account_id, qty, rate, amount = match.groups()
#             row = {
#                 "InvoiceType": invoice_type,
#                 "Invoice#": invoice_num,
#                 "Month": invoice_month,
#                 "filename": filename,
#                 "RowType": "detail",
#                 "AdvertiserName": advertiser.strip(),
#                 "AdvertiserID": advertiser_id.strip(),
#                 "CampaignID": account_id.strip(),
#                 "Campaign": "",
#                 "BillingCode": "",
#                 "Fee": "% Media Spend",
#                 "UoM": "",
#                 "Unit Price": rate.strip(),
#                 "Quantity": qty.replace(",", "").strip(),
#                 "Amount($)": amount.replace(",", "").strip(),
#             }
#             rows.append(row)

#     # --------------------
#     # Fallback Strategy 3: Backscan
#     # --------------------
#     if not rows:
#         i = 0
#         while i < len(lines):
#             line = lines[i]
#             if "% Media Spend" in line:
#                 advertiser_line = line
#                 if i + 3 < len(lines):
#                     qty_line = lines[i + 1]
#                     rate_line = lines[i + 2]
#                     amt_line = lines[i + 3]
#                     full_block = " ".join([advertiser_line, qty_line, rate_line, amt_line])
#                     match = re.search(r"Advertiser:\s*(.*?)\s*ID[:\s]*(\d+).*?Account ID[:\s]*(\d{3}-\d{3}-\d{4})", full_block)
#                     if match:
#                         advertiser, advertiser_id, account_id = match.groups()
#                         row = {
#                             "InvoiceType": invoice_type,
#                             "Invoice#": invoice_num,
#                             "Month": invoice_month,
#                             "filename": filename,
#                             "RowType": "detail",
#                             "AdvertiserName": advertiser.strip(),
#                             "AdvertiserID": advertiser_id.strip(),
#                             "CampaignID": account_id.strip(),
#                             "Campaign": "",
#                             "BillingCode": "",
#                             "Fee": "% Media Spend",
#                             "UoM": "",
#                             "Unit Price": rate_line.strip(),
#                             "Quantity": qty_line.strip().replace(",", ""),
#                             "Amount($)": amt_line.strip().replace(",", ""),
#                         }
#                         rows.append(row)
#                 i += 4
#             else:
#                 i += 1

#     # --------------------
#     # Summary Line (Always Add)
#     # --------------------
#     summary_match = re.search(r"SUBTOTAL.*?([\d,]+\.\d{2})", full_text, re.IGNORECASE)
#     if summary_match:
#         amount = summary_match.group(1)
#         rows.append({
#             "InvoiceType": invoice_type,
#             "Invoice#": invoice_num,
#             "Month": invoice_month,
#             "filename": filename,
#             "RowType": "summary",
#             "AdvertiserName": "",
#             "AdvertiserID": "",
#             "Campaign": "",
#             "CampaignID": "",
#             "BillingCode": "",
#             "Fee": "Subtotal",
#             "UoM": "",
#             "Unit Price": "",
#             "Quantity": "",
#             "Amount($)": amount.strip()
#         })

#     return pd.DataFrame(rows)

import re
import pandas as pd

import re
import pandas as pd

def extract_sa360(text_dict, invoice_num, filename, invoice_month):
    rows = []
    lines = "\n".join(p.get("text", "") for p in text_dict.values()).splitlines()
    buffer = []
    financial_pattern = re.compile(r"([\d,]+)\s+([\d.]+)\s+([\d,]+\.\d{2})")

    def extract_fields(block):
        advertiser_match = re.search(r"Advertiser:\s*(.+?)\s+ID[:\s]+(\d+)", block)
        account_id_match = re.search(r"Account ID[:\s]+([\d\-]+)", block)
        financial_match = financial_pattern.search(block)

        advertiser_name = advertiser_match.group(1).strip() if advertiser_match else ""
        advertiser_id = advertiser_match.group(2).strip() if advertiser_match else ""
        account_id = account_id_match.group(1).strip() if account_id_match else ""
        quantity = financial_match.group(1).replace(",", "") if financial_match else ""
        unit_price = financial_match.group(2) if financial_match else ""
        amount = financial_match.group(3).replace(",", "") if financial_match else ""

        return {
            "InvoiceType": "Search Ads 360",
            "Invoice#": invoice_num,
            "Month": invoice_month,
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
        }

    # Normalize and parse blocks
    lines = [line.strip() for line in lines if line.strip()]
    for line in lines:
        buffer.append(line)
        block = " ".join(buffer)
        if financial_pattern.search(block) and "Advertiser:" in block:
            rows.append(extract_fields(block))
            buffer = []

    # Append summary from printed total, not calculated
    full_text = "\n".join(lines)
    subtotal_match = re.search(r"TOTAL AMOUNT \(USD\)\s*\$?([\d,]+\.\d{2})", full_text, re.IGNORECASE)
    subtotal_value = subtotal_match.group(1).replace(",", "") if subtotal_match else ""

    rows.append({
        "InvoiceType": "Search Ads 360",
        "Invoice#": invoice_num,
        "Month": invoice_month,
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

    return pd.DataFrame(rows)
