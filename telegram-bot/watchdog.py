r"""Watchdog for Claude Telegram Bot — restarts if health check is stale.

Run as a Windows Scheduled Task every 5 minutes:
  schtasks /create /tn "ClaudeBotWatchdog" /tr "python C:\Users\nferr\OneDrive\Documents\Projects\claude-telegram-bot\watchdog.py" /sc minute /mo 5

Or run continuously:
  python watchdog.py --loop
"""

import json
import subprocess
import sys
import time
from pathlib import Path

BOT_DIR = Path(__file__).parent
HEALTH_FILE = Path.home() / ".claude" / "telegram-bot-health.json"
PID_FILE = Path.home() / ".claude" / "telegram-bot.pid"
BOT_SCRIPT = BOT_DIR / "bot.py"
STALE_THRESHOLD = 120  # seconds before health is considered stale
CHECK_INTERVAL = 60    # seconds between checks in loop mode


def is_bot_healthy() -> bool:
    if not HEALTH_FILE.exists():
        return False
    try:
        data = json.loads(HEALTH_FILE.read_text())
        age = time.time() - data.get("timestamp", 0)
        return age < STALE_THRESHOLD
    except Exception:
        return False


def is_pid_alive(pid: int) -> bool:
    try:
        r = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True, timeout=10,
        )
        for line in r.stdout.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 2 and parts[1] == str(pid):
                return True
        return False
    except Exception:
        return False


def is_bot_running() -> bool:
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
        return is_pid_alive(pid)
    except (ValueError, OSError):
        return False


def start_bot():
    subprocess.Popen(
        [sys.executable, str(BOT_SCRIPT)],
        cwd=str(BOT_DIR),
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    # Don't write PID — the bot writes its own on startup.
    # Write a grace marker so we don't restart again before the bot starts.
    HEALTH_FILE.write_text(json.dumps({
        "alive": True,
        "timestamp": time.time(),
    }))
    print("[watchdog] Started bot, grace period active")


def check_and_restart():
    if is_bot_healthy():
        return
    if is_bot_running():
        print("[watchdog] Bot running but unhealthy — waiting for recovery")
        return
    print("[watchdog] Bot not running, starting...")
    start_bot()


if __name__ == "__main__":
    if "--loop" in sys.argv:
        print(f"[watchdog] Monitoring bot (check every {CHECK_INTERVAL}s)...")
        while True:
            check_and_restart()
            time.sleep(CHECK_INTERVAL)
    else:
        check_and_restart()
