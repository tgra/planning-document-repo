import csv
import os
import re
import time
import random
from pathlib import Path
from subprocess import run
from playwright.sync_api import sync_playwright

INPUT_CSV = "planning_clean.csv"
OUTPUT_DIR = "downloads"
BATCH_SIZE = 5  # Number of files per commit

def safe_filename(text):
    """Make a safe filename from a string."""
    text = text.strip().replace('"', '')
    text = re.sub(r'[^a-zA-Z0-9_\-\. ]', '_', text)
    text = re.sub(r'\s+', '_', text)
    return text[:150]

def go_to_documents_tab(page):
    """Ensure we are on the Documents tab."""
    if "activeTab=documents" not in page.url:
        if "?" in page.url:
            url = re.sub(r'(&|\?)activeTab=\w+', '', page.url)
            sep = "&" if "?" in url else "?"
            page.goto(f"{url}{sep}activeTab=documents", timeout=30000)
        else:
            page.goto(page.url + "?activeTab=documents", timeout=30000)

def git_commit_batch(new_files):
    """Stage and commit a batch of new files."""
    if not new_files:
        return
    try:
        run(["git", "config", "--global", "user.name", "github-actions"], check=True)
        run(["git", "config", "--global", "user.email", "github-actions@github.com"], check=True)
        run(["git", "add"] + new_files, check=True)
        run(["git", "diff-index", "--quiet", "HEAD"] or ["git", "commit", "-m", f"Add {len(new_files)} documents [skip ci]"], check=False)
        run(["git", "commit", "-m", f"Add {len(new_files)} documents [skip ci]"], check=False)
        run(["git", "push"], check=True)
        print(f"[GIT] Committed {len(new_files)} files.")
    except Exception as e:
        print(f"[GIT FAIL] {e}")

def download_documents_table(page, folder, batch_files):
    """Download all files in the Documents table, skipping existing ones."""
    try:
        page.wait_for_selector("table#Documents tbody tr", timeout=15000)
    except:
        print("No documents table found.")
        return

    rows = page.query_selector_all("table#Documents tbody tr")
    for row in rows:
        if row.query_selector("th"):
            continue  # skip header row

        try:
            link = row.query_selector("td:last-child a")
            if not link:
                continue
        except:
            continue

        try:
            with page.expect_download() as download_info:
                link.click()
            download = download_info.value
            suggested_name = download.suggested_filename
            filepath = os.path.join(folder, suggested_name)

            if os.path.exists(filepath) and Path(filepath).stat().st_size > 1000:
                print(f"[SKIP exists] {suggested_name}")
                continue

            download.save_as(filepath)
            print(f"[OK] {suggested_name}")

            batch_files.append(filepath)

            # Commit batch if reached batch size
            if len(batch_files) >= BATCH_SIZE:
                git_commit_batch(batch_files.copy())
                batch_files.clear()

            time.sleep(0.5 + random.random() * 1)

        except Exception as e:
            print(f"[FAIL] {link} -> {e}")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    batch_files = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        with open(INPUT_CSV, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                application_ref = safe_filename(row.get("ref", "unknown"))
                url = row.get("link") or row.get("url")
                if not url:
                    continue

                folder = os.path.join(OUTPUT_DIR, application_ref)
                os.makedirs(folder, exist_ok=True)

                print(f"\n[OPEN] {application_ref}")
                try:
                    page.goto(url, timeout=30000)
                    go_to_documents_tab(page)
                    download_documents_table(page, folder, batch_files)

                except Exception as e:
                    print(f"[ERROR] {url} -> {e}")

                time.sleep(1 + random.random())

        # Commit any remaining files after loop ends
        if batch_files:
            git_commit_batch(batch_files.copy())
            batch_files.clear()

        browser.close()

if __name__ == "__main__":
    main()