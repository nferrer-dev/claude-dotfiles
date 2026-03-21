"""Claude Telegram Bot — psmux-backed with session persistence.

Features: named sessions, SQLite queue, HITL permission buttons,
parallel execution via git worktrees, streaming responses,
rate limiting, error recovery, health heartbeat.
"""

import json
import logging
import os
import re
import sys
import threading
import time
from pathlib import Path

import requests

from config import (
    BOT_TOKEN, ALLOWED_USER_ID, MODE_FILE, API_URL,
    MAX_MESSAGE_LENGTH, RESPONSE_TIMEOUT, RESPONSE_POLL_INTERVAL,
    PERMISSION_TIMEOUT, RATE_LIMIT_SECONDS, MAX_QUEUE_SIZE,
    STREAM_INTERVAL, HEALTH_FILE, STALE_PROCESSING_SECONDS,
)
from core.psmux import PsmuxSession, list_sessions
from core.queue import MessageQueue, SessionHistory, init_db
from core.worktree import (
    is_git_repo, next_task_number, create_worktree,
    list_worktrees, remove_worktree, diff_stat,
    merge_branch, delete_branch, BRANCH_PREFIX,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("bot")
SESSIONS_FILE = Path.home() / ".claude" / "telegram-sessions.json"

# Persistent HTTP session for reliable TLS
http = requests.Session()
try:
    http.get(f"{API_URL}/getMe", timeout=5)
except Exception:
    pass

# ── Session State ────────────────────────────────────────────

active_psmux: dict[str, PsmuxSession] = {}
active_session_name: str = None
queue = MessageQueue()
history = SessionHistory()
session_workers: dict[str, threading.Thread] = {}
yolo_sessions: set[str] = set()
parallel_sessions: set[str] = set()
last_message_time: dict[str, float] = {}  # session_name -> timestamp

# Thread synchronization
worker_lock = threading.Lock()
permission_events: dict[str, threading.Event] = {}
permission_results: dict[str, str] = {}  # session_name -> "y"/"n"/"a"
permission_lock = threading.Lock()


def load_sessions_config() -> dict:
    try:
        return json.loads(SESSIONS_FILE.read_text())
    except Exception:
        return {}


def save_sessions_config(config: dict):
    SESSIONS_FILE.write_text(json.dumps(config, indent=2))


def get_mode() -> str:
    try:
        return json.loads(MODE_FILE.read_text()).get("mode", "desktop")
    except Exception:
        return "desktop"


def set_mode(mode: str):
    MODE_FILE.write_text(json.dumps({"mode": mode}))


def parse_target(text: str) -> tuple:
    if text.startswith("#") and " " in text:
        name, rest = text[1:].split(" ", 1)
        return name, rest
    return None, text


def write_health():
    """Write heartbeat file for external monitors."""
    HEALTH_FILE.write_text(json.dumps({
        "alive": True,
        "timestamp": time.time(),
        "workers": len(session_workers),
        "sessions": len(active_psmux),
    }))


HANDOFF_FILE = Path.home() / ".claude" / "handoff-synopsis.txt"


def _send_handoff_synopsis():
    """Send handoff synopsis to Telegram if one exists, then delete it."""
    if not HANDOFF_FILE.exists():
        return
    try:
        synopsis = HANDOFF_FILE.read_text().strip()
        if not synopsis:
            return
        config = load_sessions_config()
        session_name = active_session_name or "unknown"
        msg = f"[{session_name}] Desktop -> Telegram\n\n{synopsis}"
        send_message(ALLOWED_USER_ID, msg)
        HANDOFF_FILE.unlink()
        log.info("Handoff synopsis sent to Telegram")
    except Exception as e:
        log.error(f"Failed to send handoff synopsis: {e}")


# ── Telegram API ─────────────────────────────────────────────

def api_call(method, payload=None):
    for attempt in range(3):
        try:
            r = http.post(f"{API_URL}/{method}", json=payload or {}, timeout=10)
            if r.status_code == 429:
                retry_after = r.json().get("parameters", {}).get("retry_after", 5)
                log.warning(f"Rate limited on {method}, retrying in {retry_after}s")
                time.sleep(retry_after)
                continue
            if r.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            return r.json()
        except Exception as e:
            if attempt < 2:
                time.sleep(1)
            else:
                log.error(f"api_call {method} failed: {e}")
    return {}


def send_message(chat_id, text, reply_markup=None):
    result = None
    for i in range(0, len(text), MAX_MESSAGE_LENGTH):
        payload = {
            "chat_id": chat_id,
            "text": text[i:i + MAX_MESSAGE_LENGTH],
        }
        if reply_markup and i == 0:
            payload["reply_markup"] = reply_markup
        result = api_call("sendMessage", payload)
    # Return message_id of the last sent chunk (useful for streaming edits)
    if result and result.get("ok"):
        return result["result"]["message_id"]
    return None


def send_typing(chat_id):
    api_call("sendChatAction", {"chat_id": chat_id, "action": "typing"})


def answer_callback(callback_id, text=""):
    api_call("answerCallbackQuery", {
        "callback_query_id": callback_id,
        "text": text,
    })


def edit_message_text(chat_id, message_id, text):
    # Truncate to Telegram's max; silently handles MessageNotModified
    text = text[:MAX_MESSAGE_LENGTH]
    result = api_call("editMessageText", {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
    })
    # 400 "message is not modified" is expected during streaming
    if not result.get("ok") and "not modified" in str(result.get("description", "")):
        pass
    return result


def get_updates(offset=None):
    payload = {
        "timeout": 30,
        "allowed_updates": ["message", "callback_query"],
    }
    if offset:
        payload["offset"] = offset
    try:
        r = http.post(f"{API_URL}/getUpdates", json=payload, timeout=35)
        return r.json().get("result", [])
    except Exception:
        return []


# ── psmux Session Management ────────────────────────────────

def get_or_create_session(name: str) -> PsmuxSession:
    global active_psmux
    if name in active_psmux and active_psmux[name].is_alive():
        return active_psmux[name]

    config = load_sessions_config()
    if name not in config:
        return None

    cwd = config[name].get("cwd", r"C:\Windows\System32")
    session = PsmuxSession(name, cwd)

    if not session.is_alive():
        perm_mode = "auto" if name in yolo_sessions else "default"
        log.info(f"Starting psmux session: {name} ({cwd}) [mode={perm_mode}]")
        session.create()
        session.launch_claude(permission_mode=perm_mode)

    active_psmux[name] = session
    return session


def format_sessions() -> str:
    config = load_sessions_config()
    psmux_names = {s["name"] for s in list_sessions()}
    lines = []
    # Separate parent sessions from sub-sessions
    parents = {n: i for n, i in config.items() if "parent" not in i}
    children = {n: i for n, i in config.items() if "parent" in i}

    for name, info in parents.items():
        running = "running" if name in psmux_names else "stopped"
        marker = " *" if name == active_session_name else ""
        yolo = " [YOLO]" if name in yolo_sessions else ""
        parallel = " [PARALLEL]" if name in parallel_sessions else ""
        lines.append(f"#{name} [{running}]{marker}{yolo}{parallel} - {info.get('cwd', '?')}")
        # Show child worktree sessions grouped under parent
        for cname, cinfo in children.items():
            if cinfo.get("parent") == name:
                c_running = "running" if cname in psmux_names else "stopped"
                branch = cinfo.get("branch", "")
                lines.append(f"  └ #{cname} [{c_running}] branch:{branch}")

    return "\n".join(lines) if lines else "No sessions."


# ── Permission Handling (HITL) ──────────────────────────────

def make_permission_keyboard(session_name: str) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "Approve", "callback_data": f"perm:y:{session_name}"},
                {"text": "Deny", "callback_data": f"perm:n:{session_name}"},
            ],
            [
                {"text": "Approve All (session)", "callback_data": f"perm:a:{session_name}"},
                {"text": "YOLO mode", "callback_data": f"perm:yolo:{session_name}"},
            ],
        ]
    }


