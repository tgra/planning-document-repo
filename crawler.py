import requests
from bs4 import BeautifulSoup
import re
import time
import pandas as pd
import yaml

BASE = "https://pa.swindon.gov.uk"

# Load config
with open("config.yaml") as f:
    config = yaml.safe_load(f)

START_URLS = config["start_urls"]
DELAY = config["crawler"]["delay_seconds"]

HEADERS = {
    "User-Agent": config["crawler"]["user_agent"]
}

session = requests.Session()
session.headers.update(HEADERS)

visited = set()
applications = []


def extract_applications(url):

    r = session.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    container = soup.find("div", id="Application")

    if not container:
        return []

    apps = []

    for li in container.find_all("li"):

        a = li.find("a")
        description = a.get_text(strip=True)

        link = BASE + a["href"]

        meta = li.find("span", class_="metaInfo").get_text(" ", strip=True)

        ref_match = re.search(r"Ref\. No:\s*(.*?)\s*\|", meta)
        status_match = re.search(r"Status:\s*(.*)", meta)

        ref = ref_match.group(1) if ref_match else None
        status = status_match.group(1) if status_match else None

        apps.append({
            "ref": ref,
            "status": status,
            "description": description,
            "link": link
        })

    return apps


def parse_application_page(url):

    r = session.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    data = {"url": url}

    table = soup.find("table", id="simpleDetailsTable")

    if table:
        for row in table.find_all("tr"):

            th = row.find("th")
            td = row.find("td")

            if th and td:

                key = th.get_text(strip=True)
                val = td.get_text(strip=True)

                data[key] = val

    return data


# Stage 1 — collect applications
for start in START_URLS:

    print("Scanning start page:", start)

    apps = extract_applications(start)

    for app in apps:

        if app["link"] not in visited:

            visited.add(app["link"])
            applications.append(app)


print("Applications discovered:", len(applications))


# Stage 2 — fetch application details
results = []

for app in applications:

    print("Processing:", app["ref"])

    details = parse_application_page(app["link"])

    record = {**app, **details}

    results.append(record)

    time.sleep(DELAY)


# Stage 3 — save dataset
df = pd.DataFrame(results)

df.to_csv(config["output"]["csv"], index=False)

print("Saved", len(df), "records")