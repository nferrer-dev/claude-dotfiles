#!/bin/bash
# Stop hook — writes Claude's response to a signal file for the Telegram bot.
# Only writes if the signal file contains "WAITING" (set by the bot before sending).

INPUT=$(cat)
RESPONSE=$(echo "$INPUT" | jq -r '.last_assistant_message // ""')
CWD=$(echo "$INPUT" | jq -r '.cwd // ""')

if [ -z "$RESPONSE" ] || [ "$RESPONSE" = "null" ]; then
  exit 0
fi

# Find session name whose cwd matches
SESSIONS_FILE="$HOME/.claude/telegram-sessions.json"
if [ ! -f "$SESSIONS_FILE" ]; then
  exit 0
fi

SESSION_NAME=$(python3 -c "
import json, sys
from pathlib import Path
cwd = sys.argv[1].replace('\\\\', '/').rstrip('/')
sessions = json.loads(Path.home().joinpath('.claude/telegram-sessions.json').read_text())
for name, info in sessions.items():
    scwd = info.get('cwd', '').replace('\\\\', '/').rstrip('/')
    if scwd.lower() == cwd.lower():
        print(name)
        break
" "$CWD" 2>/dev/null)

if [ -z "$SESSION_NAME" ]; then
  exit 0
fi

SIGNAL_FILE="$HOME/.claude/tg-signal-${SESSION_NAME}.json"

# Only write if the bot is waiting for a response
if [ -f "$SIGNAL_FILE" ] && grep -q "WAITING" "$SIGNAL_FILE" 2>/dev/null; then
  echo "$RESPONSE" > "$SIGNAL_FILE"
fi

exit 0
