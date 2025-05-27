import requests, zipfile, io, os, sys, shutil
from tkinter import messagebox

LOCAL_VERSION = "0.1.0"
VERSION_URL = "https://bitbucket.org/hs2studio/gmp-accounting-tool/src/main/version.txt"
ZIP_URL = "https://bitbucket.org/hs2studio/gmp-accounting-tool/src/main/gInvoiceParserAppBundle.zip"
APP_DIR = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))

def check_for_update():
    try:
        response = requests.get(VERSION_URL, timeout=5)
        if response.status_code == 200:
            remote_version = response.text.strip()
            if remote_version != LOCAL_VERSION:
                if messagebox.askyesno("Update Available", f"Version {remote_version} is available. Update now?"):
                    download_and_extract()
                    messagebox.showinfo("Update Complete", "Restart the app to use the latest version.")
                    sys.exit()
    except Exception as e:
        print(f"[Update] Error: {e}")

def download_and_extract():
    response = requests.get(ZIP_URL, stream=True)
    if response.status_code != 200:
        raise Exception("Failed to download update ZIP")

    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
        temp_path = os.path.join(APP_DIR, "_update_tmp")
        os.makedirs(temp_path, exist_ok=True)
        zip_ref.extractall(temp_path)

        for item in os.listdir(temp_path):
            src_path = os.path.join(temp_path, item)
            dst_path = os.path.join(APP_DIR, item)

            if os.path.isdir(src_path):
                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)
                shutil.move(src_path, dst_path)
            else:
                shutil.move(src_path, dst_path)

        shutil.rmtree(temp_path)
