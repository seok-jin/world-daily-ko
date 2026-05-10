"""AI CLI(claude/gemini)로 BBC 영어 기사 → 한국어 요약 또는 본문번역.

backend:
  claude  → claude -p "<prompt>"           (로컬 Windows 테스트용)
  gemini  → gemini -p "<prompt>"           (EC2 운용용)
"""
from __future__ import annotations
import json, os, re, subprocess, sys
from dataclasses import asdict
from fetch import Article

BACKEND = os.environ.get("BBC_AI_BACKEND", "claude")  # claude | gemini
BATCH_SIZE = 6           # summary 모드
BATCH_SIZE_FULL = 2      # full 번역 모드 (긴 본문)
TIMEOUT = 240
TIMEOUT_FULL = 420

BACKEND_CMD = {
    "claude": ["claude", "-p"],   # claude -p (with stdin)
    "gemini": ["gemini"],         # gemini reads stdin directly
}

PROMPT_SUMMARY = """다음 BBC 영어 기사들을 한국어로 요약하라.

각 기사마다:
- "ko_title": 자연스러운 한국어 헤드라인 (직역 X, 신문 톤)
- "ko_summary": 핵심 3줄 요약 (각 줄 줄바꿈 \\n 으로 구분, 사실 위주)

출력은 반드시 아래 JSON 배열만. 설명/마크다운/코드펜스 절대 금지.
입력 순서대로 같은 길이 배열로 응답.

입력:
{payload}

출력 형식 예시:
[{{"ko_title":"...","ko_summary":"...\\n...\\n..."}}, ...]
"""

PROMPT_FULL = """다음 BBC 영어 기사들의 본문(body 필드, 없으면 summary)을 한국어로 자연스럽게 번역하라.

각 기사마다:
- "ko_title": 한국어 헤드라인 (신문 톤, 직역 X)
- "ko_summary": 본문을 한국어로 충실히 번역 (생략 없이 모든 문단, 문단 구분은 \\n\\n)

출력은 JSON 배열만. 설명/마크다운/코드펜스 금지. 입력 순서대로 같은 길이로 응답.

입력:
{payload}

출력 형식 예시:
[{{"ko_title":"...","ko_summary":"..."}}, ...]
"""

def _call_ai(prompt: str, timeout: int = TIMEOUT) -> str:
    if BACKEND not in BACKEND_CMD:
        raise ValueError(f"unknown BBC_AI_BACKEND: {BACKEND}")
    cmd = BACKEND_CMD[BACKEND]
    use_shell = (os.name == "nt")  # Windows .cmd shims
    proc = subprocess.run(
        cmd if not use_shell else " ".join(cmd),
        input=prompt,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout, shell=use_shell,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{BACKEND} CLI failed (rc={proc.returncode}): {proc.stderr.strip()[:300]}")
    return proc.stdout

def _extract_json_array(text: str):
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        raise ValueError(f"no JSON array in output:\n{text[:500]}")
    return json.loads(m.group(0))

def summarize_batch(batch: list[Article], mode: str = "summary",
                    bodies: list[str] | None = None) -> list[dict]:
    items = []
    for i, a in enumerate(batch):
        item = {"i": i, "title": a.title, "summary": a.summary}
        if bodies and bodies[i]:
            item["body"] = bodies[i]
        items.append(item)
    payload = json.dumps(items, ensure_ascii=False)
    tmpl = PROMPT_FULL if mode == "full" else PROMPT_SUMMARY
    to = TIMEOUT_FULL if mode == "full" else TIMEOUT
    raw = _call_ai(tmpl.format(payload=payload), timeout=to)
    arr = _extract_json_array(raw)
    if len(arr) != len(batch):
        raise ValueError(f"size mismatch: got {len(arr)}, expected {len(batch)}")
    return arr

def summarize_all(articles: list[Article], mode: str = "summary",
                  bodies: list[str] | None = None) -> list[dict]:
    bs = BATCH_SIZE_FULL if mode == "full" else BATCH_SIZE
    results: list[dict] = []
    for i in range(0, len(articles), bs):
        batch = articles[i:i+bs]
        bodies_batch = bodies[i:i+bs] if bodies else None
        print(f"  batch {i//bs + 1}: {len(batch)} articles ({mode})...", flush=True)
        try:
            arr = summarize_batch(batch, mode=mode, bodies=bodies_batch)
        except Exception as e:
            print(f"  ! batch failed ({e}); falling back to titles only", flush=True)
            arr = [{"ko_title": a.title, "ko_summary": "(요약 실패)"} for a in batch]
        for a, k in zip(batch, arr):
            results.append({**asdict(a), **k})
    return results

if __name__ == "__main__":
    from fetch import fetch_all
    arts = fetch_all(per_category=2)
    out = summarize_all(arts)
    print(json.dumps(out, ensure_ascii=False, indent=2))