def handle_permission_callback(callback_query):
    """Handle inline keyboard button press for permission prompts."""
    data = callback_query.get("data", "")
    callback_id = callback_query["id"]
    msg = callback_query.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")

    if not data.startswith("perm:"):
        return

    parts = data.split(":", 2)
    if len(parts) < 3:
        return

    action = parts[1]
    session_name = parts[2]

    if action == "yolo":
        # Enable YOLO mode — restart session with auto permissions
        yolo_sessions.add(session_name)
        # Auto-approve current prompt
        with permission_lock:
            permission_results[session_name] = "y"
            if session_name in permission_events:
                permission_events[session_name].set()
        answer_callback(callback_id, f"YOLO enabled for #{session_name}")
        if chat_id and message_id:
            edit_message_text(chat_id, message_id,
                              f"YOLO enabled for #{session_name}. All future permissions auto-approved.")
        log.info(f"[{session_name}] YOLO mode enabled")
        return

    # y = approve once, n = deny, a = approve always for session
    with permission_lock:
        permission_results[session_name] = action
        if session_name in permission_events:
            permission_events[session_name].set()

    labels = {"y": "Approved", "n": "Denied", "a": "Approved (always)"}
    label = labels.get(action, action)
    answer_callback(callback_id, label)
    if chat_id and message_id:
        original_text = msg.get("text", "")
        edit_message_text(chat_id, message_id, f"{original_text}\n\n-> {label}")
    log.info(f"[{session_name}] Permission {label}")


