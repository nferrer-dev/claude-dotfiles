"""Telegram bot that forwards messages to Claude Code with primary interface enforcement."""

import json
import os
import subprocess
import time
from pathlib import Path

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_USER_ID = int(os.environ["TELEGRAM_USER_ID"])
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
POLL_INTERVAL = 2
CLAUDE_CMD = r"C:\Users\nferr\.local\bin\claude.exe"
MAX_RESPONSE_LENGTH = 4096
MODE_FILE = Path.home() / ".claude" / "primary-interface.json"


def get_state():
    try:
        return json.loads(MODE_FILE.read_text())
    except Exception:
        return {"mode": "desktop", "session_id": None}


def get_mode():
    return get_state().get("mode", "desktop")


def get_session_id():
    return get_state().get("session_id")


def set_mode(mode, session_id=None):
    state = get_state()
    state["mode"] = mode
    if session_id is not None:
        state["session_id"] = session_id
    MODE_FILE.write_text(json.dumps(state))


def api_call(method, payload=None):
    cmd = ["curl", "-s", "-X", "POST", f"{API_URL}/{method}",
           "-H", "Content-Type: application/json",
           "-d", json.dumps(payload or {})]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return json.loads(result.stdout) if result.stdout else {}
    except Exception:
        return {}


def send_message(chat_id, text):
    chunks = [text[i:i + MAX_RESPONSE_LENGTH] for i in range(0, len(text), MAX_RESPONSE_LENGTH)]
    for chunk in chunks:
        api_call("sendMessage", {"chat_id": chat_id, "text": chunk})


def send_typing(chat_id):
    api_call("sendChatAction", {"chat_id": chat_id, "action": "typing"})


def run_claude(prompt, session_id=None):
    cmd = [CLAUDE_CMD, "-p", prompt, "--output-format", "text"]
    if session_id:
        cmd.extend(["--resume", session_id])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        response = result.stdout.strip()
        if not response and result.stderr:
            response = f"Error: {result.stderr.strip()[:500]}"
        return response or "No response from Claude."
    except subprocess.TimeoutExpired:
        return "Claude timed out (5 min limit)."
    except FileNotFoundError:
        return "Error: 'claude' not found."
    except Exception as e:
        return f"Error: {e}"


def get_updates(offset=None):
    payload = {"timeout": 30, "allowed_updates": ["message"]}
    if offset:
        payload["offset"] = offset
    try:
        cmd = ["curl", "-s", "-X", "POST", f"{API_URL}/getUpdates",
               "-H", "Content-Type: application/json",
               "-d", json.dumps(payload)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
        return json.loads(result.stdout).get("result", []) if result.stdout else []
    except Exception:
        return []


def main():
    print("Claude Telegram Bot started")
    print(f"Allowed user: {ALLOWED_USER_ID}")
    print(f"Current mode: {get_mode()}")
    print("Polling for messages...")

    offset = None

    while True:
        updates = get_updates(offset)

        for update in updates:
            offset = update["update_id"] + 1

            msg = update.get("message")
            if not msg or "text" not in msg:
                continue

            user_id = msg["from"]["id"]
            chat_id = msg["chat"]["id"]
            text = msg["text"].strip()

            if user_id != ALLOWED_USER_ID:
                send_message(chat_id, "Unauthorized.")
                continue

            # Always read session_id from state file (may be updated by /telegram command)
            session_id = get_session_id()

            # /start — always allowed
            if text == "/start":
                mode = get_mode()
                sid = session_id or "none"
                send_message(chat_id, f"Claude Code bot ready.\nPrimary: {mode}\nSession: {sid}\n\n/desktop — switch to desktop\n/new — fresh session\n/ping — alive check\n/status — show state")
                continue

            if text == "/ping":
                send_message(chat_id, "Pong.")
                continue

            if text == "/status":
                sid = session_id or "none"
                send_message(chat_id, f"Primary: {get_mode()}\nSession: {sid}")
                continue

            # /desktop — switch primary to Claude Code, generate handoff
            if text == "/desktop":
                send_typing(chat_id)
                synopsis = run_claude(
                    "Summarize our conversation in 3-5 bullet points and state the last action taken. Keep it under 200 words. This is for a handoff to the desktop Claude Code interface.",
                    session_id
                )
                set_mode("desktop")
                handoff_path = Path.home() / ".claude" / "handoff-synopsis.txt"
                handoff_path.write_text(synopsis, encoding="utf-8")
                send_message(chat_id, f"Switched to desktop. Telegram input blocked.\n\nHandoff saved for /desktop command in Claude Code.")
                print(f"[{time.strftime('%H:%M:%S')}] Switched to desktop mode")
                continue

            if text == "/new":
                set_mode("telegram", session_id=None)
                send_message(chat_id, "Session cleared. Next message starts fresh.")
                continue

            # Enforce primary interface
            if get_mode() != "telegram":
                send_message(chat_id, "Desktop is primary. Run /telegram in Claude Code to switch here.")
                continue

            # Require a session
            if not session_id:
                send_message(chat_id, "No session attached. Run /telegram in Claude Code to attach a session first.")
                continue

            # Forward to Claude with session
            print(f"[{time.strftime('%H:%M:%S')}] [{session_id[:8]}] Message: {text[:80]}...")
            send_typing(chat_id)

            response = run_claude(text, session_id)
            print(f"[{time.strftime('%H:%M:%S')}] Response: {response[:80]}...")

            send_message(chat_id, response)

        if not updates:
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
