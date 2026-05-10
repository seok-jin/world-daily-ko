"""BBC 기사 URL → 본문 텍스트 추출."""
from __future__ import annotations
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (compatible; BBC-Daily-Reader/1.0; personal use)"
TIMEOUT = 15
MAX_WORKERS = 8

def scrape_one(url: str) -> str:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        return f"(본문 조회 실패: {e})"

    soup = BeautifulSoup(r.text, "lxml")
    # BBC article body: <article> 안의 data-component="text-block" div들
    article = soup.find("article")
    if not article:
        return "(본문 영역을 찾지 못함)"
    blocks = article.find_all("div", attrs={"data-component": "text-block"})
    if not blocks:
        # fallback: 모든 p 태그
        blocks = [article]
    paras: list[str] = []
    for b in blocks:
        for p in b.find_all("p"):
            t = p.get_text(strip=True)
            if t:
                paras.append(t)
    if not paras:
        return "(본문 텍스트 없음)"
    body = "\n\n".join(paras)
    return body[:8000]  # 토큰 비용 제어

def scrape_many(urls: list[str]) -> list[str]:
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        return list(ex.map(scrape_one, urls))

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.bbc.com/news/articles/c626xjq0q0vo"
    print(scrape_one(url)[:1000])
