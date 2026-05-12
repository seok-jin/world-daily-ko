"""BBC Daily KO — Streamlit 뷰어 (on-demand 본문 번역 + 수동 새로고침)."""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).parent
load_dotenv(PROJECT_DIR / ".env")

from translate import translate_article, link_hash
from fetch import CATEGORIES
import state

REPORTS_DIR = PROJECT_DIR / "reports"
KST = timezone(timedelta(hours=9))

st.set_page_config(page_title="BBC Daily KO", page_icon="📰", layout="wide")

CAT_LABEL = {name: meta["label"] for name, meta in CATEGORIES.items()}

# ── 데이터 로드 ────────────────────────────────────────────
def list_dates() -> list[str]:
    if not REPORTS_DIR.exists():
        return []
    files = sorted(REPORTS_DIR.glob("*.json"), reverse=True)
    return [f.stem for f in files if re.fullmatch(r"\d{4}-\d{2}-\d{2}", f.stem)]

@st.cache_data(ttl=30, show_spinner=False)
def load_report(date: str) -> dict:
    """{items, last_update, last_new_count} (구포맷 list도 호환)."""
    p = REPORTS_DIR / f"{date}.json"
    if not p.exists():
        return {"items": [], "last_update": None, "last_new_count": 0}
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data
    return {"items": data, "last_update": None, "last_new_count": 0}

@st.cache_data(ttl=30, show_spinner=False)
def load_all_recent_items(dates: tuple[str, ...]) -> list[dict]:
    """검색 / ⭐ 저장됨 탭용 — 모든 날짜의 items를 flat list로."""
    out = []
    for d in dates:
        r = load_report(d)
        for it in r["items"]:
            it_with_date = {**it, "_date": d}
            out.append(it_with_date)
    return out

# ── 사이드바 ───────────────────────────────────────────────
dates = list_dates()
qp = st.query_params
default_date = qp.get("date", dates[0] if dates else None)

with st.sidebar:
    st.title("📰 BBC Daily KO")
    st.caption("BBC 뉴스 한국어 다이제스트 · 30분 갱신")

    if not dates:
        st.warning("아직 리포트 없음.\n사이드바의 `🔄 지금 갱신` 클릭하거나\n`python main.py` 실행 후 새로고침.")

    if dates:
        selected = st.selectbox(
            "📅 날짜",
            dates,
            index=dates.index(default_date) if default_date in dates else 0,
        )
        st.query_params["date"] = selected
    else:
        selected = datetime.now(KST).strftime("%Y-%m-%d")

    st.divider()

    # ── 수동 새로고침 ─────────────────────────────────
    if st.button("🔄 지금 갱신", use_container_width=True, type="primary"):
        with st.spinner("BBC RSS 수집 + Gemini 요약 중... (~1분)\n신규 없으면 즉시 끝남."):
            try:
                proc = subprocess.run(
                    [sys.executable, str(PROJECT_DIR / "main.py"), "--no-push"],
                    cwd=str(PROJECT_DIR),
                    capture_output=True, text=True, timeout=300,
                )
                if proc.returncode == 0:
                    st.cache_data.clear()
                    last_line = (proc.stdout.strip().splitlines() or ["완료"])[-1]
                    st.success(last_line)
                    st.rerun()
                else:
                    st.error(f"갱신 실패 (rc={proc.returncode})\n{proc.stderr[-200:]}")
            except subprocess.TimeoutExpired:
                st.error("갱신 타임아웃 (5분 초과)")

    if dates:
        report = load_report(selected)
        items_for_count = report["items"]
        last_update = report.get("last_update")
        last_new = report.get("last_new_count", 0)

        st.markdown(f"**선택일 기사**: {len(items_for_count)}건")
        if last_update:
            try:
                dt = datetime.fromisoformat(last_update)
                st.markdown(f"**마지막 갱신**: `{dt.strftime('%H:%M:%S')}` KST")
            except Exception:
                pass
        if last_new is not None:
            st.markdown(f"**직전 회차 신규**: {last_new}건")
        st.markdown(f"**전체 리포트**: {len(dates)}일치")

    st.divider()
    # ── 검색 ──
    search_q = st.text_input("🔍 검색", placeholder="제목/요약 키워드", key="search_q").strip()

    # ── 읽은 글 숨김 ──
    hide_read = st.checkbox("✓ 읽은 글 숨기기", value=True, key="hide_read")

    # ── 키워드 알림 상태 ──
    wk = os.environ.get("WATCHED_KEYWORDS", "").strip()
    if wk:
        st.caption(f"🔔 키워드 알림: `{wk}`")
    else:
        st.caption("🔔 키워드 알림: `.env`에 `WATCHED_KEYWORDS=AI,반도체,...` 설정")

    st.divider()
    st.caption("ℹ️ 매 30분 자동 갱신 · KST 22~06시 일반 알림 끔 (키워드 매칭은 항상 알림)")
    st.caption("`📖 한글 본문 번역` → gemini가 BBC 원문을 번역 (캐시 공유)")
    st.caption("출처: [BBC News](https://www.bbc.com/news)")

