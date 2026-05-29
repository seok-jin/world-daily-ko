"""사용자 상태(읽음 / 즐겨찾기 / 알림 발송 기록) 영구 저장.

단일 사용자 가정 — JSON 1개 파일로 충분.
키: link_hash(URL)[:12] (translate.link_hash와 동일)
"""
from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from threading import Lock

STATE_DIR = Path(__file__).parent / "state"
STATE_FILE = STATE_DIR / "user.json"
_lock = Lock()

DEFAULT: dict = {"read": [], "starred": [], "notified": []}

def _read_raw() -> dict:
    if not STATE_FILE.exists():
        return dict(DEFAULT)
    try:
        d = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return {**DEFAULT, **d}
    except Exception:
        return dict(DEFAULT)

def _write_raw(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    # atomic write
    fd, tmp = tempfile.mkstemp(dir=str(STATE_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, STATE_FILE)
    except Exception:
        try: os.unlink(tmp)
        except: pass
        raise

def load() -> dict:
    with _lock:
        return _read_raw()

def is_read(h: str) -> bool:
    return h in load()["read"]

def is_starred(h: str) -> bool:
    return h in load()["starred"]

def already_notified(h: str) -> bool:
    return h in load()["notified"]

def _toggle(key: str, h: str) -> bool:
    with _lock:
        s = _read_raw()
        cur = set(s.get(key, []))
        if h in cur:
            cur.remove(h)
            present = False
        else:
            cur.add(h)
            present = True
        s[key] = sorted(cur)
        _write_raw(s)
        return present

def toggle_read(h: str) -> bool:
    return _toggle("read", h)

def toggle_starred(h: str) -> bool:
    return _toggle("starred", h)

def mark_notified(hashes: list[str]) -> None:
    if not hashes:
        return
    with _lock:
        s = _read_raw()
        s["notified"] = sorted(set(s.get("notified", [])) | set(hashes))
        _write_raw(s)

def mark_read_batch(hashes: list[str]) -> None:
    """여러 항목을 한 번에 읽음 처리 (스와이프 deck 일괄 반영)."""
    hashes = [h for h in hashes if h]
    if not hashes:
        return
    with _lock:
        s = _read_raw()
        s["read"] = sorted(set(s.get("read", [])) | set(hashes))
        _write_raw(s)
