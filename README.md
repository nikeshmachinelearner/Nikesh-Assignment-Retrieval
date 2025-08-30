Coventry University Vertical Search (IR Coursework)
📌 Overview

This project implements a vertical search engine for Coventry University’s PurePortal research outputs.
It covers the full pipeline of data collection, indexing, and retrieval:

Crawler (crawler.py)

Uses Selenium + BeautifulSoup to scrape researcher profile pages and extract publications (title, year, authors, links, type).

Saves data in JSONL (for indexing) and CSV (for inspection).

Each record has a stable ID (md5(title+url)) and crawl timestamp.

Indexer (indexer.py)

Reads the JSONL dataset and builds a Whoosh inverted index.

Schema fields include: title, authors, year, url, author_links, publication_type, crawled_at.

Supports incremental indexing (update_document).

Stores index files in models/index/.

Flask Search API + UI (app.py)

Provides a scholar-style search page.

REST API endpoints:

/api/search?q=term&sort=relevance|year|recent

/api/stats (index health + doc count)

Uses BM25F ranking with field boosts (title > authors > publication_type).

Search supports flexible matching across multiple fields.

Scheduler (optional) (scheduler.py)

Uses APScheduler to run crawler + indexer weekly (cron job).

Ensures the index stays up-to-date with new publications.

⚙️ Requirements

Python 3.9+

Virtual environment recommended

Install dependencies:

pip install -r requirements.txt


Main packages used:

selenium, webdriver-manager, beautifulsoup4

whoosh, pyyaml, flask, pandas

🚀 Usage
1. Crawl Data
python crawler.py


This generates:

data/publications.jsonl – append-only dataset

data/publications.csv – human-readable version

2. Build Index
python indexer.py


This creates/updates the Whoosh index in models/index/.

3. Run Search UI
python app.py


Open http://localhost:5000
 in your browser.
You can search by title, author, or type, sort by relevance/year/recent.

4. Automate Weekly (optional)
python scheduler.py


Runs crawler + indexer every Sunday 03:30 UTC.

📂 Project Structure
task/
│
├── crawler.py        # Scrapes PurePortal persons + publications
├── indexer.py        # Builds Whoosh index from JSONL data
├── app.py            # Flask API + search interface
├── scheduler.py      # APScheduler job for weekly updates
│
├── data/             # Raw + processed crawl data (jsonl, csv)
├── models/index/     # Whoosh index files
├── templates/        # index.html for UI
├── static/           # CSS + JS assets
│
├── config.yaml       # Paths + crawler settings
├── requirements.txt  # Dependencies
└── README.md         # Documentation

🔍 Example Query

Search: compensation
Results: Titles like "New perspectives on the governance of executive compensation" will appear, ranked by BM25F.

📝 Notes

Crawler is polite (accepts cookies, waits between requests, handles pagination).

JSONL is append-only, preserving crawl history.

Indexer is idempotent — re-running updates changed records instead of duplicating.

Flask app is debug-ready, but production deployment should use a WSGI server (e.g., Gunicorn).

👨‍🎓 Author

Name: Nikesh Adhikari

Course: Information Retrieval (MSc, Coventry University)

Task: Coursework – Vertical Search System
