---
name: desktop
description: Switch primary interface back to Claude Code from Telegram
---

Switch the primary interface back to Claude Code desktop. Do these steps:

1. Read the handoff synopsis if it exists:
```bash
cat ~/.claude/handoff-synopsis.txt 2>/dev/null
```

2. Set mode to desktop:
```bash
echo '{"mode": "desktop"}' > ~/.claude/primary-interface.json
```

3. Present the handoff synopsis to me so I have context on what was discussed via Telegram.

4. Tell me: "Desktop is now primary. Telegram input is blocked until you run /telegram again."
