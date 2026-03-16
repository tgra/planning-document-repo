import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from time import sleep
import os

BASE_URL = "https://pa.swindon.gov.uk"
CSV_INPUT = "planning_clean.csv"
CSV_OUTPUT = "planning_documents.csv"
CSV_TEMP = "planning_documents_temp.csv"

df = pd.read_csv(CSV_INPUT)

# If temp file exists, resume from there
if os.path.exists(CSV_TEMP):
    docs_df = pd.read_csv(CSV_TEMP)
    processed_refs = set(docs_df['application_ref'])
    print(f"Resuming: {len(processed_refs)} applications already processed.")
else:
    docs_df = pd.DataFrame(columns=["application_ref", "document_title", "document_link", "document_meta"])
    processed_refs = set()

headers = {"User-Agent": "Mozilla/5.0"}

print(f"Starting document extraction for {len(df)} applications...")

for idx, row in df.iterrows():
    ref = row['Reference']
    if ref in processed_refs:
        print(f"[{idx+1}/{len(df)}] Skipping already processed application: {ref}")
        continue
    
    try:
        link = row["link"]
        print(f"[{idx+1}/{len(df)}] Processing application: {ref}")
        
        response = requests.get(link, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"  Warning: Failed to fetch page ({response.status_code})")
            continue
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        documents_tab = soup.find("a", id=re.compile(r"tab_documents"))
        if not documents_tab:
            print("  No documents tab found for this application.")
            continue
        
        doc_url = documents_tab["href"]
        doc_page = requests.get(BASE_URL + doc_url, headers=headers, timeout=10)
        if doc_page.status_code != 200:
            print(f"  Warning: Failed to fetch documents page ({doc_page.status_code})")
            continue
        
        doc_soup = BeautifulSoup(doc_page.text, "html.parser")
        doc_count = 0
        
        for li in doc_soup.select("ul li, table tr"):
            a = li.find("a")
            if a:
                title = a.get_text(strip=True)
                href = a.get("href")
                full_link = BASE_URL + href if href else None
                meta = li.get_text(" ", strip=True)
                
                docs_df = pd.concat([docs_df, pd.DataFrame([{
                    "application_ref": ref,
                    "document_title": title,
                    "document_link": full_link,
                    "document_meta": meta
                }])], ignore_index=True)
                
                doc_count += 1
        
        print(f"  Extracted {doc_count} documents.")

        # save temp file after each application
        docs_df.to_csv(CSV_TEMP, index=False)
        
        sleep(0.5)
    
    except Exception as e:
        print(f"  Error processing application {ref}: {e}")

# Save final output
docs_df.to_csv(CSV_OUTPUT, index=False)
print(f"\nFinished! Extracted a total of {len(docs_df)} documents across all applications.")
# Remove temp file after successful completion
if os.path.exists(CSV_TEMP):
    os.remove(CSV_TEMP)