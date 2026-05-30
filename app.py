"""월드 데일리 KO — Streamlit 뷰어 (on-demand 본문 번역 + 수동 새로고침)."""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).parent
load_dotenv(PROJECT_DIR / ".env")

from translate import translate_article, link_hash, is_cached
from fetch import CATEGORIES
import state

REPORTS_DIR = PROJECT_DIR / "reports"
KST = timezone(timedelta(hours=9))

APP_NAME = os.environ.get("APP_NAME", "월드 데일리 KO")
APP_TITLE = os.environ.get("APP_TITLE", "월드 데일리 리포트")
APP_SOURCES = os.environ.get("APP_SOURCES", "BBC · Guardian · Al Jazeera · NPR · TechCrunch · The Verge · Ars Technica · Nikkei Asia · SCMP · CNA")
APP_PAGE_ICON = os.environ.get("APP_PAGE_ICON", "📰")

st.set_page_config(page_title=APP_NAME, page_icon=APP_PAGE_ICON, layout="wide")

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

# 스와이프 deck에서 일괄 읽음 반영 (?swipe_read=h1,h2,...)
if "swipe_read" in qp:
    _batch = [h for h in qp["swipe_read"].split(",") if h]
    if _batch:
        state.mark_read_batch(_batch)
    del st.query_params["swipe_read"]
    st.rerun()

default_date = qp.get("date", dates[0] if dates else None)

with st.sidebar:
    st.title(f"{APP_PAGE_ICON} {APP_NAME}")
    st.caption(f"{APP_SOURCES}\n\n30분마다 자동 갱신")

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
    hide_read = st.checkbox("✓ 읽은 글 숨기기", value=True, key="hide_read",
                            help="ON: 읽음 표시한 글 숨김 (기본)  ·  OFF: 회색으로 하단에 정렬되어 표시")

    st.divider()
    st.caption("ℹ️ 매 30분 자동 갱신 · KST 22~06시 알림 끔")
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

st.title(f"{APP_TITLE} — {selected}")
# 오늘 데이터에 등장한 source들만 표시
sources_today = sorted({it.get("source", "BBC") for it in items})
st.caption(f"📊 총 {len(items)}건{ts_caption}  ·  출처: {' · '.join(sources_today)}")

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

# 그룹 선택 (📱 스와이프 / 📚 토픽 / 🌐 지역 / ⭐ 저장됨)
group_choice = st.radio(
    "분류",
    ["📱 스와이프", "📚 토픽", "🌐 지역", "⭐ 저장됨"],
    horizontal=True,
    label_visibility="collapsed",
    key="group_radio",
)
if "스와이프" in group_choice:
    group_key = "swipe"
