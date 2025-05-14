from pathlib import Path
import re
import pdfplumber
import pandas as pd
from collections import defaultdict
from gInvoiceParser.extractor.dv360 import extract_dv360
from gInvoiceParser.extractor.cm360 import extract_cm360
from gInvoiceParser.extractor.google_ads import extract_google_ads
from gInvoiceParser.extractor.linkedin import extract_linkedin
from gInvoiceParser.extractor.google_workspace import extract_google_workspace
from gInvoiceParser.extractor.sa360 import extract_sa360

extractor_map = {
    "CM360": extract_cm360,
    "DV360": extract_dv360,
    "GOOGLE_ADS": extract_google_ads,
    "GOOGLE_WORKSPACE": extract_google_workspace,
    "LINKEDIN": extract_linkedin,
    "SA360": extract_sa360,
}

def build_text_dict(pdf):
    return {f"page_{i + 1}": {"text": page.extract_text()} for i, page in enumerate(pdf.pages)}

def extract_invoice_number(text_dict):
    full_text = "\n".join(p.get("text", "") for p in text_dict.values())
    match = re.search(r"Invoice number[:\s]*([0-9]{7,})", full_text, re.IGNORECASE)
    return match.group(1) if match else None

def extract_invoice_month(text_dict):
    full_text = "\n".join(p.get("text", "") for p in text_dict.values())
    match = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\s*[-\u2013]\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}", full_text)
    return match.group(0) if match else None

class SuperHeroFlex:
    def __init__(self, pdf_dir: str = None, file_paths: list[str] = None):
        self.pdf_dir = Path(pdf_dir) if pdf_dir else None
        self.file_paths = [Path(p) for p in file_paths] if file_paths else []
        if not self.pdf_dir and not self.file_paths:
            raise ValueError("Must provide either a pdf_dir or file_paths.")
        self.results_by_product = defaultdict(list)
        self.extractor_map = extractor_map

    def extract_all(self):
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
                    full_text = "\n".join(p.get("text", "") for p in text_dict.values())
                    match = re.search(r"INVOICE\s+#?:?\s*(\d{5,})", full_text, re.IGNORECASE)
                    if match:
                        context["invoice_num"] = match.group(1)
                    month_match = re.search(r'Search Ads 360\s*[-\u2013]\s*(\w+\s+\d{4})', full_text, re.IGNORECASE)
                    if month_match:
                        context["invoice_month"] = month_match.group(1)

                extractor = self.get_extractor(product_type)
                if extractor:
                    try:
                        df = extractor(
                            context["text_dict"],
                            context["invoice_num"] or "",
                            str(pdf_file),
                            context["invoice_month"] or "",
                        )
                        if isinstance(df, tuple):
                            for d in df:
                                if isinstance(d, pd.DataFrame) and not d.empty:
                                    self.results_by_product[product_type].append(d)
                        elif isinstance(df, pd.DataFrame) and not df.empty:
                            self.results_by_product[product_type].append(df)
                        else:
                            print(f"[INFO] No rows returned for {pdf_file.name} ({product_type})")
                    except Exception as e:
                        print(f"[ERROR] Extractor failed for {pdf_file.name}: {e}")
                else:
                    print(f"[WARNING] No extractor found for {pdf_file.name}")
            except Exception as e:
                print(f"[CRITICAL] Failed processing {pdf_file}: {e}")

    def export_by_product(self, output_dir: Path):
        output_dir.mkdir(parents=True, exist_ok=True)
        for product_type, dfs in self.results_by_product.items():
            df = pd.concat(dfs, ignore_index=True)
            output_path = output_dir / f"{product_type.lower().replace(' ', '_')}_invoices.xlsx"
            df.to_excel(output_path, index=False)
            print(f"[EXPORT] {product_type}: {len(df)} rows → {output_path}")

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
