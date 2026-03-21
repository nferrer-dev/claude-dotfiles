#!/bin/bash
# Stop hook — writes Claude's response to a signal file for the Telegram bot.
# ONLY fires inside psmux sessions (not desktop Claude Code).

# Check if we're inside a psmux/tmux session
# psmux sets TMUX environment variable when inside a session
if [ -z "$TMUX" ]; then
  exit 0
fi

INPUT=$(cat)
RESPONSE=$(echo "$INPUT" | jq -r '.last_assistant_message // ""')
CWD=$(echo "$INPUT" | jq -r '.cwd // ""')

if [ -z "$RESPONSE" ] || [ "$RESPONSE" = "null" ]; then
  exit 0
fi

SESSIONS_FILE="$HOME/.claude/telegram-sessions.json"
if [ ! -f "$SESSIONS_FILE" ]; then
  exit 0
fi

SESSION_NAME=$(python3 -c "
import json, sys
from pathlib import Path
cwd = sys.argv[1].replace('\\\\', '/').rstrip('/')
try:
    sessions = json.loads(Path.home().joinpath('.claude/telegram-sessions.json').read_text())
except:
    sys.exit(0)
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

if [ ! -f "$SIGNAL_FILE" ]; then
  exit 0
fi

# Read nonce and write response
python3 -c "
import json, sys
try:
    data = json.loads(open(sys.argv[1]).read())
    if data.get('status') != 'waiting':
        sys.exit(0)
    nonce = data.get('nonce', '')
    if not nonce:
        sys.exit(0)
    out = {'nonce': nonce, 'status': 'done', 'response': sys.argv[2]}
    with open(sys.argv[1], 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False)
except:
    pass
" "$SIGNAL_FILE" "$RESPONSE" 2>/dev/null

exit 0