elif "토픽" in group_choice:
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

    # hide_read ON + read 상태 → 빈 fragment 로 카드 + divider 즉시 비표시
    # (st.tabs 가 풀 리런 시 리셋되는 이슈로 fragment scope 만 사용 가능 → 이 방식이 최선)
    # 다음 페이지 갱신/탭 전환/필터 변경 시 _arrange() 가 정렬·필터링 재계산
    if read and st.session_state.get("hide_read", True):
        return

    title_prefix = "✓ " if read else ""
    star_prefix = "⭐ " if starred else ""
    source = it.get("source", "BBC")
    cached = is_cached(url)
    src_badge = f"<span style='background:#eef; color:#557; padding:2px 8px; border-radius:10px; font-size:0.75em; margin-left:8px; vertical-align:middle'>{source}</span>"
    cache_badge = (
        f"<span style='background:#e8f5e9; color:#2e7d32; padding:2px 8px; "
        f"border-radius:10px; font-size:0.75em; margin-left:6px; vertical-align:middle' "
        f"title='한글 본문 번역 캐시 있음 — 클릭 시 즉시 표시'>💾 번역됨</span>"
        if cached else ""
    )
    title_style = f"<span style='color:#999'>{title_prefix}{star_prefix}{idx}. {it['ko_title']}</span>" if read else None
    if title_style:
        st.markdown(f"#### {title_style} {src_badge}{cache_badge}", unsafe_allow_html=True)
    else:
        st.markdown(f"### {star_prefix}{idx}. {it['ko_title']} {src_badge}{cache_badge}", unsafe_allow_html=True)

    pub = _format_published(it.get("published", ""))
    if not read:
        for line in it["ko_summary"].split("\n"):
            line = line.strip().lstrip("-•·").strip()
            if line:
                st.markdown(f"- {line}")
        # 메타: 발행일 · 원문 제목
        meta_bits = []
        if pub:
            meta_bits.append(f"🕒 {pub}")
        meta_bits.append(f"_원문 제목: {it['title']}_")
        st.caption("  ·  ".join(meta_bits))
    else:
        # 읽은 글: 발행일만 짧게
        if pub:
            st.caption(f"🕒 {pub}  ·  _읽음 처리됨_")

    btn_key = f"act_{cat}_{idx}_{h}"
    trans_state_key = f"shown_{btn_key}"

    shown = st.session_state.get(trans_state_key, False)
    if shown:
        trans_label = "📕 한글 본문 닫기"
    elif cached:
        trans_label = "💾 한글 본문 보기"  # 즉시 로드됨
    else:
        trans_label = "📖 한글 본문 번역"   # gemini 호출 (~1분)
    read_label = "↺ 안 읽음" if read else "✓ 읽음"
    star_label = "⭐ 해제" if starred else "☆ 저장"

    cols = st.columns([1.2, 1.5, 1, 1, 2])
    cols[0].link_button("🔗 원문", url, use_container_width=True)
    if cols[1].button(trans_label, key=f"{btn_key}_trans", use_container_width=True):
        st.session_state[trans_state_key] = not shown
        st.rerun(scope="fragment")
    if cols[2].button(read_label, key=f"{btn_key}_read", use_container_width=True):
        state.toggle_read(h)
        # fragment 리런만 — 풀 리런 하면 st.tabs가 톱스토리로 리셋됨
        # 읽음 처리하면 카드가 회색 처리됨. 사이드바 '읽은 글 숨기기' ON이면 다음 페이지 갱신 때 사라짐
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

def _arrange(items: list[dict]) -> list[dict]:
    """hide_read ON → 읽음 글 제거 / OFF → 읽음 글은 하단으로."""
    if st.session_state.get("hide_read", True):
        return [it for it in items if not state.is_read(link_hash(it["link"]))]
    unread, read = [], []
    for it in items:
        (read if state.is_read(link_hash(it["link"])) else unread).append(it)
    return unread + read

def _format_published(s: str) -> str:
    """RSS 'published' 문자열 → 한국어 상대시간 / 절대시간."""
    if not s:
        return ""
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_kst = dt.astimezone(KST)
        now = datetime.now(KST)
        delta = now - dt_kst
        secs = int(delta.total_seconds())
        if secs < 60:
            return "방금 전"
        if secs < 3600:
            return f"{secs // 60}분 전"
        if secs < 86400:
            return f"{secs // 3600}시간 전"
        if delta.days == 1:
            return "어제"
        if delta.days < 7:
            return f"{delta.days}일 전"
        # 1주 이상은 절대 날짜
        if dt_kst.year == now.year:
            return dt_kst.strftime("%m월 %d일")
        return dt_kst.strftime("%Y-%m-%d")
    except Exception:
        return s[:25]

# ── 검색 모드 ──
if search_q:
    q = search_q.lower()
    pool = load_all_recent_items(tuple(dates))
    hits = [
        it for it in pool
        if q in (it.get("ko_title","") + it.get("ko_summary","") + it.get("title","")).lower()
    ]
    hits = _arrange(hits)
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

