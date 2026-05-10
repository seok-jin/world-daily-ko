# BBC Daily Report

BBC News (5개 카테고리) → AI CLI로 한국어 요약 → 일일 Markdown 리포트.

## 구성
- `fetch.py` — BBC RSS (World/Business/Technology/Science/Health) 수집
- `summarize.py` — Claude/Gemini CLI로 한국어 헤드라인+3줄 요약 (또는 본문 번역)
- `render.py` — 카테고리별 Markdown 리포트 생성
- `main.py` — 파이프라인 진입점
- `reports/YYYY-MM-DD.md` — 결과물

## 로컬 실행 (Windows + Claude CLI)

```cmd
pip install -r requirements.txt
python main.py                  # 카테고리당 10건, 3줄 요약 (기본)
python main.py --full           # 본문 번역 모드
python main.py --per 5          # 카테고리당 5건만
```

또는 `run.bat` 더블클릭.

## EC2 운용 (Gemini CLI)

```bash
export BBC_AI_BACKEND=gemini
python3 main.py --per 10
```

cron 등록 예 (매일 KST 08:00 = UTC 23:00):
```
0 23 * * * cd /home/ubuntu/bbc_daily_report && BBC_AI_BACKEND=gemini /usr/bin/python3 main.py >> run.log 2>&1
```

## 백엔드 전환
환경변수 `BBC_AI_BACKEND` 로 결정:
- `claude` (기본) — 로컬 Claude Code CLI
- `gemini` — EC2 Gemini CLI

두 CLI 모두 `<cli> -p` + stdin 입력 → stdout JSON 응답 인터페이스.

## 카테고리당 기사 수
기본 10건 × 5카테고리 = 50건 / 일 (배치 6건씩 ≈ 9 호출, 약 1~2분 소요)

## 저작권
헤드라인 + 자체 작성 한국어 요약 + 원문 링크 형태로, 개인 열람용.
