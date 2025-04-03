import re

def flatten_text_block(block):
    def recursive_flatten(item):
        if isinstance(item, list):
            for subitem in item:
                yield from recursive_flatten(subitem)
        else:
            yield item

    if isinstance(block, list):
        return "\n".join(recursive_flatten(block))
    return block

def extract_cm360(full_text: str, detail_text: str, summary_text: str, tables: list) -> list:
    details = []

    detail_text = flatten_text_block(detail_text)

    # ✅ Safe regex matches
    invoice_number_match = re.search(r"Invoice number:\s*(\d+)", detail_text)
    date_range_match = re.search(r"(\w+ \d{1,2}, \d{4})\s*-\s*(\w+ \d{1,2}, \d{4})", detail_text)
    advertiser_id_match = re.search(r"Advertiser Id:?[:\s]+(\d+)", detail_text)
    total_amount_match = re.search(r"Total (amount due|in USD)\s*\$([\d,]+\.\d{2})", detail_text, re.IGNORECASE)

    # ✅ Assign only if matches found
    invoice_number = invoice_number_match.group(1) if invoice_number_match else "N/A"
    date_range = f"{date_range_match.group(1)} - {date_range_match.group(2)}" if date_range_match else "N/A"
    advertiser_id = advertiser_id_match.group(1) if advertiser_id_match else "N/A"
    total_amount = total_amount_match.group(2) if total_amount_match else "N/A"

    details.append({
        "InvoiceType": "CM360",
        "Invoice#": invoice_number,
        "Month": date_range,
        "AdvertiserName": "SUMMARY",
        "AdvertiserID": advertiser_id,
        "Campaign": "SUMMARY",
        "CampaignID": "SUMMARY",
        "BillingCode": "SUMMARY",
        "Fee": "TOTAL",
        "UOM": "Total",
        "Unit Price": "",
        "Quantity": "",
        "Amount($)": total_amount
    })

    # ✅ Match detail rows from invoice text
    item_block_pattern = re.compile(
        r'Advertiser: "?(?P<advertiser_name>.+?)", ID:\s*(?P<advertiser_id>\d+)\s*-\s*Campaign:\s*\n?"(?P<campaign>.+?)", ID:\s*(?P<campaign_id>\d+), Billing Code:\s*(?P<billing_code>[\w\-]+)\s*-\s*Fee:\s*CPM\s+(?P<unit_price>[\d\.]+)\s+(?P<quantity>[\d,]+)\s+(?P<amount>[\d\.]+)',
        re.DOTALL
    )

    for match in item_block_pattern.finditer(detail_text):
        details.append({
            "InvoiceType": "CM360",
            "Invoice#": invoice_number,
            "Month": date_range,
            "AdvertiserName": match.group("advertiser_name").strip(),
            "AdvertiserID": match.group("advertiser_id"),
            "Campaign": match.group("campaign").strip(),
            "CampaignID": match.group("campaign_id"),
            "BillingCode": match.group("billing_code"),
            "Fee": "CPM",
            "UOM": "CPM",
            "Unit Price": float(match.group("unit_price")),
            "Quantity": int(match.group("quantity").replace(",", "")),
            "Amount($)": float(match.group("amount"))
        })

    return [], details
