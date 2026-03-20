"""Bot configuration — all secrets via env vars or local file."""

import json
import os
from pathlib import Path

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
PSMUX = os.environ.get("PSMUX_PATH", str(Path.home() / "AppData/Local/Microsoft/WinGet/Links/psmux.exe"))
CLAUDE = os.environ.get("CLAUDE_PATH", str(Path.home() / ".local/bin/claude.exe"))
MODE_FILE = Path.home() / ".claude" / "primary-interface.json"
DB_PATH = Path.home() / ".claude" / "telegram-bot.db"

MAX_MESSAGE_LENGTH = 4096
RESPONSE_TIMEOUT = 120
RESPONSE_POLL_INTERVAL = 2.0
PERMISSION_TIMEOUT = 300  # 5 minutes to respond to permission prompt

# Phase 6: Reliability
RATE_LIMIT_SECONDS = 5       # Min seconds between messages per session
MAX_QUEUE_SIZE = 20           # Max pending messages per session
STREAM_INTERVAL = 4.0         # Seconds between streaming updates to Telegram
HEALTH_FILE = Path.home() / ".claude" / "telegram-bot-health.json"
STALE_PROCESSING_SECONDS = 600  # Requeue messages stuck "processing" for 10+ min
