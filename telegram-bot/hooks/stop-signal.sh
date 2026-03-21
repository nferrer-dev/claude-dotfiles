#!/bin/bash
# Stop hook — writes Claude's response to a signal file for the Telegram bot.
# Uses nonce protocol: bot writes {"nonce":"xxx","status":"waiting"},
# this hook writes {"nonce":"xxx","status":"done","response":"..."}.

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

# Only write if signal file exists and contains a waiting nonce
if [ ! -f "$SIGNAL_FILE" ]; then
  exit 0
fi

# Read the nonce from the waiting signal
NONCE=$(python3 -c "
import json, sys
try:
    data = json.loads(open(sys.argv[1]).read())
    if data.get('status') == 'waiting':
        print(data.get('nonce', ''))
except:
    pass
" "$SIGNAL_FILE" 2>/dev/null)

if [ -z "$NONCE" ]; then
  exit 0
fi

# Write response with matching nonce
python3 -c "
import json, sys
nonce = sys.argv[1]
response = sys.argv[2]
signal_file = sys.argv[3]
data = {'nonce': nonce, 'status': 'done', 'response': response}
with open(signal_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)
" "$NONCE" "$RESPONSE" "$SIGNAL_FILE" 2>/dev/null

exit 0
