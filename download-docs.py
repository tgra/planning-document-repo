import csv
import os
import re
import requests
from urllib.parse import urlparse

INPUT_CSV = "planning_documents.csv"
OUTPUT_DIR = "downloads"

def safe_filename(text):
    text = text.strip().replace('"', '')
    text = re.sub(r'[^a-zA-Z0-9_\-\. ]', '_', text)
    text = re.sub(r'\s+', '_', text)
    return text[:150]

def is_valid_url(url):
    # Ignore Swindon docKey links
    return "omt-server/omt.html#docKey=" not in url

def download_file(url, filepath):
    try:
        response = requests.get(url, stream=True, timeout=30, verify=False)  # <--- disable SSL check
        response.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"[OK] {filepath}")
    except Exception as e:
        print(f"[FAIL] {url} -> {e}")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(INPUT_CSV, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)

        for row in reader:
            if len(row) < 3:
                continue

            application_ref = safe_filename(row[0])
            url = row[1].strip()
            metadata = row[2]

            if not is_valid_url(url):
                print(f"[SKIP docKey] {url}")
                continue

            app_folder = os.path.join(OUTPUT_DIR, application_ref)
            os.makedirs(app_folder, exist_ok=True)

            parsed = urlparse(url)
            ext = os.path.splitext(parsed.path)[1] or ".pdf"

            filename = safe_filename(metadata) + ext
            filepath = os.path.join(app_folder, filename)

            if os.path.exists(filepath):
                print(f"[SKIP exists] {filepath}")
                continue

            download_file(url, filepath)

if __name__ == "__main__":
    main()