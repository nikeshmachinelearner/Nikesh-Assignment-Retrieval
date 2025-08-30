"""
Coventry PurePortal Publications Crawler
----------------------------------------
- Uses Selenium to render dynamic PurePortal pages.
- Crawls department persons, then scrapes each person's research outputs.
- Saves results to:
    - data/publications.jsonl  (JSON Lines; 1 record per line)  <-- for indexer.py
    - data/publications.csv    (flat view for quick inspection)
"""

import os
import re
import time
import json
import hashlib
import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
BASE_URL = "https://pureportal.coventry.ac.uk"
DEPT_PERSONS_URL = BASE_URL + "/en/organisations/fbl-school-of-economics-finance-and-accounting/persons/"
DATA_DIR = "data"
JSONL_FILE = os.path.join(DATA_DIR, "publications.jsonl")  # JSONL for indexer
CSV_FILE = os.path.join(DATA_DIR, "publications.csv")      # Optional: flat view

os.makedirs(DATA_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CoventryCrawler")

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def stable_id(title: str, url: str) -> str:
    """Deterministic ID for deduplication."""
    return hashlib.md5((title + url).encode("utf-8")).hexdigest()

def write_jsonl(path: str, records: List[Dict]) -> None:
    """Write a list of dicts to JSONL (overwrites the file)."""
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

# -------------------------------------------------------------------
# Crawler Class
# -------------------------------------------------------------------
class CoventryCrawler:
    def __init__(self, headless: bool = True):
        self.driver = self._setup_driver(headless)
        self.publications: List[Dict] = []

    def _setup_driver(self, headless: bool):
        options = Options()
        if headless:
            options.add_argument("--headless=new")  # new headless for Chrome 109+
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def _accept_cookies(self):
        """Best-effort accept of cookie banner (if present)."""
        try:
            btn = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]"))
            )
            btn.click()
            logger.info("✓ Accepted cookies")
        except Exception:
            pass

    def get_all_persons(self) -> List[Dict]:
        """Collect all persons in the department (across paginated list)."""
        persons: List[Dict] = []
        self.driver.get(DEPT_PERSONS_URL)
        time.sleep(2)
        self._accept_cookies()

        while True:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            cards = soup.select("div.result-container h3.title a")
            for a in cards:
                persons.append({
                    "name": a.text.strip(),
                    "url": urljoin(BASE_URL, a.get("href", ""))
                })
            # pagination
            try:
                next_btn = self.driver.find_element(By.CSS_SELECTOR, "a.nextLink")
                if "disabled" in (next_btn.get_attribute("class") or ""):
                    break
                self.driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(2)
            except Exception:
                break

        logger.info(f"Found {len(persons)} persons")
        return persons

    def scrape_person_publications(self, person: Dict) -> List[Dict]:
        """Scrape all publications visible on a person's page."""
        pubs: List[Dict] = []
        self.driver.get(person["url"])
        time.sleep(2)

        # Expand "View all research outputs" if present
        try:
            btn = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'research output')]"))
            )
            self.driver.execute_script("arguments[0].click();", btn)
            time.sleep(2)
        except Exception:
            pass

        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        containers = soup.find_all("div", class_="result-container")
        for c in containers:
            pub = self._parse_pub_container(c, person)
            if pub:
                pubs.append(pub)
        return pubs

    def _parse_pub_container(self, container, person: Dict) -> Dict | None:
        """Extract a publication from a listing container."""
        title_elem = container.find("h3", class_="title")
        if not title_elem:
            return None

        link = title_elem.find("a")
        title = link.text.strip() if link else title_elem.text.strip()
        url = urljoin(BASE_URL, link.get("href", "")) if link else ""

        pub: Dict = {
            "id": stable_id(title, url),
            "title": title,
            "url": url,
            "year": None,
            "publication_type": None,
            "authors": [],
            "crawled_at": datetime.now().isoformat()
        }

        # Year (from visible date span)
        date_elem = container.find("span", class_="date")
        if date_elem:
            m = re.search(r"\b\d{4}\b", date_elem.get_text(" ", strip=True))
            if m:
                pub["year"] = m.group(0)

        # Type
        type_elem = container.find("span", class_="type")
        if type_elem:
            pub["publication_type"] = type_elem.get_text(" ", strip=True)

        # Authors (include the person we’re scraping + any co-authors)
        authors = [{
            "name": person["name"],
            "profile_url": person["url"]
        }]
        for a in container.find_all("a", class_="person"):
            name = a.get_text(" ", strip=True)
            href = urljoin(BASE_URL, a.get("href", ""))
            if name and name != person["name"]:
                authors.append({"name": name, "profile_url": href})
        pub["authors"] = authors

        return pub

    def crawl(self, limit: int | None = None):
        persons = self.get_all_persons()
        if limit:
            persons = persons[:limit]

        for i, person in enumerate(persons, 1):
            logger.info(f"[{i}/{len(persons)}] {person['name']}")
            pubs = self.scrape_person_publications(person)

            # Deduplicate by stable id
            for p in pubs:
                if not any(x["id"] == p["id"] for x in self.publications):
                    self.publications.append(p)

            time.sleep(1.5)  # politeness
            if i % 10 == 0:
                self.save()

        self.save()
        logger.info(f"✓ Done. {len(self.publications)} unique publications.")

    def save(self):
        """Persist as JSONL (for indexer) + CSV (for quick viewing)."""
        # JSONL
        write_jsonl(JSONL_FILE, self.publications)
        logger.info(f"[SAVE] Wrote {len(self.publications)} records to {JSONL_FILE}")

        # CSV (flat)
        df = pd.DataFrame([{
            "title": p["title"],
            "year": p.get("year"),
            "type": p.get("publication_type"),
            "authors": ", ".join(a["name"] for a in p.get("authors", [])),
            "author_links": "; ".join(a["profile_url"] for a in p.get("authors", [])),
            "url": p["url"]
        } for p in self.publications])
        df.to_csv(CSV_FILE, index=False)
        logger.info(f"[SAVE] CSV written to {CSV_FILE}")

# -------------------------------------------------------------------
if __name__ == "__main__":
    crawler = CoventryCrawler(headless=True)
    crawler.crawl(limit=5)  # remove limit for full crawl
