# BBC Daily KO — 프로젝트 개요

> BBC News의 5개 카테고리 기사를 매일 자동 수집 → AI CLI로 한국어 번역·요약 → Markdown 리포트 생성 → Telegram·이메일 푸시까지 수행하는 일일 뉴스 다이제스트 시스템.

작성일: 2026-05-10  ·  GitHub: <https://github.com/seok-jin/bbc-daily-ko>

---

## 1. 무엇을 만들었나

| 영역 | 내용 |
|---|---|
| **수집** | BBC RSS — World / Business / Technology / Science / Health 5개 카테고리, 카테고리당 N건 (기본 10) |
| **본문 보강 (선택)** | `--full` 모드에서 BeautifulSoup + ThreadPool로 기사 URL 병렬 스크래핑 (한 건당 ~1~2초) |
| **AI 처리** | 백엔드 전환 가능: 로컬 Windows = `claude` CLI / EC2 = `gemini` CLI. JSON 배치 입출력으로 일관성 유지 |
| **출력 모드** | `summary`(기본): 한국어 헤드라인 + 3줄 요약 / `full`: 본문 전체 자연 번역 |
| **리포트** | 카테고리별로 그룹핑된 Markdown (`reports/YYYY-MM-DD.md`) |
| **푸시** | Telegram (메시지 + 첨부) / 이메일 SMTP 둘 다 지원, 자격증명은 `.env` |
| **실행 환경** | 로컬 Windows (테스트) → EC2 t3.small (cron 자동 운영) |

---

## 2. 디렉토리 구조

```
bbc_daily_report/
├── fetch.py            # BBC RSS 5카테고리 수집 → Article 데이터클래스 리스트
├── scrape.py           # 기사 URL → 본문 텍스트 (병렬, 8 worker)
├── summarize.py        # claude/gemini CLI 호출 + 배치 처리 + JSON 파싱
├── render.py           # Markdown 리포트 렌더 (카테고리별 섹션·앵커·원문 링크)
├── push.py             # Telegram (sendMessage + sendDocument) / SMTP 이메일
├── main.py             # 파이프라인 진입점 (1) RSS → (2) 스크랩 → (3) AI → (4) 렌더 → (+) 푸시
│
├── requirements.txt    # feedparser, requests, beautifulsoup4, lxml, python-dotenv
├── run.bat             # Windows 1-click 실행 (venv 자동 생성)
├── deploy_ec2.sh       # EC2 scp 배포 + venv 설치 + 스모크 테스트 자동화
├── .env.example        # 자격증명 템플릿 (실제 .env는 gitignore)
├── .gitignore          # .venv, .env, reports/, *.log
│
├── docs/
│   └── PROJECT_OVERVIEW.md   # 이 파일
└── reports/            # 생성된 일일 리포트 (git ignore)
```

---

## 3. 데이터 흐름

```
BBC RSS                   기사 URL                  Claude/Gemini CLI            Markdown                 Telegram/Email
(feedparser)  ──→  Article(meta) ──→  scrape body ──→  배치 prompt → JSON → ko_title/ko_summary  ──→  reports/YYYY-MM-DD.md  ──→  push
                                       (--full만)        (stdin pipe)                              (카테고리별 그룹)
```

### 백엔드 추상화
- `BBC_AI_BACKEND` 환경변수로 전환
  - `claude` → `claude -p` (with stdin) — 로컬 Windows
  - `gemini` → `gemini` (stdin only) — EC2
- 두 CLI 모두 stdin 파이프로 프롬프트 전달, stdout JSON 응답을 정규식으로 추출

### 배치 사이즈
| 모드 | BATCH_SIZE | TIMEOUT | 평균 소요 (5카테고리×10건) |
|---|---|---|---|
| summary | 6 | 240s | ~70~120초 |
| full | 2 | 420s | ~5~10분 |

---

## 4. 핵심 설계 결정