# ── 메인 ───────────────────────────────────────────────────
if not dates:
    st.info("리포트가 아직 없습니다. 사이드바의 `🔄 지금 갱신` 버튼을 눌러주세요.")
    st.stop()

report = load_report(selected)
items = report["items"]
if not items:
    st.error(f"`{selected}.json` 데이터가 없습니다.")
    st.stop()

last_update = report.get("last_update")
ts_caption = ""
if last_update:
    try:
        dt = datetime.fromisoformat(last_update)
        ts_caption = f"  ·  마지막 갱신: {dt.strftime('%H:%M')} KST"
    except Exception:
        pass

st.title(f"BBC 데일리 리포트 — {selected}")
st.caption(f"📊 총 {len(items)}건{ts_caption}  ·  출처: BBC News")

# ── 텔레그램 딥링크로 진입한 기사 우선 표시 ──
focus_hash = qp.get("article", None)
focused = None
if focus_hash:
    for it in items:
        if link_hash(it["link"]) == focus_hash:
            focused = it
            break

# 카테고리별 그룹핑
by_cat: dict[str, list[dict]] = {}
for it in items:
    by_cat.setdefault(it["category"], []).append(it)

# 그룹 선택 (📚 토픽 / 🌐 지역 / ⭐ 저장됨)
group_choice = st.radio(
    "분류",
    ["📚 토픽", "🌐 지역", "⭐ 저장됨"],
    horizontal=True,
    label_visibility="collapsed",
    key="group_radio",
)
if "토픽" in group_choice:
    group_key = "topic"
elif "지역" in group_choice:
    group_key = "region"
else:
    group_key = "starred"

@st.fragment
def render_article_card(it: dict, idx: int, cat: str):
    """단일 기사 카드 — fragment로 격리되어 번역 중에도 다른 카드/탭 사용 가능."""
    url = it["link"]
    h = link_hash(url)
    read = state.is_read(h)
    starred = state.is_starred(h)

    title_prefix = "✓ " if read else ""
    star_prefix = "⭐ " if starred else ""
    title_style = f"<span style='color:#999'>{title_prefix}{star_prefix}{idx}. {it['ko_title']}</span>" if read else None
    if title_style:
        st.markdown(f"#### {title_style}", unsafe_allow_html=True)
    else:
        st.subheader(f"{star_prefix}{idx}. {it['ko_title']}")

    if not read:
        for line in it["ko_summary"].split("\n"):
            line = line.strip().lstrip("-•·").strip()
            if line:
                st.markdown(f"- {line}")
        st.caption(f"_원문 제목: {it['title']}_")

    btn_key = f"act_{cat}_{idx}_{h}"
    trans_state_key = f"shown_{btn_key}"

    shown = st.session_state.get(trans_state_key, False)
    trans_label = "📕 한글 본문 닫기" if shown else "📖 한글 본문 번역"
    read_label = "↺ 안 읽음" if read else "✓ 읽음"
    star_label = "⭐ 해제" if starred else "☆ 저장"

    cols = st.columns([1.2, 1.5, 1, 1, 2])
    cols[0].link_button("🔗 원문", url, use_container_width=True)
    if cols[1].button(trans_label, key=f"{btn_key}_trans", use_container_width=True):
        st.session_state[trans_state_key] = not shown
        st.rerun(scope="fragment")
    if cols[2].button(read_label, key=f"{btn_key}_read", use_container_width=True):
        state.toggle_read(h)
        if not read and st.session_state.get("hide_read", True):
            st.rerun()  # 카드 즉시 사라지도록 풀 리런
        else:
            st.rerun(scope="fragment")
    if cols[3].button(star_label, key=f"{btn_key}_star", use_container_width=True):
        state.toggle_starred(h)
        st.rerun(scope="fragment")

    if st.session_state.get(trans_state_key):
        with st.spinner("gemini가 본문을 번역 중... (최초 1회만, 다음부터는 캐시)"):
            try:
                text, cached = translate_article(url, it["title"])
                with st.container(border=True):
                    if cached:
                        st.caption("💾 캐시에서 즉시 로드")
                    else:
                        st.caption("✨ 새로 번역됨 (다음부터는 캐시)")
                    st.markdown(text)
            except Exception as e:
                st.error(f"번역 실패: {e}")

    st.divider()

