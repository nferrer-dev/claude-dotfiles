---
name: telegram
description: Switch primary interface to Telegram bot, attaching this session
---

Switch the primary interface from Claude Code to Telegram. Do these steps in order:

1. Generate a synopsis of this conversation (3-5 bullet points + last action taken, under 200 words). Store it in a variable — you'll need it in step 3.

2. Write the mode file:
```bash
echo '{"mode": "telegram"}' > ~/.claude/primary-interface.json
```

3. Save the synopsis to the handoff file (the bot will send it automatically on startup):
```bash
cat > ~/.claude/handoff-synopsis.txt << 'SYNOPSIS_EOF'
<INSERT YOUR SYNOPSIS HERE>
SYNOPSIS_EOF
```

4. Start the Telegram bot if not already running:
```bash
python3 -c "
import subprocess, sys, os
from pathlib import Path
bot_dir = Path.home() / 'OneDrive/Documents/Projects/claude-telegram-bot'
pid_file = Path.home() / '.claude/telegram-bot.pid'
# Check if already running
if pid_file.exists():
    try:
        pid = int(pid_file.read_text().strip())
        r = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], capture_output=True, text=True, timeout=5)
        if str(pid) in r.stdout:
            print(f'Bot already running (PID {pid})')
            sys.exit(0)
    except Exception:
        pass
# Start new instance
subprocess.Popen(
    [sys.executable, '-u', 'bot.py'],
    cwd=str(bot_dir),
    creationflags=0x00000010,
    env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
)
print('Bot started')
"
```

5. Tell me: "Telegram is now primary. Continue on Telegram. Send /desktop there to switch back."

NOTE: If the bot is already running, it will pick up the handoff synopsis on its next health cycle. If not, it sends it on startup.