### a) RSS + 부분 스크래핑 하이브리드
- RSS는 빠르고 BBC가 공식 제공 (rate-limit 걱정 없음)
- 본문이 필요할 때만(`--full`) HTML 파싱 → 토큰·시간 비용 제어
- 본문은 8000자 cap (한 기사당)

### b) AI는 "직접 통합"이 아니라 CLI subprocess
- Claude API 호출이 아닌 Claude **Code** CLI (`claude -p`) → 별도 API 키 관리 불필요, 사용자 인증 그대로 사용
- EC2의 Gemini도 동일 패턴 → 백엔드 교체가 1줄 (`BACKEND_CMD` dict)

### c) 출력 형식: JSON-only 강제
- 프롬프트에서 "설명/마크다운/코드펜스 절대 금지" 명시
- 응답에서 정규식으로 `[...]` 배열 추출 → CLI 응답에 종종 섞이는 잡음 제거
- 파싱 실패 시 헤드라인만 fallback (전체 실패 방지)

### d) `.env` 기반 시크릿
- python-dotenv 자동 로드
- 토큰·SMTP 자격증명은 `.env` (gitignore)
- 개념 분리: `.env.example`(공개) / `.env`(비공개)

---

## 5. 사용법

### 로컬 (Windows + Claude CLI)
```cmd
python main.py                  # 카테고리당 10건, 3줄 요약, 푸시
python main.py --full           # 본문 전체 번역
python main.py --per 5          # 카테고리당 5건
python main.py --no-push        # 푸시 끄기 (개발/테스트)
```

### EC2 (Ubuntu + Gemini CLI)
```bash
cd ~/bbc_daily_report
BBC_AI_BACKEND=gemini ./.venv/bin/python main.py
```

### cron (KST 08:00 / UTC 23:00)
```cron
0 23 * * * cd /home/ubuntu/bbc_daily_report && ./.venv/bin/python main.py >> run.log 2>&1
```
(`.env`에 `BBC_AI_BACKEND=gemini` 넣으면 명령줄 export 불필요)

---

## 6. 인프라

| 항목 | 값 |
|---|---|
| EC2 | `3.37.118.119` (ubuntu, ap-northeast-2, t3.small — kr-scalping과 공유) |
| EC2 경로 | `/home/ubuntu/bbc_daily_report/` |
| Python | EC2 3.10.12 / 로컬 Windows 3.14 |
| AI CLI | EC2 gemini 0.35.3 / 로컬 Claude Code 2.1.89 |
| GitHub | <https://github.com/seok-jin/bbc-daily-ko> (public) |

---

## 7. 검증 결과 (2026-05-10)

| 시나리오 | 결과 |
|---|---|
| 로컬 Windows + Claude CLI, summary, 5건 | ✅ 50초, 한국어 자연스러움 |
| 로컬 Windows + Claude CLI, full(스크래핑), 5건 | ✅ 5분, 본문 전체 한국어 번역 양호 |
| EC2 Ubuntu + Gemini CLI, summary, 5건 | ✅ 36초, 한국어 정상 |
| Markdown 렌더 (목차·앵커·원문 링크) | ✅ |
| Telegram 푸시 | ⏳ 봇 `/start` 대기 중 (사용자 첫 메시지 필요) |
| Email 푸시 | 🟡 SMTP 자격증명 미설정 (선택) |

---

## 8. 보안·저작권 메모

- **저작권**: 헤드라인 + 자체 작성 한국어 요약 + 원문 링크 형태 (개인 열람용). 본문 전체 번역은 재배포·공개 금지.
- **시크릿**: 토큰·비밀번호는 `.env`에만, GitHub에는 `.env.example`만 노출.
- **rate-limit**: BBC RSS는 정책상 폴링 OK. 본문 스크래핑은 5건씩 동시 8 worker로 부담 낮음.

---

## 9. 향후 후보

- 카테고리 커스텀 (Sports, Entertainment 등 추가)
- 토픽 클러스터링 → 중복 기사 dedupe
- Notion / Obsidian 자동 동기화
- 이전 N일 비교 트렌드 ("한 주의 키워드")
- 다른 영문 매체 추가 (Reuters, AP, FT)
