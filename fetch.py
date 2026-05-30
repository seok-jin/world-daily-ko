"""RSS feeds → article metadata. BBC_PROFILE 환경변수로 프로필 전환.

기본: 월드 (BBC + Guardian + Al Jazeera + ...)
BBC_PROFILE=health: 정형외과 + 헬스 정책 (feeds_health.py)
"""
from __future__ import annotations
import os
import feedparser
from dataclasses import dataclass

_PROFILE = os.environ.get("BBC_PROFILE", "world").lower()

# ── 월드 프로필 (기본값) ──
_WORLD_CATEGORIES: dict[str, dict] = {
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

_WORLD_FEEDS: list[tuple[str, str, str]] = [
    # 토픽 — BBC
    ("Top Stories",   "BBC",          "https://feeds.bbci.co.uk/news/rss.xml"),
    ("World",         "BBC",          "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Business",      "BBC",          "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("Technology",    "BBC",          "https://feeds.bbci.co.uk/news/technology/rss.xml"),
    ("Science",       "BBC",          "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
    ("Health",        "BBC",          "https://feeds.bbci.co.uk/news/health/rss.xml"),
    ("Politics",      "BBC",          "https://feeds.bbci.co.uk/news/politics/rss.xml"),
    ("Entertainment", "BBC",          "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"),
    # 토픽 — World 강화
    ("World",         "Guardian",     "https://www.theguardian.com/world/rss"),
    ("World",         "Al Jazeera",   "https://www.aljazeera.com/xml/rss/all.xml"),
    ("World",         "NPR",          "https://feeds.npr.org/1004/rss.xml"),
    # 토픽 — Tech 강화
    ("Technology",    "TechCrunch",   "https://techcrunch.com/feed/"),
    ("Technology",    "The Verge",    "https://www.theverge.com/rss/index.xml"),
    ("Technology",    "Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    # 토픽 — Business 강화
    ("Business",      "Nikkei Asia",  "https://asia.nikkei.com/rss/feed/nar"),
    # 지역
    ("US & Canada",   "BBC",          "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"),
    ("UK",            "BBC",          "https://feeds.bbci.co.uk/news/uk/rss.xml"),
    ("Europe",        "BBC",          "https://feeds.bbci.co.uk/news/world/europe/rss.xml"),
    ("Asia",          "BBC",          "https://feeds.bbci.co.uk/news/world/asia/rss.xml"),
    ("Asia",          "SCMP",         "https://www.scmp.com/rss/91/feed"),
    ("Asia",          "CNA",          "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6511"),
    ("Australia",     "BBC",          "https://feeds.bbci.co.uk/news/world/australia/rss.xml"),
    ("Africa",        "BBC",          "https://feeds.bbci.co.uk/news/world/africa/rss.xml"),
    ("Latin America", "BBC",          "https://feeds.bbci.co.uk/news/world/latin_america/rss.xml"),
    ("Middle East",   "BBC",          "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml"),
]

# ── 프로필별 활성 CATEGORIES / FEEDS 선택 ──
if _PROFILE == "health":
    from feeds_health import CATEGORIES as _C, FEEDS as _F
    CATEGORIES: dict[str, dict] = _C
    FEEDS: list[tuple[str, str, str]] = _F
else:
    CATEGORIES = _WORLD_CATEGORIES
    FEEDS = _WORLD_FEEDS

@dataclass
class Article:
    category: str
    title: str
    summary: str
    link: str
    published: str
    source: str = "BBC"  # 레거시 호환 기본값

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
    print(f"PROFILE: {_PROFILE} · feeds: {len(FEEDS)} · categories: {len(CATEGORIES)}")
    arts = fetch_all(per_category=2)
    print(f"fetched {len(arts)} articles")
    from collections import Counter
    for (cat, src), n in sorted(Counter((a.category, a.source) for a in arts).items()):
        print(f"  {cat:18s} {src:22s} {n}")
