"""BBC RSS feeds → article metadata."""
from __future__ import annotations
import feedparser
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

FEEDS = {
    "World":      "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Business":   "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "Science":    "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    "Health":     "https://feeds.bbci.co.uk/news/health/rss.xml",
}

@dataclass
class Article:
    category: str
    title: str
    summary: str
    link: str
    published: str

def fetch_all(per_category: int = 12) -> list[Article]:
    out: list[Article] = []
    for cat, url in FEEDS.items():
        d = feedparser.parse(url)
        for e in d.entries[:per_category]:
            out.append(Article(
                category=cat,
                title=getattr(e, "title", "").strip(),
                summary=getattr(e, "summary", "").strip(),
                link=getattr(e, "link", ""),
                published=getattr(e, "published", ""),
            ))
    return out

if __name__ == "__main__":
    import json
    arts = fetch_all()
    print(f"fetched {len(arts)} articles")
    print(json.dumps([asdict(a) for a in arts[:2]], ensure_ascii=False, indent=2))
