"""BBC Daily KO — Streamlit 뷰어.

reports/YYYY-MM-DD.md 파일을 자동 스캔해서 날짜·카테고리별로 보여준다.

실행:
    streamlit run app.py --server.port 8504 --server.address 0.0.0.0
URL 파라미터:
    /?date=2026-05-10           → 특정 날짜로 직접 진입
"""
from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
import streamlit as st

REPORTS_DIR = Path(__file__).parent / "reports"

st.set_page_config(
    page_title="BBC Daily KO",
    page_icon="📰",
    layout="wide",
)

# ── 데이터 로드 ────────────────────────────────────────────
def list_dates() -> list[str]:
    if not REPORTS_DIR.exists():
        return []
    files = sorted(REPORTS_DIR.glob("*.md"), reverse=True)
    return [f.stem for f in files if re.fullmatch(r"\d{4}-\d{2}-\d{2}", f.stem)]

@st.cache_data(ttl=60)
def load_report(date: str) -> str | None:
    p = REPORTS_DIR / f"{date}.md"
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8")

def split_sections(md: str) -> dict[str, str]:
    """## 헤더 단위로 섹션 분리 (목차/카테고리)."""
    parts = re.split(r"(?m)^## ", md)
    sections: dict[str, str] = {}
    for p in parts[1:]:
        line, _, body = p.partition("\n")
        title = re.sub(r"<a id=.*?</a>", "", line).strip()
        sections[title] = "## " + p
    return sections

# ── 사이드바 ───────────────────────────────────────────────
dates = list_dates()
qp = st.query_params
default_date = qp.get("date", dates[0] if dates else None)

with st.sidebar:
    st.title("📰 BBC Daily KO")
    st.caption("BBC 뉴스 한국어 리포트")
    if not dates:
        st.warning("아직 리포트 없음.\n`python main.py` 실행 후 새로고침.")
        st.stop()

    selected = st.selectbox(
        "날짜 선택",
        dates,
        index=dates.index(default_date) if default_date in dates else 0,
    )
    st.query_params["date"] = selected

    st.divider()
    st.markdown(f"**총 리포트**: {len(dates)}개")
    st.markdown(f"**최신**: `{dates[0]}`")
    st.markdown(f"**가장 오래**: `{dates[-1]}`")

    st.divider()
    st.markdown("**소스**: [BBC News](https://www.bbc.com/news)")
    st.markdown("**원문 링크는 각 기사 하단에 있어요.**")

# ── 메인 ───────────────────────────────────────────────────
md = load_report(selected)
if not md:
    st.error(f"`{selected}.md` 를 읽을 수 없습니다.")
    st.stop()

sections = split_sections(md)
title_section = next((v for k, v in sections.items() if "BBC 데일리" in k), None)

# 헤더 (첫 # 라인)
m = re.match(r"# (.+)", md)
if m:
    st.title(m.group(1))

# 메타 라인
meta = re.search(r"_총 (\d+)건", md)
if meta:
    st.caption(f"📊 총 {meta.group(1)}건  ·  출처: BBC News")

# 카테고리 탭
cat_sections = {k: v for k, v in sections.items()
                if any(emoji in k for emoji in ["🌍", "💼", "💻", "🔬", "🏥"])}

if cat_sections:
    tabs = st.tabs(list(cat_sections.keys()))
    for tab, (name, body) in zip(tabs, cat_sections.items()):
        with tab:
            # 첫 줄(섹션 헤더) 제거하고 본문만 렌더
            _, _, content = body.partition("\n")
            st.markdown(content, unsafe_allow_html=True)
else:
    st.markdown(md, unsafe_allow_html=True)

# 하단
st.divider()
st.caption(
    f"리포트 생성: {selected}  ·  "
    f"갱신: 매일 KST 08:00 (cron on EC2)"
)
