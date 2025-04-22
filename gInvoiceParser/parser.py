from pathlib import Path
import re
import pdfplumber
import pandas as pd
from gInvoiceParser.extractor.dv360 import extract_dv360
from gInvoiceParser.extractor.cm360 import extract_cm360
from gInvoiceParser.extractor.google_ads import extract_google_ads
from gInvoiceParser.extractor.linkedin import extract_linkedin
from gInvoiceParser.extractor.google_workspace import extract_google_workspace
from gInvoiceParser.extractor.sa360 import extract_sa360
# Constants
DEBUG_MODE = False

# Extractor mapping
extractor_map = {
    "CM360": extract_cm360,
    "DV360": extract_dv360,
    "GOOGLE_ADS": extract_google_ads,
    "GOOGLE_WORKSPACE": extract_google_workspace,
    "LINKEDIN": extract_linkedin,
    "SA360": extract_sa360,
}

# Helper Functions
def build_text_dict(pdf):
    return {f"page_{i + 1}": {"text": page.extract_text()} for i, page in enumerate(pdf.pages)}

def extract_invoice_number(text_dict):
    full_text = "\n".join(p.get("text", "") for p in text_dict.values())
    match = re.search(r"Invoice number[:\s]*([0-9]{7,})", full_text, re.IGNORECASE)
    return match.group(1) if match else None

def extract_invoice_month(text_dict):
    full_text = "\n".join(p.get("text", "") for p in text_dict.values())
    match = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\s*[-–]\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}", full_text)
    return match.group(0) if match else None

def dump_text_debug(text_dict):
    print("\n--- DEBUG: Raw Page Text ---")
    for page, data in text_dict.items():
        print(f"\n{page.upper()}:\n{data.get('text', '')}")

def dump_account_blocks(text_dict):
    for page, data in text_dict.items():
        text = data.get("text", "")
        accounts = re.findall(r"Account ID:\s*\d+", text)
        if accounts:
            print(f"\n{page.upper()} ACCOUNTS:\n" + "\n".join(accounts))

# Main Parser Class
class SuperHeroFlex:
    def __init__(self, pdf_dir: str=None, file_paths: list[str] = None):
        self.pdf_dir = Path(pdf_dir) if pdf_dir else None
        self.file_paths = [Path(p) for p in file_paths] if file_paths else []

        if not self.pdf_dir and not self.file_paths:
            raise ValueError("Must provide either a pdf_dir or file_paths.")
        self.results = []
        self.extractor_map = extractor_map

    def extract_all(self) -> pd.DataFrame:
        pdf_list = self.file_paths or list(self.pdf_dir.glob("*.pdf"))
        for pdf_file in pdf_list:
            try:
                with pdfplumber.open(pdf_file) as pdf:
                    text_dict = build_text_dict(pdf)

                context = {
                    "invoice_num": extract_invoice_number(text_dict),
                    "invoice_month": extract_invoice_month(text_dict),
                    "text_dict": text_dict,
                }

                product_type = self.identify_product(text_dict)

                # SA360 override
                if product_type == "SA360":
                    full_text = "\n".join(p.get("text", "") if isinstance(p, dict) else "" for p in text_dict.values())
                    invoice_match = re.search(r"INVOICE\s+#?:?\s*(\d{5,})", full_text, re.IGNORECASE)
                    if invoice_match:
                        context["invoice_num"] = invoice_match.group(1)
                    month_from_header = re.search(r'Search Ads 360\s*[-–]\s*(\w+\s+\d{4})', full_text, re.IGNORECASE)
                    if month_from_header:
                        context["invoice_month"] = month_from_header.group(1)

                extractor = self.get_extractor(product_type)

                if extractor:
                    full_path = str(pdf_file.resolve())
                    try:
                        df = extractor(
                            text_dict,
                            context.get("invoice_num", ""),
                            full_path,
                            context.get("invoice_month", "")
                        )

                        # Support both single df and (df_summary, df_detail) formats
                        if isinstance(df, tuple):
                            for d in df:
                                if isinstance(d, pd.DataFrame) and not d.empty:
                                    self.results.append(d)
                        elif isinstance(df, pd.DataFrame) and not df.empty:
                            self.results.append(df)
                        else:
                            print(f"[INFO] No rows returned for {pdf_file.name} (type: {product_type})")

                    except Exception as inner:
                        print(f"[ERROR] Extractor failed for {pdf_file.name}: {inner}")
                        continue
                else:
                    print(f"[WARNING] No extractor found for {pdf_file.name}")

            except Exception as e:
                print(f"[CRITICAL] Failed processing {pdf_file}: {e}")

        return pd.concat(self.results, ignore_index=True) if self.results else pd.DataFrame()


    def identify_product(self, text_dict) -> str:
        full_text = "\n".join(p.get("text", "") for p in text_dict.values())
        if "Campaign Manager 360" in full_text:
            return "CM360"
        elif "Google Ads" in full_text:
            return "GOOGLE_ADS"
        elif "Google Workspace" in full_text:
            return "GOOGLE_WORKSPACE"
        elif "LinkedIn" in full_text:
            return "LINKEDIN"
        elif "Display and Video 360" in full_text or "Display & Video 360" in full_text:
            return "DV360"
        elif "Search Ads 360" in full_text:
            return "SA360"
        else:
            return "UNKNOWN"


    def get_extractor(self, product_type):
        return self.extractor_map.get(product_type)

    def find_missing(self, df):
        expected_fields = [
            "InvoiceType", "Invoice#", "Month", "filename", "RowType", "AdvertiserName",
            "AdvertiserID", "Campaign", "CampaignID", "BillingCode", "Fee", "UoM",
            "Unit Price", "Quantity", "Amount($)"
        ]
        missing = [f for f in expected_fields if f not in df.columns]
        if missing:
            print("[WARNING] Missing fields:", missing)
        return missing
