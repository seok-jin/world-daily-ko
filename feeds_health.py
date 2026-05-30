"""헬스 프로필 (BBC_PROFILE=health) — 정형외과 + 일반 헬스 정책/임상.

fetch.py가 BBC_PROFILE 환경변수에 따라 이 파일을 import.
"""
from __future__ import annotations

# ── 카테고리 메타 ──
CATEGORIES: dict[str, dict] = {
    # 토픽
    "Orthopedics":   {"group": "topic", "label": "🦴 정형외과"},
    "Health Policy": {"group": "topic", "label": "🏥 헬스 정책/임상"},
    "AI Medical":    {"group": "topic", "label": "🤖 AI 의료기기"},
}

# ── 실제 RSS 피드 ──
# (category, source, url)
FEEDS: list[tuple[str, str, str]] = [
    # 정형외과 (3)
    ("Orthopedics",   "OrthoSpineNews",       "https://orthospinenews.com/feed/"),
    ("Orthopedics",   "OrthoBuzz (JBJS)",     "https://orthobuzz.jbjs.org/feed/"),
    ("Orthopedics",   "Orthopedics This Week","https://ryortho.com/feed/"),
    # 정책 + 임상 (3)
    ("Health Policy", "KFF Health News",      "https://kffhealthnews.org/feed/"),
    ("Health Policy", "MedPage Today",        "https://www.medpagetoday.com/rss/headlines.xml"),
    ("Health Policy", "Guardian Health",      "https://www.theguardian.com/society/health/rss"),
    # AI 의료기기 / 디지털헬스 (3)
    ("AI Medical",    "STAT Health Tech",     "https://www.statnews.com/category/health-tech/feed/"),
    ("AI Medical",    "MobiHealthNews",       "https://www.mobihealthnews.com/rss.xml"),
    ("AI Medical",    "Healthcare IT News",   "https://www.healthcareitnews.com/feed"),
]