# ── 📱 스와이프 리더 모드 ──
if group_key == "swipe":
    st.subheader("📱 스와이프 리더")
    cats_present = [c for c in CATEGORIES if c in by_cat]
    options = ["전체"] + [CAT_LABEL[c] for c in cats_present]
    sel = st.selectbox("카테고리 선택", options, key="swipe_cat")
    if sel == "전체":
        pool = items
    else:
        _cat = next(c for c in cats_present if CAT_LABEL[c] == sel)
        pool = by_cat[_cat]

    skipped = st.session_state.setdefault("swipe_skipped", set())
    unread = [it for it in pool
              if not state.is_read(link_hash(it["link"])) and link_hash(it["link"]) not in skipped]

    # 그날 해당 분류의 총 기사 수가 분모, 읽은 수가 분자
    total = len(pool)
    cur_unread = sum(1 for it in pool if not state.is_read(link_hash(it["link"])))
    done = total - cur_unread  # 읽음 처리한 건수

    if not unread:
        skipped_here = len(skipped & {link_hash(it["link"]) for it in pool})
        if cur_unread == 0:
            st.success(f"🎉 이 분류의 기사 {total}건을 모두 읽었어요!")
        else:
            st.info(f"건너뛴 {skipped_here}건이 남았습니다.")
        if st.button("↺ 건너뛴 기사 다시 보기", use_container_width=True):
            st.session_state["swipe_skipped"] = set()
            st.rerun()
        st.stop()

    # 진행 바: 읽음 / 총 기사
    if total:
        st.progress(done / total, text=f"읽음 {done} / 총 {total}건  ·  남은 {len(unread)}건")

    it = unread[0]
    url = it["link"]; h = link_hash(url)
    source = it.get("source", "BBC")
    pub = _format_published(it.get("published", ""))
    cached = is_cached(url)

    with st.container(border=True):
        cat_label = CAT_LABEL.get(it["category"], it["category"])
        badges = f"**{cat_label}**  ·  `{source}`"
        if pub:
            badges += f"  ·  🕒 {pub}"
        if cached:
            badges += "  ·  💾 번역됨"
        st.markdown(badges)
        st.markdown(f"## {it['ko_title']}")
        for line in it["ko_summary"].split("\n"):
            line = line.strip().lstrip("-•·").strip()
            if line:
                st.markdown(f"- {line}")
        st.caption(f"_원문: {it['title']}_")

        # 본문 번역 (옵션)
        tkey = f"swipe_trans_{h}"
        if st.button("💾 한글 본문 보기" if cached else "📖 한글 본문 번역",
                     key=f"btn_{tkey}", use_container_width=True):
            st.session_state[tkey] = not st.session_state.get(tkey, False)
            st.rerun()
        if st.session_state.get(tkey):
            with st.spinner("번역 중..."):
                try:
                    text, _c = translate_article(url, it["title"])
                    with st.container(border=True):
                        st.markdown(text)
                except Exception as e:
                    st.error(f"번역 실패: {e}")

    # 액션 버튼 (크게)
    c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1.3])
    if c1.button("⏭ 건너뛰기", use_container_width=True):
        st.session_state["swipe_skipped"].add(h)
        st.rerun()
    c2.link_button("🔗 원문", url, use_container_width=True)
    if c3.button("⭐ 저장", use_container_width=True):
        state.toggle_starred(h)
        st.rerun()
    if c4.button("✓ 읽음, 다음 ▶", use_container_width=True, type="primary"):
        state.toggle_read(h)
        st.session_state.pop(tkey, None)
        st.rerun()

    st.caption("⏭ 건너뛰기: 읽음 처리 안 함 (이번 세션에서만 뒤로) · ✓ 읽음: 영구 처리 후 다음 기사")
    st.stop()

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
    arranged = _arrange(by_cat[c])
    visible_by_cat[c] = arranged
    # 탭 카운트: 읽지 않은 / 전체
    unread_n = sum(1 for it in by_cat[c] if not state.is_read(link_hash(it["link"])))
    tab_labels.append(f"{CAT_LABEL[c]} ({unread_n}/{len(by_cat[c])})")

tabs = st.tabs(tab_labels)

for tab, cat in zip(tabs, cat_order):
    with tab:
        if not visible_by_cat[cat]:
            st.info(f"읽지 않은 기사 없음. 사이드바에서 `✓ 읽은 글 숨기기`를 꺼서 다시 보기.")
            continue
        for idx, it in enumerate(visible_by_cat[cat], 1):
            render_article_card(it, idx, cat)

st.caption(f"리포트 날짜: {selected}  ·  자동 갱신 30분  ·  KST 22~06시 알림 OFF")
