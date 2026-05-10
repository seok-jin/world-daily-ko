"""BBC → AI CLI 한국어 리포트 → Markdown + 푸시.

사용법:
    python main.py                        # 기본: 헤드라인+3줄 요약
    python main.py --full                 # 본문 스크래핑 + 전체 번역
    python main.py --per 5                # 카테고리당 기사 수
    python main.py --no-push              # 푸시 비활성화
"""
from __future__ import annotations
import argparse, io, sys, time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 같은 폴더의 .env 자동 로드 (있으면)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

from fetch import fetch_all
from summarize import summarize_all
from render import render
from push import push_all

REPORTS_DIR = Path(__file__).parent / "reports"

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--full", action="store_true", help="본문 스크래핑 + 전체 번역")
    p.add_argument("--per", type=int, default=10, help="카테고리당 기사 수 (기본 10)")
    p.add_argument("--no-push", action="store_true", help="Telegram/이메일 푸시 끄기")
    args = p.parse_args()
    mode = "full" if args.full else "summary"

    t0 = time.time()
    print(f"[1/4] BBC RSS 수집 (카테고리당 {args.per}건)...", flush=True)
    arts = fetch_all(per_category=args.per)
    print(f"      → {len(arts)}건 수집 ({time.time()-t0:.1f}s)", flush=True)

    bodies = None
    if args.full:
        print(f"[2/4] 기사 본문 스크래핑 (병렬)...", flush=True)
        from scrape import scrape_many
        bodies = scrape_many([a.link for a in arts])
        ok = sum(1 for b in bodies if not b.startswith("(본문"))
        print(f"      → {ok}/{len(bodies)} 성공 ({time.time()-t0:.1f}s)", flush=True)

    print(f"[3/4] AI CLI 한국어 처리 (mode={mode})...", flush=True)
    items = summarize_all(arts, mode=mode, bodies=bodies)
    print(f"      → {len(items)}건 완료 ({time.time()-t0:.1f}s)", flush=True)

    print("[4/4] Markdown 리포트 생성...", flush=True)
    path = render(items, REPORTS_DIR)
    print(f"      → {path}", flush=True)

    if not args.no_push:
        print("[+] 푸시...", flush=True)
        try:
            push_all(path, total=len(items))
        except Exception as e:
            print(f"  ! 푸시 실패: {e}", flush=True)

    print(f"\n✅ 완료 ({time.time()-t0:.1f}s)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
