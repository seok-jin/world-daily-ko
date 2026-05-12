"""요약된 기사 리스트 → 일일 Markdown 리포트."""
from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from fetch import CATEGORIES

def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def render(items: list[dict], out_dir: Path) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{today}.md"

    grouped: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        grouped[it["category"]].append(it)

    lines: list[str] = []
    sources = sorted({it.get("source", "BBC") for it in items})
    lines.append(f"# 월드 데일리 리포트 — {today}")
    lines.append("")
    lines.append(f"_총 {len(items)}건 · 출처: {' · '.join(sources)}_")
    lines.append("")

    # 그룹별 목차
    topic_cats = [c for c in CATEGORIES if CATEGORIES[c]["group"] == "topic" and c in grouped]
    region_cats = [c for c in CATEGORIES if CATEGORIES[c]["group"] == "region" and c in grouped]
    if topic_cats:
        lines.append("### 📚 토픽")
        for c in topic_cats:
            lines.append(f"- [{CATEGORIES[c]['label']}](#{_slug(c)})  ({len(grouped[c])}건)")
    if region_cats:
        lines.append("")
        lines.append("### 🌐 지역")
        for c in region_cats:
            lines.append(f"- [{CATEGORIES[c]['label']}](#{_slug(c)})  ({len(grouped[c])}건)")
    lines.append("")

    for cat in topic_cats + region_cats:
        label = CATEGORIES[cat]["label"]
        lines.append(f"## {label} <a id='{_slug(cat)}'></a>")
        lines.append("")
        for idx, it in enumerate(grouped[cat], 1):
            lines.append(f"### {idx}. {it['ko_title']}")
            lines.append("")
            for s in it["ko_summary"].split("\n"):
                s = s.strip().lstrip("-•·").strip()
                if s:
                    lines.append(f"- {s}")
            lines.append("")
            lines.append(f"_원문 제목: {it['title']}_  ")
            lines.append(f"🔗 [원문 보기]({it['link']})")
            lines.append("")
        lines.append("---")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
