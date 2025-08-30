"""
Flask Search API + UI (BM25F + MultifieldParser)
------------------------------------------------
- Serves a scholar-style search page backed by a Whoosh inverted index.
- Uses BM25F with field-specific boosts (title > authors > type > title_ngram).
- MultifieldParser + OrGroup.factory(0.9) ⇒ flexible matching across fields.

Prerequisite: build the index first (e.g., `python indexer.py`).
"""

import os
import yaml
from flask import Flask, request, jsonify, render_template
from whoosh import index
from whoosh.qparser import MultifieldParser, OrGroup
from whoosh.scoring import BM25F

# --------------------------------------------------------------------
# Configuration & index path
# --------------------------------------------------------------------
BASE = os.path.dirname(__file__)
CONFIG = yaml.safe_load(open(os.path.join(BASE, "config.yaml"), "r", encoding="utf-8"))

INDEX_DIR = os.path.join(BASE, CONFIG["paths"]["index_dir"])

app = Flask(__name__, template_folder="templates", static_folder="static")


def index_ready() -> bool:
    """Return True if a Whoosh index exists in INDEX_DIR."""
    return index.exists_in(INDEX_DIR)


def open_ix():
    """Open the Whoosh index from disk."""
    if not index_ready():
        raise RuntimeError("Index not found. Run indexer.py first to build the index.")
    return index.open_dir(INDEX_DIR)


# --------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------

@app.get("/")
def home():
    """Render the search UI (simple index.html)."""
    return render_template("index.html")


@app.get("/api/stats")
def stats():
    """Small health endpoint for the UI."""
    if not index_ready():
        return jsonify({"ready": False, "docs": 0})
    ix = open_ix()
    with ix.searcher() as s:
        return jsonify({"ready": True, "docs": s.doc_count_all()})


@app.get("/api/search")
def api_search():
    """
    Search endpoint.
    Query params:
      - q:    the user query (string)
      - sort: 'relevance' (default), 'year' (desc), or 'recent' (crawled_at desc)

    Response JSON:
      { "query": "...", "results": [ {...}, ... ] }
    """
    q = (request.args.get("q") or "").strip()
    sort = (request.args.get("sort") or "relevance").lower()

    if not q:
        return jsonify({"query": q, "results": []})

    ix = open_ix()

    # BM25F weighting (boost title > authors > type > title_ngram)
    weighting = BM25F(
        title_B=1.3,
        authors_B=1.0,
        publication_type_B=0.8,
        title_ngram_B=0.6  # matches the ngram field in indexer.py
    )

    # Search across title, title_ngram (for substring), authors, and publication_type
    fields = ["title", "title_ngram", "authors", "publication_type"]
    parser = MultifieldParser(fields, schema=ix.schema, group=OrGroup.factory(0.9))
    query = parser.parse(q)

    with ix.searcher(weighting=weighting) as s:
        # Default: relevance
        hits = s.search(query, limit=100)

        # Optional sorts
        if sort == "year":
            hits = s.search(query, limit=100, sortedby="year", reverse=True)
        elif sort == "recent":
            hits = s.search(query, limit=100, sortedby="crawled_at", reverse=True)

        rows = []
        for h in hits:
            # authors: KEYWORD stored as comma-separated
            authors_list = []
            raw_authors = h.get("authors", "")
            if isinstance(raw_authors, str) and raw_authors.strip():
                authors_list = [a.strip() for a in raw_authors.split(",") if a.strip()]

            # author_links stored as semicolon-separated string
            links_list = []
            raw_links = h.get("author_links", "")
            if isinstance(raw_links, str) and raw_links.strip():
                links_list = [u.strip() for u in raw_links.split(";") if u.strip()]

            rows.append({
                "title": h.get("title", ""),
                "year": h.get("year"),
                "url": h.get("url"),
                "authors": authors_list,
                "author_links": links_list,
                "publication_type": h.get("publication_type", ""),
                "crawled_at": h.get("crawled_at"),
                "score": float(getattr(h, "score", 0.0)),
            })

    return jsonify({"query": q, "results": rows})


# --------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
