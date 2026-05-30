"""BBC + 외부 매체 RSS feeds → article metadata.

CATEGORIES: 카테고리 메타 (group, label) — 화면 표시용
FEEDS: 실제 RSS URL 리스트 — 한 카테고리에 여러 source 가능 (예: World = BBC + Guardian + Al Jazeera)
"""
from __future__ import annotations
import feedparser
from dataclasses import dataclass

# ── 카테고리 메타 (8 topics + 8 regions) ──
CATEGORIES: dict[str, dict] = {
    # 토픽
    "Top Stories":   {"group": "topic",  "label": "📰 톱스토리"},
    "World":         {"group": "topic",  "label": "🌍 세계"},
    "Business":      {"group": "topic",  "label": "💼 비즈니스"},
    "Technology":    {"group": "topic",  "label": "💻 테크"},
    "Science":       {"group": "topic",  "label": "🔬 과학·환경"},
    "Health":        {"group": "topic",  "label": "🏥 헬스"},
    "Politics":      {"group": "topic",  "label": "🗳️ 정치"},
    "Entertainment": {"group": "topic",  "label": "🎭 엔터·문화"},
    # 지역
    "US & Canada":   {"group": "region", "label": "🇺🇸 미주"},
    "UK":            {"group": "region", "label": "🇬🇧 영국"},
    "Europe":        {"group": "region", "label": "🇪🇺 유럽"},
    "Asia":          {"group": "region", "label": "🌏 아시아"},
    "Australia":     {"group": "region", "label": "🇦🇺 호주"},
    "Africa":        {"group": "region", "label": "🌍 아프리카"},
    "Latin America": {"group": "region", "label": "🌎 라틴아메리카"},
    "Middle East":   {"group": "region", "label": "🕌 중동"},
}

# ── 실제 RSS 피드 (한 카테고리에 다중 출처 OK) ──
# (category, source, url)
FEEDS: list[tuple[str, str, str]] = [
    # 토픽 — BBC
    ("Top Stories",   "BBC",        "https://feeds.bbci.co.uk/news/rss.xml"),
    ("World",         "BBC",        "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Business",      "BBC",        "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("Technology",    "BBC",        "https://feeds.bbci.co.uk/news/technology/rss.xml"),
    ("Science",       "BBC",        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
    ("Health",        "BBC",        "https://feeds.bbci.co.uk/news/health/rss.xml"),
    ("Politics",      "BBC",        "https://feeds.bbci.co.uk/news/politics/rss.xml"),
    ("Entertainment", "BBC",        "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"),
    # 토픽 — World 강화
    ("World",         "Guardian",   "https://www.theguardian.com/world/rss"),
    ("World",         "Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("World",         "NPR",        "https://feeds.npr.org/1004/rss.xml"),
    # 토픽 — Tech 강화
    ("Technology",    "TechCrunch", "https://techcrunch.com/feed/"),
    ("Technology",    "The Verge",  "https://www.theverge.com/rss/index.xml"),
    ("Technology",    "Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    # 토픽 — Business 강화 (아시아 비즈니스)
    ("Business",      "Nikkei Asia", "https://asia.nikkei.com/rss/feed/nar"),
    # 지역 — BBC
    ("US & Canada",   "BBC",        "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"),
    ("UK",            "BBC",        "https://feeds.bbci.co.uk/news/uk/rss.xml"),
    ("Europe",        "BBC",        "https://feeds.bbci.co.uk/news/world/europe/rss.xml"),
    ("Asia",          "BBC",        "https://feeds.bbci.co.uk/news/world/asia/rss.xml"),
    ("Asia",          "SCMP",       "https://www.scmp.com/rss/91/feed"),
    ("Asia",          "CNA",        "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6511"),
    ("Australia",     "BBC",        "https://feeds.bbci.co.uk/news/world/australia/rss.xml"),
    ("Africa",        "BBC",        "https://feeds.bbci.co.uk/news/world/africa/rss.xml"),
    ("Latin America", "BBC",        "https://feeds.bbci.co.uk/news/world/latin_america/rss.xml"),
    ("Middle East",   "BBC",        "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml"),
]

@dataclass
class Article:
    category: str
    title: str
    summary: str
    link: str
    published: str
    source: str = "BBC"  # default for legacy compat

def fetch_all(per_category: int = 6) -> list[Article]:
    out: list[Article] = []
    for category, source, url in FEEDS:
        try:
            d = feedparser.parse(url)
        except Exception as e:
            print(f"  · RSS 실패 {source}/{category}: {e}", flush=True)
            continue
        for e in d.entries[:per_category]:
            out.append(Article(
                category=category,
                source=source,
                title=getattr(e, "title", "").strip(),
                summary=getattr(e, "summary", "").strip(),
                link=getattr(e, "link", ""),
                published=getattr(e, "published", ""),
            ))
    return out

if __name__ == "__main__":
    arts = fetch_all(per_category=2)
    print(f"fetched {len(arts)} articles from {len(FEEDS)} feeds")
    from collections import Counter
    src_count = Counter((a.category, a.source) for a in arts)
    for (cat, src), n in sorted(src_count.items()):
        print(f"  {cat:18s} {src:14s} {n}")
