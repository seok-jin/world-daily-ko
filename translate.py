"""기사 1건 본문 → 한국어 번역 (on-demand, 디스크 캐시)."""
from __future__ import annotations
import hashlib
from pathlib import Path
from scrape import scrape_one
from summarize import _call_ai, TIMEOUT_FULL

CACHE_DIR = Path(__file__).parent / "reports" / "translations"

PROMPT = """다음 BBC 영어 기사를 한국어로 자연스럽게 번역하라.

제목: {title}

본문:
{body}

요구사항:
- 한국어 신문/매거진 톤. 직역체 X.
- 본문 모든 문단을 충실히 번역, 문단 구분은 빈 줄로.
- 설명·머릿말·코드펜스 없이 번역된 본문만 출력.
- 첫 줄은 한국어 제목 (## 헤더로 시작).
"""

def link_hash(url: str) -> str:
    """URL → 12자 md5 prefix (Streamlit 딥링크 + 번역 캐시 키 공용)."""
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:12]

def _cache_path(url: str) -> Path:
    return CACHE_DIR / f"{link_hash(url)}.md"

def translate_article(url: str, title: str, force: bool = False) -> tuple[str, bool]:
    """본문 번역 결과 + 캐시 히트 여부."""
    cp = _cache_path(url)
    if cp.exists() and not force:
        return cp.read_text(encoding="utf-8"), True

    body = scrape_one(url)
    if body.startswith("(본문"):
        return f"⚠️ {body}", False

    prompt = PROMPT.format(title=title, body=body[:8000])
    out = _call_ai(prompt, timeout=TIMEOUT_FULL).strip()
    # 코드펜스 제거 (간혹 들어옴)
    if out.startswith("```"):
        lines = out.splitlines()
        out = "\n".join(lines[1:-1]) if lines[-1].strip().startswith("```") else "\n".join(lines[1:])

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cp.write_text(out, encoding="utf-8")
    return out, False
