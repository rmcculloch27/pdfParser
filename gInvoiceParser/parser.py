import pdfplumber
import os
import pandas as pd
from pathlib import Path
from .extractor.dv360 import extract_dv360
from .extractor.cm360 import extract_cm360
from .extractor.google_ads import extract_google_ads
from .extractor.linkedin import extract_linkedin
from .extractor.google_workspace import extract_google_workspace
from collections.abc import Iterable

class SuperHeroFlex:
    def __init__(self, file_paths_or_dir):
        if isinstance(file_paths_or_dir, str) and Path(file_paths_or_dir).is_dir():
            self.file_paths = list(Path(file_paths_or_dir).rglob("*.pdf"))
        elif isinstance(file_paths_or_dir, Iterable) and not isinstance(file_paths_or_dir, str):
            self.file_paths = [Path(p) for p in file_paths_or_dir]
        else:
            self.file_paths = [Path(file_paths_or_dir)]

    def identify_product_static(self, text):
        text = text.lower()
        if "campaign manager 360" in text or "cm360" in text:
            return "CM360"
        elif "display and video 360" in text or "dv360" in text:
            return "DV360"
        elif "google ads" in text:
            return "Google Ads"
        elif "linkedin" in text:
            return "LinkedIn"
        elif "google workspace" in text:
            return "Google Workspace"
        return "Unknown"

    def extract_all(self):
        all_rows = []

        for path in self.file_paths:
            filename = os.path.basename(path)

            try:
                with pdfplumber.open(path) as pdf:
                    first_page_text = pdf.pages[0].extract_text() or ""
                    product = self.identify_product_static(first_page_text)

                    if not product or product == "Unknown":
                        print(f"⚠️ Could not identify product for {filename}")
                        continue

                    if product == "Google Ads":
                        table_pages = pdf.pages[2:]
                    else:
                        table_pages = pdf.pages[1:]

                    detail_text = "\n".join([p.extract_text() or "" for p in table_pages])

                    tables = []
                    for page in table_pages:
                        tbl = page.extract_table()
                        if tbl:
                            tables.append(tbl)

                    result = self.extract_by_product(first_page_text, tables, detail_text, product, filename)

                    if not result:
                        print(f"[INFO] No rows returned for {filename} (type: {product})")
                        continue

                    if isinstance(result, tuple) and len(result) == 2:
                        summary_df, detail_df = result

                        if isinstance(summary_df, list):
                            summary_df = pd.DataFrame(summary_df)
                        if isinstance(detail_df, list):
                            detail_df = pd.DataFrame(detail_df)

                        if summary_df is not None and not summary_df.empty:
                            summary_df["filename"] = filename
                            summary_df["RowType"] = "summary"
                            all_rows.extend(summary_df.to_dict(orient="records"))

                        if detail_df is not None and not detail_df.empty:
                            detail_df["filename"] = filename
                            detail_df["RowType"] = "detail"
                            all_rows.extend(detail_df.to_dict(orient="records"))



                    elif isinstance(result, list) and isinstance(result[0], dict):
                        for row in result:
                            row["filename"] = filename
                            row["RowType"] = "detail"
                            all_rows.append(row)

                    else:
                        print(f"[WARNING] Unrecognized return format for {filename}")

            except Exception as e:
                print(f"[ERROR] Failed processing {filename}: {e}")
                all_rows.append({
                    "InvoiceType": "Error",
                    "Invoice#": "N/A",
                    "Month": "N/A",
                    "filename": filename,
                    "RowType": "error",
                    "Error": f"Error processing {filename}: {str(e)}"
                })

        return pd.DataFrame(all_rows)

    def extract_by_product(self, full_text, tables, detail_text, product, filename):
        if product == "CM360":
            return extract_cm360(full_text, detail_text, full_text, tables)
        elif product == "DV360":
            return extract_dv360(full_text, tables, detail_text, filename)
        elif product == "Google Ads":
            return extract_google_ads(full_text, tables, detail_text, filename)
        elif product == "LinkedIn":
            return extract_linkedin(full_text, tables, detail_text, filename)
        elif product == "Google Workspace":
            return extract_google_workspace(full_text, tables, detail_text, filename)
        else:
            return [{
                "InvoiceType": "Unknown",
                "Invoice#": "N/A",
                "Month": "N/A",
                "Description": "Unknown format",
                "Error": f"No line items extracted for {filename}"
            }]