def _filter_read(items: list[dict]) -> list[dict]:
    if not st.session_state.get("hide_read", True):
        return items
    return [it for it in items if not state.is_read(link_hash(it["link"]))]

# ── 검색 모드 ──
if search_q:
    q = search_q.lower()
    pool = load_all_recent_items(tuple(dates))
    hits = [
        it for it in pool
        if q in (it.get("ko_title","") + it.get("ko_summary","") + it.get("title","")).lower()
    ]
    hits = _filter_read(hits)
    st.subheader(f"🔍 검색 결과: '{search_q}' — {len(hits)}건")
    if not hits:
        st.info("일치하는 기사가 없습니다.")
    else:
        for idx, it in enumerate(hits[:50], 1):
            label = CATEGORIES.get(it["category"], {}).get("label", it["category"])
            st.caption(f"📅 {it.get('_date','?')}  ·  {label}")
            render_article_card(it, idx, f"search_{idx}")
            st.divider()
    st.stop()

# 포커스된 기사 (텔레그램 링크 진입) 상단 하이라이트
if focus_hash:
    if focused:
        with st.container(border=True):
            st.markdown(f"📌 **텔레그램 링크에서 진입한 기사** — {CAT_LABEL.get(focused['category'], focused['category'])}")
            render_article_card(focused, 1, f"focus_{focused['category']}")
        if st.button("← 전체 리포트로", type="secondary"):
            st.query_params.pop("article")
            st.rerun()
        st.divider()
    else:
        st.warning("링크의 기사를 현재 리포트에서 찾을 수 없습니다 (오래된 링크일 수 있음). 전체 리포트를 보여드립니다.")

# ── ⭐ 저장됨 모드 ──
if group_key == "starred":
    pool = load_all_recent_items(tuple(dates))
    starred_items = [it for it in pool if state.is_starred(link_hash(it["link"]))]
    st.subheader(f"⭐ 저장된 기사 — {len(starred_items)}건")
    if not starred_items:
        st.info("아직 저장한 기사가 없습니다. 기사 카드의 `☆ 저장` 버튼을 누르면 여기 모입니다.")
        st.stop()
    for idx, it in enumerate(starred_items, 1):
        label = CATEGORIES.get(it["category"], {}).get("label", it["category"])
        st.caption(f"📅 {it.get('_date','?')}  ·  {label}")
        render_article_card(it, idx, f"star_{idx}")
        st.divider()
    st.stop()

# ── 일반 모드 (토픽/지역 탭) ──
cat_order = [
    c for c in CATEGORIES
    if CATEGORIES[c]["group"] == group_key and c in by_cat
]
if not cat_order:
    st.info("이 그룹에 해당하는 기사가 아직 없습니다. 사이드바의 `🔄 지금 갱신` 클릭해보세요.")
    st.stop()

tab_labels = []
visible_by_cat: dict[str, list[dict]] = {}
for c in cat_order:
    filt = _filter_read(by_cat[c])
    visible_by_cat[c] = filt
    tab_labels.append(f"{CAT_LABEL[c]} ({len(filt)}/{len(by_cat[c])})")

tabs = st.tabs(tab_labels)

for tab, cat in zip(tabs, cat_order):
    with tab:
        if not visible_by_cat[cat]:
            st.info(f"읽지 않은 기사 없음. 사이드바에서 `✓ 읽은 글 숨기기`를 꺼서 다시 보기.")
            continue
        for idx, it in enumerate(visible_by_cat[cat], 1):
            render_article_card(it, idx, cat)

st.caption(f"리포트 날짜: {selected}  ·  자동 갱신 30분  ·  KST 22~06시 알림 OFF")
