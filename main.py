"""BBC → AI CLI 한국어 리포트 → Markdown + 푸시 (증분 + dedupe).

사용법:
    python main.py                        # 30분마다 cron — 신규 기사만 추가
    python main.py --full                 # 본문 스크래핑 + 전체 번역
    python main.py --per 5                # 카테고리당 기사 수
    python main.py --no-push              # 푸시 비활성화
"""
from __future__ import annotations
import argparse, io, json, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 같은 폴더의 .env 자동 로드 (있으면)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

import os
from fetch import fetch_all, Article
from summarize import summarize_all
from render import render
from push import push_all

REPORTS_DIR = Path(__file__).parent / "reports"

DEDUPE_WINDOW_DAYS = 7

def _load_existing(json_path: Path) -> tuple[list[dict], str | None]:
    """오늘 자 JSON에서 기존 items + last_update 로드 (구·신 포맷 모두 지원)."""
    if not json_path.exists():
        return [], None
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        return [], None
    if isinstance(data, dict):
        return data.get("items", []), data.get("last_update")
    return data, None  # 구 포맷 (list)

def _is_failed(it: dict) -> bool:
    """요약 실패 항목 — 재시도 대상 (dedupe pool에서 제외)."""
    return "(요약 실패)" in (it.get("ko_summary") or "")

def _recent_links(reports_dir: Path, days: int = DEDUPE_WINDOW_DAYS) -> set[str]:
    """최근 N일치 JSON에서 본 적 있는 모든 link 집합 (실패 항목은 제외)."""
    cutoff = datetime.now(KST).date() - timedelta(days=days)
    links: set[str] = set()
    for jp in reports_dir.glob("*.json"):
        try:
            d = datetime.strptime(jp.stem, "%Y-%m-%d").date()
        except ValueError:
            continue
        if d < cutoff:
            continue
        try:
            data = json.loads(jp.read_text(encoding="utf-8"))
        except Exception:
            continue
        items = data.get("items", []) if isinstance(data, dict) else data
        for it in items:
            if "link" in it and not _is_failed(it):
                links.add(it["link"])
    return links

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--full", action="store_true", help="본문 스크래핑 + 전체 번역")
    p.add_argument("--per", type=int, default=6, help="카테고리당 기사 수 (16카테고리 × 6 = 최대 96건/회)")
    p.add_argument("--no-push", action="store_true", help="Telegram/이메일 푸시 끄기")
    args = p.parse_args()
    mode = "full" if args.full else "summary"

    t0 = time.time()
    today = datetime.now(KST).strftime("%Y-%m-%d")
    json_path = REPORTS_DIR / f"{today}.json"
    md_path = REPORTS_DIR / f"{today}.md"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    existing_items, _ = _load_existing(json_path)
    seen_links = _recent_links(REPORTS_DIR, days=DEDUPE_WINDOW_DAYS)
    print(f"[1/4] BBC RSS 수집 (카테고리당 {args.per}건, 오늘 {len(existing_items)}건 / 최근 {DEDUPE_WINDOW_DAYS}일 dedupe pool {len(seen_links)}건)...", flush=True)
    arts = fetch_all(per_category=args.per)
    new_arts = [a for a in arts if a.link not in seen_links]
    print(f"      → 수집 {len(arts)}건, 신규 {len(new_arts)}건 ({time.time()-t0:.1f}s)", flush=True)

    # 실패 항목 재처리 (RSS에서 이미 사라진 경우라도 JSON에 남아있으면 직접 재시도)
    failed_items = [it for it in existing_items if _is_failed(it)]
    if failed_items:
        print(f"      · 기존 실패 항목 {len(failed_items)}건 → 즉시 재시도", flush=True)
        failed_arts = [
            Article(
                category=it["category"], title=it["title"],
                summary=it.get("summary", ""), link=it["link"],
                published=it.get("published", ""),
            )
            for it in failed_items
        ]
        retried = summarize_all(failed_arts, mode=mode)
        retried_by_link = {r["link"]: r for r in retried}
        existing_items = [
            retried_by_link.get(it["link"], it) if _is_failed(it) else it
            for it in existing_items
        ]
        recovered = sum(1 for it in existing_items if it["link"] in retried_by_link and not _is_failed(it))
        print(f"      · 재처리 결과: {recovered}/{len(failed_items)}건 복구", flush=True)

    if not new_arts:
        # 신규 없음 — JSON last_update만 갱신 (실패 재처리 결과는 위에서 existing_items에 반영됨)
        payload = {
            "date": today,
            "last_update": datetime.now(KST).isoformat(timespec="seconds"),
            "items": existing_items,
            "last_new_count": 0,
        }
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        # render도 갱신 (md 파일도 fresh)
        render(existing_items, REPORTS_DIR)
        print(f"\n✅ 신규 기사 없음 — last_update + render 갱신 ({time.time()-t0:.1f}s)")
        return 0

    bodies = None
    if args.full:
        print("[2/4] 신규 기사 본문 스크래핑 (병렬)...", flush=True)
        from scrape import scrape_many
        bodies = scrape_many([a.link for a in new_arts])
        ok = sum(1 for b in bodies if not b.startswith("(본문"))
        print(f"      → {ok}/{len(bodies)} 성공 ({time.time()-t0:.1f}s)", flush=True)

    print(f"[3/4] AI CLI 한국어 처리 — 신규 {len(new_arts)}건 (mode={mode})...", flush=True)
    new_items = summarize_all(new_arts, mode=mode, bodies=bodies)
    print(f"      → 신규 {len(new_items)}건 처리 완료 ({time.time()-t0:.1f}s)", flush=True)

    # 병합: 실패 항목은 기존에서 제거하고 새로 처리된 결과로 교체
    new_links = {it["link"] for it in new_items}
    existing_cleaned = [
        it for it in existing_items
        if not (_is_failed(it) and it["link"] in new_links)
    ]
    merged = new_items + existing_cleaned

    print("[4/4] Markdown + JSON 리포트 생성...", flush=True)
    render(merged, REPORTS_DIR)
    payload = {
        "date": today,
        "last_update": datetime.now(KST).isoformat(timespec="seconds"),
        "items": merged,
        "last_new_count": len(new_items),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"      → {md_path}", flush=True)
    print(f"      → {json_path} (총 {len(merged)}건, 신규 {len(new_items)}건)", flush=True)

    if not args.no_push:
        print("[+] 푸시...", flush=True)
        try:
            push_all(md_path, new_items=new_items, total=len(merged))
        except Exception as e:
            print(f"  ! 푸시 실패: {e}", flush=True)

    print(f"\n✅ 완료 ({time.time()-t0:.1f}s)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
