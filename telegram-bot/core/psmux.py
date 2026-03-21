"""psmux session management for Claude Code instances."""

import json
import re
import subprocess
import time
import uuid
from pathlib import Path
from config import PSMUX, CLAUDE

SIGNAL_DIR = Path.home() / ".claude"

# Patterns that indicate Claude is waiting for permission approval
PERMISSION_PATTERNS = [
    re.compile(r"Allow\s+(Read|Edit|Write|Bash|Glob|Grep|WebFetch|WebSearch|NotebookEdit)\b", re.IGNORECASE),
    re.compile(r"\(y\s*=\s*yes", re.IGNORECASE),
    re.compile(r"Do you want to allow", re.IGNORECASE),
    re.compile(r"Allow tool", re.IGNORECASE),
]

import logging
log = logging.getLogger("psmux")


class PsmuxSession:
    """Manages a Claude Code instance inside a psmux terminal session."""

    def __init__(self, name: str, cwd: str = None):
        self.name = name
        self.cwd = cwd or r"C:\Windows\System32"
        self.signal_file = SIGNAL_DIR / f"tg-signal-{name}.json"
        self._current_nonce = None

    def create(self) -> bool:
        """Create a detached psmux session."""
        r = subprocess.run(
            [PSMUX, "new-session", "-d", "-s", self.name],
            capture_output=True, text=True, timeout=5,
        )
        return r.returncode == 0 or "already exists" in r.stderr

    def launch_claude(self, permission_mode: str = "auto") -> bool:
        """Launch interactive Claude Code inside the psmux session."""
        cmd = f'cd /d "{self.cwd}" && "{CLAUDE}" --permission-mode {permission_mode}'
        self._send_keys(cmd)
        for _ in range(60):
            time.sleep(1)
            output = self.capture() or ""
            if "effort" in output or "───" in output or "\u276f" in output:
                time.sleep(2)
                log.info(f"[{self.name}] Claude Code ready")
                return True
        log.error(f"[{self.name}] Claude Code failed to start in 60s")
        return False

    def send_message(self, text: str) -> None:
        """Send a user message to the Claude session."""
        # Generate unique nonce for this request
        self._current_nonce = uuid.uuid4().hex[:8]
        # Write nonce to signal file — Stop hook echoes it back with the response
        signal = json.dumps({"nonce": self._current_nonce, "status": "waiting"})
        self.signal_file.write_text(signal)
        log.info(f"[{self.name}] Signal file: nonce={self._current_nonce}")
        # Inject the message
        self._send_keys(text)

    def _read_signal_response(self) -> str:
        """Read response from signal file if the Stop hook has written it with matching nonce."""
        if not self.signal_file.exists():
            return ""
        try:
            content = self.signal_file.read_text(encoding="utf-8").strip()
            if not content:
                return ""
            # Try JSON format (nonce protocol)
            try:
                data = json.loads(content)
                if data.get("status") == "waiting":
                    return ""  # Hook hasn't written yet
                if data.get("nonce") != self._current_nonce:
                    log.warning(f"[{self.name}] Nonce mismatch: got {data.get('nonce')}, expected {self._current_nonce}")
                    return ""  # Wrong nonce — stale response
                return data.get("response", "")
            except json.JSONDecodeError:
                # Not JSON — might be raw text from a hook that doesn't use nonce
                return content
        except Exception as e:
            log.error(f"[{self.name}] Signal file read error: {e}")
            return ""

    def wait_for_response(
        self, timeout: int = 120, poll_interval: float = 2.0,
        on_permission=None, on_progress=None,
    ) -> str:
        """Wait for Claude to finish responding via signal file.

        The Stop hook writes last_assistant_message with matching nonce.
        Capture-pane is used ONLY for permission prompt detection.
        """
        start = time.time()
        log.info(f"[{self.name}] Waiting for response (nonce={self._current_nonce}, timeout={timeout}s)")

        while time.time() - start < timeout:
            time.sleep(poll_interval)

            # Check signal file for response with matching nonce
            response = self._read_signal_response()
            if response:
                log.info(f"[{self.name}] Got signal response ({len(response)} chars)")
                # Clear signal file
                try:
                    self.signal_file.unlink()
                except Exception:
                    pass
                return response

            # Check for permission prompt via capture-pane
            if on_permission:
                current = self.capture() or ""
                perm = self.detect_permission_prompt(current)
                if perm:
                    log.info(f"[{self.name}] Permission prompt: {perm.get('tool')}")
                    result = on_permission(perm)
                    if result == "a":
                        self.approve_always()
                    elif result == "n":
                        self.deny_permission()
                    else:
                        self.approve_permission()
                    time.sleep(2)
                    continue

        elapsed = time.time() - start
        log.warning(f"[{self.name}] Response timeout after {elapsed:.0f}s")
        return ""

    def capture(self, lines: int = 100) -> str:
        """Capture current psmux pane content."""
        try:
            r = subprocess.run(
                [PSMUX, "capture-pane", "-t", self.name, "-p", "-S", f"-{lines}"],
                capture_output=True, timeout=5,
            )
            return r.stdout.decode("utf-8", errors="replace")
        except Exception:
            return ""

    def is_alive(self) -> bool:
        """Check if the psmux session exists."""
        try:
            r = subprocess.run(
                [PSMUX, "list-sessions"],
                capture_output=True, text=True, timeout=5,
            )
            return any(
                line.split(":")[0].strip() == self.name
                for line in r.stdout.strip().split("\n") if ":" in line
            )
        except Exception:
            return False

    def kill(self) -> None:
        """Kill the psmux session."""
        subprocess.run(
            [PSMUX, "kill-session", "-t", self.name],
            capture_output=True, timeout=5,
        )

    def _send_keys(self, text: str) -> None:
        """Send keystrokes to the psmux session."""
        subprocess.run(
            [PSMUX, "send-keys", "-t", self.name, "-l", text],
            capture_output=True, timeout=5,
        )
        subprocess.run(
            [PSMUX, "send-keys", "-t", self.name, "Enter"],
            capture_output=True, timeout=5,
        )

    def detect_permission_prompt(self, output: str = None) -> dict | None:
        """Check if Claude is blocked on a permission prompt."""
        if output is None:
            output = self.capture() or ""
        lines = output.strip().split("\n")
        tail = "\n".join(lines[-25:])

        for pattern in PERMISSION_PATTERNS:
            match = pattern.search(tail)
            if match:
                if self._has_prompt(output):
                    last_lines = lines[-3:]
                    for l in last_lines:
                        s = l.strip()
                        if s.startswith(">") or s.startswith("\u276f"):
                            return None
                context_lines = []
                for line in lines[-25:]:
                    stripped = line.strip()
                    if stripped and stripped not in ("", ">"):
                        context_lines.append(stripped)
                tool = match.group(1) if match.lastindex else "Unknown"
                return {
                    "tool": tool,
                    "context": "\n".join(context_lines[-8:]),
                }
        return None

    def _has_prompt(self, output: str) -> bool:
        """Check if Claude's input prompt is visible."""
        lines = output.strip().split("\n")
        for line in lines[-5:]:
            stripped = line.strip()
            if stripped.startswith(">") or "───" in stripped:
                return True
        return False

    def approve_permission(self) -> None:
        self._send_keys("y")

    def deny_permission(self) -> None:
        self._send_keys("n")

    def approve_always(self) -> None:
        self._send_keys("a")


def list_sessions() -> list[dict]:
    """List all psmux sessions."""
    try:
        r = subprocess.run(
            [PSMUX, "list-sessions"],
            capture_output=True, text=True, timeout=5,
        )
        sessions = []
        for line in r.stdout.strip().split("\n"):
            if ":" in line:
                name = line.split(":")[0].strip()
                sessions.append({"name": name, "info": line.strip()})
        return sessions
    except Exception:
        return []
