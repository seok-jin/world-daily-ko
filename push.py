"""리포트 푸시: Telegram (Top 5 헤드라인 + Streamlit URL) / 이메일.

환경변수:
  Telegram:  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
  Streamlit: REPORT_BASE_URL (예: http://3.37.118.119:8504)
  Email:     SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, EMAIL_TO
"""
from __future__ import annotations
import os, re, smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
import requests

def _extract_top_headlines(md_text: str, n: int = 5) -> list[tuple[str, str]]:
    """리포트에서 (카테고리이모지+제목, 원문링크) 페어 상위 n건 추출."""
    out: list[tuple[str, str]] = []
    current_cat = ""
    lines = md_text.splitlines()
    for i, line in enumerate(lines):
        # 카테고리 헤더: ## 🌍 세계 <a id=...>
        m_cat = re.match(r"^## ([^\n<]+?)(\s*<a)?", line)
        if m_cat and any(e in line for e in ["🌍","💼","💻","🔬","🏥"]):
            current_cat = m_cat.group(1).strip()
            continue
        # 기사 헤더: ### N. 제목
        m_art = re.match(r"^### \d+\.\s+(.+)$", line)
        if m_art:
            title = m_art.group(1).strip()
            link = ""
            for j in range(i+1, min(i+12, len(lines))):
                lm = re.search(r"\[원문 보기\]\((https?://[^)]+)\)", lines[j])
                if lm:
                    link = lm.group(1)
                    break
            out.append((f"{current_cat} · {title}", link))
            if len(out) >= n:
                break
    return out

def push_telegram(report_path: Path, total: int | None = None) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        print("  · TELEGRAM 환경변수 없음 → 스킵", flush=True)
        return

    base_url = os.environ.get("REPORT_BASE_URL", "").rstrip("/")
    md = report_path.read_text(encoding="utf-8")
    headlines = _extract_top_headlines(md, n=5)

    lines = [f"📰 *BBC 데일리 리포트 — {report_path.stem}*"]
    if total:
        lines.append(f"_총 {total}건 · BBC News_")
    lines.append("")
    lines.append("*오늘의 헤드라인*")
    for i, (title, link) in enumerate(headlines, 1):
        # MarkdownV2가 까다로워서 일반 Markdown 사용
        if link:
            lines.append(f"{i}. [{title}]({link})")
        else:
            lines.append(f"{i}. {title}")

    if base_url:
        lines.append("")
        lines.append(f"📖 [전체 리포트 보기]({base_url}/?date={report_path.stem})")

    text = "\n".join(lines)
    api = f"https://api.telegram.org/bot{token}"
    r = requests.post(
        f"{api}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": "true",
        },
        timeout=15,
    )
    if not r.ok:
        # parse_mode 에러 폴백: 평문 발송
        requests.post(f"{api}/sendMessage",
                      data={"chat_id": chat_id, "text": text},
                      timeout=15).raise_for_status()
    print("  · Telegram 전송 완료", flush=True)

def push_email(report_path: Path, summary_text: str | None = None) -> None:
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    pw   = os.environ.get("SMTP_PASS")
    to   = os.environ.get("EMAIL_TO")
    if not all([host, user, pw, to]):
        print("  · SMTP 환경변수 없음 → 스킵", flush=True)
        return

    msg = MIMEMultipart()
    msg["From"] = user
    msg["To"] = to
    msg["Subject"] = f"BBC 데일리 리포트 — {report_path.stem}"
    body = summary_text or f"BBC News 한국어 리포트 ({report_path.stem}) — 첨부 파일 참고."
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with report_path.open("rb") as f:
        att = MIMEApplication(f.read(), _subtype="markdown")
        att.add_header("Content-Disposition", "attachment", filename=report_path.name)
        msg.attach(att)

    ctx = ssl.create_default_context()
    with smtplib.SMTP(host, port) as s:
        s.starttls(context=ctx)
        s.login(user, pw)
        s.sendmail(user, [to], msg.as_string())
    print(f"  · 이메일 전송 완료 → {to}", flush=True)

def push_all(report_path: Path, total: int | None = None,
             summary_text: str | None = None) -> None:
    push_telegram(report_path, total=total)
    push_email(report_path, summary_text)
