"""요약된 기사 리스트 → 일일 Markdown 리포트."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from collections import defaultdict

CAT_KO = {
    "World": "🌍 세계",
    "Business": "💼 비즈니스",
    "Technology": "💻 테크",
    "Science": "🔬 과학·환경",
    "Health": "🏥 헬스",
}

def render(items: list[dict], out_dir: Path) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{today}.md"

    grouped: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        grouped[it["category"]].append(it)

    lines: list[str] = []
    lines.append(f"# BBC 데일리 리포트 — {today}")
    lines.append("")
    lines.append(f"_총 {len(items)}건 · 출처: BBC News_")
    lines.append("")
    lines.append("## 목차")
    for cat in CAT_KO:
        if cat in grouped:
            lines.append(f"- [{CAT_KO[cat]}](#{cat.lower()})  ({len(grouped[cat])}건)")
    lines.append("")

    for cat, label in CAT_KO.items():
        if cat not in grouped:
            continue
        lines.append(f"## {label} <a id='{cat.lower()}'></a>")
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
