---
name: telegram
description: Switch primary interface to Telegram bot, attaching this session
---

Switch the primary interface from Claude Code to Telegram, attaching this conversation session. Do these steps in order:

1. Get the current session ID by running:
```bash
claude -p "echo session" --output-format json 2>/dev/null | jq -r '.session_id // empty'
```
If that doesn't work, check for the session ID in the environment or use the most recent session from `~/.claude/projects/`.

2. Generate a synopsis of this conversation (3-5 bullet points + last action taken, under 200 words).

3. Write the mode file with the session ID:
```bash
echo '{"mode": "telegram", "session_id": "SESSION_ID_HERE"}' > ~/.claude/primary-interface.json
```

4. Send the synopsis to Telegram:
```bash
curl -s -X POST "https://api.telegram.org/botYOUR_TELEGRAM_BOT_TOKEN/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": YOUR_TELEGRAM_USER_ID, "text": "Session attached to Telegram.\n\nSynopsis:\n<SYNOPSIS>"}'
```

5. Start the Telegram bot in the background if not already running:
```bash
python C:\Users\nferr\OneDrive\Documents\Projects\claude-telegram-bot\bot.py &
```

6. Tell me: "Telegram is now primary with session [ID]. Continue on @claude_njf_bot. Send /desktop there to switch back."

NOTE: If a previous session was attached and never detached, this command replaces it with the current session.
