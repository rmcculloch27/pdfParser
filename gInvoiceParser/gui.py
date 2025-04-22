import os
import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import subprocess
import platform
from gInvoiceParser.parser import SuperHeroFlex

class InvoiceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("gInvoiceParser - PDF Invoice Extractor")
        self.file_paths = []
        self.output_file = None

        self.build_gui()

    def build_gui(self):
        frame = tk.Frame(self.root, padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Button(frame, text="Upload PDFs", command=self.browse_files, width=20).pack(pady=5)
        tk.Button(frame, text="Extract PDFs", command=self.extract_invoices, width=20).pack(pady=5)
        self.view_btn = tk.Button(frame, text="View Output", command=self.view_excel, state="disabled", width=20)
        self.view_btn.pack(pady=5)

    def browse_files(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")], title="Select PDF invoices")
        if files:
            self.file_paths = list(files)
            messagebox.showinfo("Files Selected", f"{len(files)} PDF file(s) loaded.")

    def extract_invoices(self):
        if not self.file_paths:
            messagebox.showerror("Error", "Please select PDF files to extract.")
            return

        try:
            parser = SuperHeroFlex(file_paths=self.file_paths)
            df = parser.extract_all()

            output_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
            if not output_path:
                messagebox.showinfo("Cancelled", "No file selected. Operation cancelled.")
                return

            df.to_excel(output_path, index=False)
            self.output_file = output_path
            self.view_btn.config(state="normal")
            messagebox.showinfo("Success", f"Extraction completed!\nFile saved to: {output_path}")

        except Exception as e:
            messagebox.showerror("Processing Error", f"An unexpected error occurred:\n{e}")

    def view_excel(self):
        if not self.output_file:
            messagebox.showerror("Error", "No output file to view.")
            return

        try:
            if platform.system() == "Darwin":
                subprocess.call(["open", self.output_file])
            elif platform.system() == "Windows":
                os.startfile(self.output_file)
            else:
                subprocess.call(["xdg-open", self.output_file])
        except Exception as e:
            messagebox.showerror("Error Opening File", f"Could not open file:\n{e}")

def main():
    root = tk.Tk()
    app = InvoiceApp(root)
    root.mainloop()