def make_permission_handler(session_name: str, chat_id: int):
    """Create an on_permission callback for a session worker."""
    def on_permission(details: dict) -> str:
        # YOLO mode: auto-approve without sending buttons
        if session_name in yolo_sessions:
            log.info(f"[{session_name}] YOLO: auto-approving {details.get('tool', '?')}")
            return "y"

        # Send inline keyboard to Telegram
        tool = details.get("tool", "Unknown")
        context = details.get("context", "")
        text = f"[{session_name}] Permission request: {tool}\n\n{context}"
        keyboard = make_permission_keyboard(session_name)
        send_message(chat_id, text, reply_markup=keyboard)
        log.info(f"[{session_name}] Permission prompt sent for {tool}")

        # Wait for callback response
        event = threading.Event()
        with permission_lock:
            permission_events[session_name] = event
            permission_results.pop(session_name, None)

        if event.wait(timeout=PERMISSION_TIMEOUT):
            with permission_lock:
                result = permission_results.pop(session_name, "n")
                permission_events.pop(session_name, None)
            log.info(f"[{session_name}] Permission response: {result}")
            return result
        else:
            # Timeout — auto-deny
            with permission_lock:
                permission_events.pop(session_name, None)
                permission_results.pop(session_name, None)
            send_message(chat_id, f"[{session_name}] Permission timed out — denied.")
            log.info(f"[{session_name}] Permission timed out")
            return "n"

    return on_permission


# ── Parallel Task Creation ────────────────────────────────────

def _create_parallel_task(parent_name: str, config: dict, chat_id: int) -> str | None:
    """Create a worktree sub-session for parallel execution.

    Returns the task session name, or None on failure.
    """
    parent_cwd = config[parent_name].get("cwd", "")
    task_num = next_task_number(parent_cwd, parent_name)
    task_name = f"{parent_name}-task-{task_num}"
    branch = f"{BRANCH_PREFIX}{task_name}"

    ok, result = create_worktree(parent_cwd, task_name)
    if not ok:
        send_message(chat_id, f"Worktree creation failed: {result}\nFalling back to serial.")
        log.error(f"[{parent_name}] Worktree failed: {result}")
        return None

    wt_path = result

    # Register sub-session in config
    config[task_name] = {
        "cwd": wt_path,
        "parent": parent_name,
        "branch": branch,
    }
    save_sessions_config(config)

    send_message(chat_id, f"Spawned #{task_name} (branch: {branch})")
    log.info(f"[{task_name}] Worktree created at {wt_path}")
    return task_name


