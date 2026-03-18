#!/bin/bash
# Interface Guard — blocks Claude Code input when Telegram is primary
INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt')
MODE_FILE="$HOME/.claude/primary-interface.json"

# Allow /telegram command to always pass through (it switches mode)
if echo "$PROMPT" | grep -qiE '^/telegram'; then
  exit 0
fi

# Check if Telegram is primary
if [ -f "$MODE_FILE" ]; then
  MODE=$(jq -r '.mode' "$MODE_FILE" 2>/dev/null)
  if [ "$MODE" = "telegram" ]; then
    echo "BLOCKED: Telegram is the primary interface. Send /desktop via Telegram to switch back." >&2
    exit 2
  fi
fi

exit 0
