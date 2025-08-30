import os, json, yaml, shutil
from whoosh import index
from whoosh.fields import Schema, TEXT, KEYWORD, ID, NUMERIC, STORED, DATETIME
from whoosh.analysis import StemmingAnalyzer, NgramWordAnalyzer
from whoosh.writing import AsyncWriter
from datetime import datetime

# -------------------------------------------------------------------
# Config & paths
# -------------------------------------------------------------------
BASE = os.path.dirname(__file__)
CONFIG = yaml.safe_load(open(os.path.join(BASE, "config.yaml"), "r", encoding="utf-8"))
DATA_PATH = os.path.join(BASE, CONFIG["paths"]["data_jsonl"])
INDEX_DIR = os.path.join(BASE, CONFIG["paths"]["index_dir"])
os.makedirs(INDEX_DIR, exist_ok=True)

# -------------------------------------------------------------------
# Schema definition (aligned with crawler fields)
# -------------------------------------------------------------------
schema = Schema(
    doc_id=ID(stored=True, unique=True),
    title=TEXT(stored=True, analyzer=StemmingAnalyzer()),          # normal stemming
    title_ngram=TEXT(stored=False, analyzer=NgramWordAnalyzer(3,6)), # partial/substring search
    authors=KEYWORD(stored=True, commas=True, lowercase=True, scorable=True),
    year=NUMERIC(stored=True),
    url=STORED,
    author_links=STORED,
    publication_type=TEXT(stored=True, analyzer=StemmingAnalyzer()),
    crawled_at=DATETIME(stored=True)
)

# -------------------------------------------------------------------
# Demo record (only if no crawl data yet)
# -------------------------------------------------------------------
def seed_demo_if_missing():
    if os.path.exists(DATA_PATH):
        return
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    demo = {
        "id": "demo-efa-1",
        "title": "Fiscal Policy and Market Volatility",
        "year": 2023,
        "url": "https://pureportal.coventry.ac.uk/en/publications/",
        "authors": [
            {"name": "EFA Member", "profile_url": "https://pureportal.coventry.ac.uk/en/persons/"}
        ],
        "publication_type": "Journal Article",
        "crawled_at": datetime.now().isoformat()
    }
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        f.write(json.dumps(demo, ensure_ascii=False) + "\n")

# -------------------------------------------------------------------
# Safe open/create index (drops if schema mismatch)
# -------------------------------------------------------------------
def safe_open_or_create(index_dir, schema):
    if not index.exists_in(index_dir):
        return index.create_in(index_dir, schema)
    try:
        ix = index.open_dir(index_dir)
        # Check schema mismatch (e.g., title_ngram missing)
        for field in schema.names():
            if field not in ix.schema.names():
                print("[Indexer] Schema mismatch detected — rebuilding index...")
                shutil.rmtree(index_dir)
                os.makedirs(index_dir, exist_ok=True)
                return index.create_in(index_dir, schema)
        return ix
    except Exception:
        shutil.rmtree(index_dir)
        os.makedirs(index_dir, exist_ok=True)
        return index.create_in(index_dir, schema)

# -------------------------------------------------------------------
# Indexing
# -------------------------------------------------------------------
def main():
    seed_demo_if_missing()

    ix = safe_open_or_create(INDEX_DIR, schema)
    writer = AsyncWriter(ix)

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Extract authors
            authors = [a.get("name", "") for a in obj.get("authors", []) if a.get("name")]
            links = [a.get("profile_url", "") for a in obj.get("authors", []) if a.get("profile_url")]

            # Parse crawled_at
            crawled_dt = None
            if obj.get("crawled_at"):
                try:
                    crawled_dt = datetime.fromisoformat(obj["crawled_at"])
                except Exception:
                    pass

            writer.update_document(
                doc_id=obj.get("id", ""),
                title=obj.get("title", ""),
                title_ngram=obj.get("title", ""),   # NEW field for substring matching
                authors=",".join(authors),
                year=obj.get("year"),
                url=obj.get("url", ""),
                author_links="; ".join(links),
                publication_type=obj.get("publication_type", ""),
                crawled_at=crawled_dt
            )

    writer.commit()
    print(f"[Indexer] Index updated at {INDEX_DIR}")

# -------------------------------------------------------------------
if __name__ == "__main__":
    main()