# ── Message Processing ───────────────────────────────────────

def process_message(chat_id, text):
    global active_session_name

    # Commands
    if text == "/start":
        send_message(chat_id,
                     f"Claude Bot v2 (psmux + HITL)\nMode: {get_mode()}\n\n"
                     f"{format_sessions()}\n\n"
                     "Commands: /sessions /switch /close /yolo /desktop /ping /health\n"
                     "Parallel: /parallel /serial /branches /diff /merge /discard\n"
                     "Send: #name message, or just type")
        return

    if text == "/ping":
        send_message(chat_id, "Pong.")
        return

    if text == "/sessions":
        send_message(chat_id, f"Mode: {get_mode()}\n\n{format_sessions()}")
        return

    if text.startswith("/switch"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Usage: /switch <name>")
            return
        name = parts[1].strip()
        config = load_sessions_config()
        if name not in config:
            send_message(chat_id, f"Unknown: {name}")
            return
        active_session_name = name
        send_message(chat_id, f"Active: #{name}")
        return

    if text.startswith("/close"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Usage: /close <name>")
            return
        name = parts[1].strip()
        if name in active_psmux:
            active_psmux[name].kill()
            active_psmux.pop(name, None)
        send_message(chat_id, f"Closed: #{name}")
        return

    if text.startswith("/register"):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            send_message(chat_id, "Usage: /register <name> <path>")
            return
        name, path = parts[1], parts[2].strip().strip('"')
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            send_message(chat_id, "Invalid name. Use only letters, numbers, - and _")
            return
        p = Path(path)
        if not p.is_absolute() or not p.exists() or not p.is_dir():
            send_message(chat_id, f"Invalid path: {path} (must be absolute, existing directory)")
            return
        if any(c in str(p) for c in '&|;`$(){}'):
            send_message(chat_id, "Path contains invalid characters.")
            return
        config = load_sessions_config()
        config[name] = {"cwd": str(p)}
        save_sessions_config(config)
        send_message(chat_id, f"Registered: #{name} -> {p}")
        return

    if text.startswith("/yolo"):
        parts = text.split(maxsplit=1)
        name = parts[1].strip() if len(parts) > 1 else active_session_name
        if not name:
            send_message(chat_id, "Usage: /yolo [name]")
            return
        if name in yolo_sessions:
            yolo_sessions.discard(name)
            # Restart session with default permissions
            if name in active_psmux:
                active_psmux[name].kill()
                active_psmux.pop(name, None)
                send_message(chat_id,
                             f"YOLO OFF for #{name}. Permissions will be relayed.\n"
                             "Session restarting with permission prompts.")
            else:
                send_message(chat_id, f"YOLO OFF for #{name}. Permissions will be relayed.")
            log.info(f"[{name}] YOLO disabled")
        else:
            yolo_sessions.add(name)
            # Restart session with auto permissions
            if name in active_psmux:
                active_psmux[name].kill()
                active_psmux.pop(name, None)
                send_message(chat_id,
                             f"YOLO ON for #{name}. All permissions auto-approved.\n"
                             "Session restarting with auto mode.")
            else:
                send_message(chat_id, f"YOLO ON for #{name}. All permissions auto-approved.")
            log.info(f"[{name}] YOLO enabled")
        return

    if text == "/desktop":
        # Build synopsis from recent history across all active sessions
        handoff_file = Path.home() / ".claude" / "handoff-synopsis.txt"
        config = load_sessions_config()
        synopsis_lines = ["Telegram -> Desktop\n"]
        for sname in config:
            if "parent" in config[sname]:
                continue
            entries = history.recent(sname, 10)
            if entries:
                synopsis_lines.append(f"#{sname}:")
                for e in entries:
                    prefix = ">" if e["role"] == "user" else "<"
                    synopsis_lines.append(f"  {prefix} {e['text'][:120]}")
                synopsis_lines.append("")
        handoff_file.write_text("\n".join(synopsis_lines))
        set_mode("desktop")
        send_message(chat_id,
                     "Switched to desktop. Synopsis saved.\n"
                     "Run /desktop in Claude Code to resume with context.")
        log.info("-> desktop (synopsis saved)")
        return

    if text == "/queue":
        pending = queue.pending_all()
        if pending:
            lines = [f"#{n}: {c} pending" for n, c in pending.items()]
            send_message(chat_id, "Queue:\n" + "\n".join(lines))
        else:
            send_message(chat_id, "Queue empty.")
        return

    if text == "/health":
        psmux_names = {s["name"] for s in list_sessions()}
        alive_workers = {n for n, t in session_workers.items() if t.is_alive()}
        lines = [
            f"Workers: {len(alive_workers)} active",
            f"psmux sessions: {len(psmux_names)}",
            f"Parallel: {', '.join(parallel_sessions) or 'none'}",
            f"YOLO: {', '.join(yolo_sessions) or 'none'}",
        ]
        pending = queue.pending_all()
        if pending:
            lines.append(f"Queue: {sum(pending.values())} pending")
        send_message(chat_id, "\n".join(lines))
        return

    if text.startswith("/history"):
        parts = text.split(maxsplit=2)
        name = parts[1] if len(parts) > 1 else active_session_name
        try:
            limit = max(1, min(int(parts[2]), 50)) if len(parts) > 2 else 10
        except ValueError:
            send_message(chat_id, "Usage: /history <name> [count]")
            return
        if not name:
            send_message(chat_id, "Usage: /history <name> [count]")
            return
        entries = history.recent(name, limit)
        if entries:
            lines = [f"{'>' if e['role']=='user' else '<'} {e['text'][:100]}" for e in entries]
            send_message(chat_id, f"History #{name} (last {len(entries)}):\n" + "\n".join(lines))
        else:
            send_message(chat_id, f"No history for #{name}")
        return

    # ── Parallel / Worktree Commands ─────────────────────────

    if text.startswith("/parallel") or text.startswith("/serial"):
        is_parallel = text.startswith("/parallel")
        parts = text.split(maxsplit=1)
        name = parts[1].strip() if len(parts) > 1 else active_session_name
        if not name:
            send_message(chat_id, f"Usage: /{'parallel' if is_parallel else 'serial'} [name]")
            return
        config = load_sessions_config()
        if name not in config:
            send_message(chat_id, f"Unknown session: {name}")
            return
        cwd = config[name].get("cwd", "")
        if is_parallel:
            if not is_git_repo(cwd):
                send_message(chat_id, f"#{name} is not a git repo. Parallel mode requires git.")
                return
            parallel_sessions.add(name)
            send_message(chat_id, f"Parallel mode ON for #{name}. Each message spawns a worktree.")
        else:
            parallel_sessions.discard(name)
            send_message(chat_id, f"Parallel mode OFF for #{name}. Messages route to main session.")
        return

    if text.startswith("/branches"):
        parts = text.split(maxsplit=1)
        name = parts[1].strip() if len(parts) > 1 else active_session_name
        if not name:
            send_message(chat_id, "Usage: /branches [name]")
            return
        config = load_sessions_config()
        if name not in config:
            send_message(chat_id, f"Unknown session: {name}")
            return
        cwd = config[name].get("cwd", "")
        if not is_git_repo(cwd):
            send_message(chat_id, f"#{name} is not a git repo.")
            return
        psmux_names = {s["name"] for s in list_sessions()}
        worktrees = list_worktrees(cwd)
        prefix = f"{BRANCH_PREFIX}{name}-task-"
        lines = [f"Branches for #{name}:"]
        found = False
        for wt in worktrees:
            branch = wt.get("branch", "")
            if branch.startswith(prefix):
                task_name = branch.replace(BRANCH_PREFIX, "")
                status = "running" if task_name in psmux_names else "stopped"
                lines.append(f"  {branch} [{status}]")
                found = True
        if not found:
            lines.append("  No worktree branches.")
        send_message(chat_id, "\n".join(lines))
        return

    if text.startswith("/diff "):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Usage: /diff <task-name>")
            return
        task_name = parts[1].strip()
        branch = f"{BRANCH_PREFIX}{task_name}"
        # Find the parent repo
        config = load_sessions_config()
        parent = config.get(task_name, {}).get("parent")
        if not parent or parent not in config:
            send_message(chat_id, f"Unknown task: {task_name}")
            return
        cwd = config[parent].get("cwd", "")
        stat = diff_stat(cwd, branch)
        send_message(chat_id, f"Diff for {branch}:\n{stat}")
        return

    if text.startswith("/merge "):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Usage: /merge <task-name>")
            return
        task_name = parts[1].strip()
        config = load_sessions_config()
        task_info = config.get(task_name)
        if not task_info or "parent" not in task_info:
            send_message(chat_id, f"Unknown task: {task_name}")
            return
        parent = task_info["parent"]
        parent_cwd = config[parent].get("cwd", "")
        branch = task_info.get("branch", f"{BRANCH_PREFIX}{task_name}")
        wt_path = task_info.get("cwd", "")

        # Kill psmux session if running
        if task_name in active_psmux:
            active_psmux[task_name].kill()
            active_psmux.pop(task_name, None)
        with worker_lock:
            session_workers.pop(task_name, None)

        # Remove worktree first (must happen before merge from main repo)
        if wt_path:
            remove_worktree(parent_cwd, wt_path)

        # Merge branch into main
        ok, msg = merge_branch(parent_cwd, branch)
        if not ok:
            send_message(chat_id, f"Merge failed: {msg}")
            return

        # Delete the branch
        delete_branch(parent_cwd, branch)

        # Remove from sessions config
        del config[task_name]
        save_sessions_config(config)

        send_message(chat_id, f"Merged {branch} into main and cleaned up.")
        log.info(f"[{task_name}] Merged and removed")
        return

    if text.startswith("/discard "):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(chat_id, "Usage: /discard <task-name>")
            return
        task_name = parts[1].strip()
        config = load_sessions_config()
        task_info = config.get(task_name)
        if not task_info or "parent" not in task_info:
            send_message(chat_id, f"Unknown task: {task_name}")
            return
        parent = task_info["parent"]
        parent_cwd = config[parent].get("cwd", "")
        branch = task_info.get("branch", f"{BRANCH_PREFIX}{task_name}")
        wt_path = task_info.get("cwd", "")

        # Kill psmux session
        if task_name in active_psmux:
            active_psmux[task_name].kill()
            active_psmux.pop(task_name, None)
        with worker_lock:
            session_workers.pop(task_name, None)

        # Remove worktree
        if wt_path:
            remove_worktree(parent_cwd, wt_path)

        # Delete branch
        delete_branch(parent_cwd, branch)

        # Remove from config
        del config[task_name]
        save_sessions_config(config)

        send_message(chat_id, f"Discarded {task_name} (worktree + branch removed).")
        log.info(f"[{task_name}] Discarded")
        return

    # Mode check
    if get_mode() != "telegram":
        send_message(chat_id, "Desktop is primary. Run /telegram in Claude Code.")
        return

    # Route message (parallel or serial)
    config = load_sessions_config()
    target, prompt = parse_target(text)

    if target and target not in config:
        send_message(chat_id, f"Unknown: #{target}\nAvailable: {', '.join(config.keys())}")
        return

    if not target:
        target = active_session_name
    if not target:
        if config:
            target = list(config.keys())[-1]
            active_session_name = target
        else:
            send_message(chat_id, "No sessions. Run /telegram <name> in Claude Code.")
            return

    # Rate limiting
    now = time.time()
    if target in last_message_time:
        elapsed = now - last_message_time[target]
        if elapsed < RATE_LIMIT_SECONDS:
            send_message(chat_id, f"Rate limited. Wait {RATE_LIMIT_SECONDS - elapsed:.0f}s.")
            return
    last_message_time[target] = now

    # Queue overflow protection
    pending = queue.pending_count(target)
    if pending >= MAX_QUEUE_SIZE:
        send_message(chat_id, f"Queue full for #{target} ({pending} pending). Try later.")
        return

    # Parallel mode: spawn a worktree sub-session for each message
    if target in parallel_sessions:
        task_target = _create_parallel_task(target, config, chat_id)
        if not task_target:
            return  # error already sent
        # Route to the new sub-session instead
        msg_id = queue.enqueue(chat_id, prompt, task_target)
        history.add(task_target, "user", prompt)
        log.info(f"[{task_target}] Parallel task queued: {prompt[:60]}...")
        ensure_worker(task_target)
        return

    # Enqueue the message (serial mode)
    pending = queue.pending_count(target)
    msg_id = queue.enqueue(chat_id, prompt, target)
    history.add(target, "user", prompt)
    log.info(f"[{target}] Queued #{msg_id}: {prompt[:60]}... ({pending} ahead)")

    if pending > 0:
        send_message(chat_id, f"Queued ({pending} ahead)")

    # Ensure worker is running for this session
    ensure_worker(target)


# ── Queue Workers ────────────────────────────────────────────

def session_worker(session_name: str):
    """Process queued messages for a session with streaming and error recovery."""
    log.info(f"[{session_name}] Worker started")
    while True:
        msg = None
        try:
            msg = queue.dequeue(session_name)
            if not msg:
                time.sleep(1)
                msg = queue.dequeue(session_name)
                if not msg:
                    # Final check under lock to prevent race with ensure_worker
                    with worker_lock:
                        msg = queue.dequeue(session_name)
                        if not msg:
                            log.info(f"[{session_name}] Worker idle, stopping")
                            session_workers.pop(session_name, None)
                            return

            chat_id = msg["chat_id"]
            prompt = msg["text"]
            msg_id = msg["id"]

            log.info(f"[{session_name}] Processing #{msg_id}: {prompt[:60]}...")
            send_typing(chat_id)

            session = get_or_create_session(session_name)
            if not session:
                # Try once more — session may have died
                log.warning(f"[{session_name}] Session dead, retrying...")
                active_psmux.pop(session_name, None)
                session = get_or_create_session(session_name)
            if not session:
                queue.fail(msg_id, "Failed to start session")
                send_message(chat_id, f"[{session_name}] Failed to start session.")
                continue

            # Send a "working" message that we'll update with streaming output
            stream_msg_id = send_message(chat_id, f"[{session_name}] Working...")

            # Streaming progress callback
            last_stream_time = [0.0]

            def on_stream(partial_text):
                now = time.time()
                if now - last_stream_time[0] < STREAM_INTERVAL:
                    return
                last_stream_time[0] = now
                preview = partial_text[:MAX_MESSAGE_LENGTH - 50]
                if stream_msg_id:
                    edit_message_text(
                        chat_id, stream_msg_id,
                        f"[{session_name}] ...streaming...\n\n{preview}",
                    )

            on_perm = make_permission_handler(session_name, chat_id)

            session.send_message(prompt)
            response = session.wait_for_response(
                RESPONSE_TIMEOUT, RESPONSE_POLL_INTERVAL,
                on_permission=on_perm,
                on_progress=on_stream,
            )
            if not response or not response.strip():
                response = "(No response captured)"

            queue.complete(msg_id, response)
            history.add(session_name, "assistant", response)
            log.info(f"[{session_name}] #{msg_id} -> {response[:60]}...")

            # Replace the streaming message with the final response
            final_text = f"[{session_name}] {response}"
            if stream_msg_id and len(final_text) <= MAX_MESSAGE_LENGTH:
                edit_message_text(chat_id, stream_msg_id, final_text)
            else:
                # Too long for edit — send as new message(s)
                if stream_msg_id:
                    edit_message_text(chat_id, stream_msg_id,
                                     f"[{session_name}] Done. Full response below.")
                send_message(chat_id, final_text)

        except Exception as e:
            log.error(f"[{session_name}] Worker error: {e}", exc_info=True)
            # Don't let the worker thread die — mark message failed and continue
            try:
                if msg:
                    queue.fail(msg["id"], str(e))
                    send_message(msg["chat_id"],
                                 f"[{session_name}] Error: {e}")
            except Exception:
                pass
            # If session died, clear it so it gets recreated
            active_psmux.pop(session_name, None)
            time.sleep(2)


def ensure_worker(session_name: str):
    """Start a worker thread for a session if one isn't running."""
    with worker_lock:
        if session_name in session_workers and session_workers[session_name].is_alive():
            return
        t = threading.Thread(target=session_worker, args=(session_name,), daemon=True)
        t.start()
        session_workers[session_name] = t


# ── Main Loop ────────────────────────────────────────────────

def main():
    global active_session_name
    if not BOT_TOKEN:
        log.error("TELEGRAM_BOT_TOKEN not set. Exiting.")
        sys.exit(1)
    if not ALLOWED_USER_ID:
        log.error("TELEGRAM_USER_ID not set. Exiting.")
        sys.exit(1)

    log.info("Claude Telegram Bot starting...")

    # Write PID file for watchdog
    pid_file = Path.home() / ".claude" / "telegram-bot.pid"
    pid_file.write_text(str(os.getpid()))

    init_db()
    log.info(f"Mode: {get_mode()}")

    # Crash recovery: requeue messages stuck in 'processing'
    requeued = queue.requeue_stale(STALE_PROCESSING_SECONDS)
    if requeued:
        log.info(f"Recovered {requeued} stale messages from previous crash")

    config = load_sessions_config()
    if config:
        # Set active to first parent session (skip worktree sub-sessions)
        parents = [n for n, i in config.items() if "parent" not in i]
        if parents:
            active_session_name = parents[-1]
        log.info(f"Sessions: {', '.join(config.keys())} (active: {active_session_name})")

        # Resume workers for any pending messages
        pending = queue.pending_all()
        for session_name in pending:
            if session_name in config:
                log.info(f"Resuming worker for {session_name} ({pending[session_name]} pending)")
                ensure_worker(session_name)

    # Send handoff synopsis if switching from desktop
    _send_handoff_synopsis()

    write_health()
    log.info("Polling...")
    offset = None
    health_counter = 0

    while True:
        updates = get_updates(offset)

        for update in updates:
            offset = update["update_id"] + 1

            # Handle callback queries (permission buttons)
            callback = update.get("callback_query")
            if callback:
                user = callback.get("from", {})
                if user.get("id") == ALLOWED_USER_ID:
                    handle_permission_callback(callback)
                else:
                    answer_callback(callback["id"], "Unauthorized.")
                continue

            msg = update.get("message")
            if not msg or "text" not in msg:
                continue

            sender = msg.get("from")
            if not sender or sender.get("id") != ALLOWED_USER_ID:
                send_message(msg["chat"]["id"], "Unauthorized.")
                continue

            text = msg["text"].strip()
            chat_id = msg["chat"]["id"]

            process_message(chat_id, text)

        if not updates:
            time.sleep(2)

        # Write health heartbeat every ~30s (every 10 poll cycles)
        health_counter += 1
        if health_counter >= 10:
            health_counter = 0
            write_health()
            _send_handoff_synopsis()
            queue.cleanup()
            history.cleanup()
            # Prune dead worker thread references
            with worker_lock:
                dead = [n for n, t in session_workers.items() if not t.is_alive()]
                for n in dead:
                    session_workers.pop(n, None)


if __name__ == "__main__":
    main()
