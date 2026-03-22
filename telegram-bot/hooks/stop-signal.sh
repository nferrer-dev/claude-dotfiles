#!/bin/bash
# Stop hook — writes Claude's response to a signal file for the Telegram bot.
# Uses nonce protocol. Only fires for sessions whose cwd matches a registered
# Telegram session (the bot uses a unique cwd to avoid desktop conflicts).

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
    if scwd == cwd:
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

# Pipe response via stdin to avoid ARG_MAX limits on long responses
# Use printf to avoid shell expansion of $, backticks, ! in response
printf '%s' "$RESPONSE" | python3 -c "
import json, sys
try:
    response = sys.stdin.read()
    data = json.loads(open(sys.argv[1]).read())
    if data.get('status') != 'waiting':
        sys.exit(0)
    nonce = data.get('nonce', '')
    if not nonce:
        sys.exit(0)
    out = {'nonce': nonce, 'status': 'done', 'response': response}
    with open(sys.argv[1], 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False)
except:
    pass
" "$SIGNAL_FILE" 2>/dev/null

exit 0
