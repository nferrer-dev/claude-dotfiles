"""Bot configuration — all secrets via env vars or local file."""

import json
import os
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USER_ID = int(os.environ.get("TELEGRAM_USER_ID", "0"))

# Load from local secrets file if env vars not set
SECRETS_FILE = Path(__file__).parent / ".secrets.json"
if (not BOT_TOKEN or not ALLOWED_USER_ID) and SECRETS_FILE.exists():
    _secrets = json.loads(SECRETS_FILE.read_text())
    BOT_TOKEN = BOT_TOKEN or _secrets.get("bot_token", "")
    ALLOWED_USER_ID = ALLOWED_USER_ID or int(_secrets.get("user_id", "0"))

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Tool paths — override via env vars if not in default locations
if IS_WINDOWS:
    _default_psmux = str(Path.home() / "AppData/Local/Microsoft/WinGet/Links/psmux.exe")
    _default_claude = str(Path.home() / ".local/bin/claude.exe")
else:
    _default_psmux = "tmux"
    _default_claude = "claude"
PSMUX = os.environ.get("PSMUX_PATH", _default_psmux)
CLAUDE = os.environ.get("CLAUDE_PATH", _default_claude)
MODE_FILE = Path.home() / ".claude" / "primary-interface.json"
DB_PATH = Path.home() / ".claude" / "telegram-bot.db"

MAX_MESSAGE_LENGTH = 4096
RESPONSE_TIMEOUT = 300
RESPONSE_POLL_INTERVAL = 2.0
PERMISSION_TIMEOUT = 300  # 5 minutes to respond to permission prompt

# Phase 6: Reliability
RATE_LIMIT_SECONDS = 5       # Min seconds between messages per session
MAX_QUEUE_SIZE = 20           # Max pending messages per session
HEALTH_FILE = Path.home() / ".claude" / "telegram-bot-health.json"
STALE_PROCESSING_SECONDS = 600  # Requeue messages stuck "processing" for 10+ min
