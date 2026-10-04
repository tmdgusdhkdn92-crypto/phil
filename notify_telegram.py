#!/usr/bin/env python3
"""Send a short Phil status message to Telegram.

Operator-side helper for run-with-telegram.sh; not part of the protected
core. Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from the environment
(never from a file in this public repo) and never prints the token.

Usage: python3 notify_telegram.py {done|failed|test} [cycle] [total]
"""
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))


def env(name):
    value = os.environ.get(name)
    if value:
        return value
    if os.name == "nt":  # new user env vars may not reach an already-open shell
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                return winreg.QueryValueEx(key, name)[0]
        except OSError:
            return None
    return None


def run(*args):
    proc = subprocess.run(
        [sys.executable, *args], cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
    )
    return proc.stdout


def status_lines():
    try:
        s = json.loads(run("core/ledger.py", "status"))
        lines = [f"잔고 ${s['cash']:,.2f} · 열린 포지션 {s['open_positions']} · "
                 f"확정 {s['settled']} (승 {s['wins']}) · 실현손익 ${s['realized_pnl']:+,.2f}"]
    except (ValueError, KeyError):
        lines = ["잔고를 읽지 못했습니다"]
    score = [l for l in run("core/score.py").splitlines() if l.strip()][:2]
    if score and score[0].startswith("settled="):
        lines += score
    return lines


def last_cycle_line():
    path = os.path.join(ROOT, "journal", "cycles.log")
    try:
        with open(path, encoding="utf-8") as f:
            rows = [l.strip() for l in f if l.strip()]
    except OSError:
        return None
    if not rows:
        return None
    line = rows[-1]
    return line if len(line) <= 300 else line[:297] + "..."


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else "test"
    progress = f" {sys.argv[2]}/{sys.argv[3]}" if len(sys.argv) > 3 else ""
    now = datetime.now().strftime("%m/%d %H:%M")
    title = {
        "done": f"✅ Phil 사이클{progress} 완료 ({now})",
        "failed": f"⚠️ Phil 사이클{progress} 중단됨 ({now}) — 터미널을 확인하세요",
        "test": f"🧪 Phil 알림 테스트 ({now})",
    }.get(kind, f"Phil ({now})")
    parts = [title, *status_lines()]
    if kind == "done" and (cycle := last_cycle_line()):
        parts += ["", cycle]
    text = "\n".join(parts)

    token, chat_id = env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set; message not sent")
        print(text)
        return 1
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            ok = json.load(resp).get("ok")
    except Exception as e:  # never echo the URL: it contains the token
        print(f"telegram send failed: {type(e).__name__}")
        return 1
    print("telegram sent" if ok else "telegram send failed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
