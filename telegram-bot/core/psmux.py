"""psmux session management for Claude Code instances."""

import os
import re
import subprocess
import time
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


class PsmuxSession:
    """Manages a Claude Code instance inside a psmux terminal session."""

    def __init__(self, name: str, cwd: str = None):
        self.name = name
        self.cwd = cwd or r"C:\Windows\System32"
        self.signal_file = SIGNAL_DIR / f"tg-signal-{name}.json"
        self._last_capture = ""
        self._last_prompt_line = 0

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
        # Wait for Claude Code to start (look for Claude-specific indicators)
        for _ in range(60):
            time.sleep(1)
            output = self.capture() or ""
            # Claude Code shows these when ready — cmd prompt ">" is NOT sufficient
            if "effort" in output or "───" in output or "\u276f" in output:
                time.sleep(2)  # Let UI fully render before first capture
                return True
        return False

    def send_message(self, text: str) -> None:
        """Send a user message to the Claude session."""
        # Write marker to signal file — the Stop hook only writes if marker present
        self.signal_file.write_text("WAITING")
        # Capture current state for permission prompt detection
        self._last_capture = self.capture() or ""
        # Inject the message
        self._send_keys(text)

    def _read_signal_file(self) -> str:
        """Read response from signal file if the Stop hook has written it."""
        if not self.signal_file.exists():
            return ""
        try:
            content = self.signal_file.read_text(encoding="utf-8").strip()
            # "WAITING" means the hook hasn't written yet
            if not content or content == "WAITING":
                return ""
            return content
        except Exception:
            return ""

    def wait_for_response(
        self, timeout: int = 120, poll_interval: float = 2.0,
        on_permission=None, on_progress=None,
    ) -> str:
        """Wait for Claude to finish responding via signal file.

        The Stop hook writes last_assistant_message to the signal file.
        Capture-pane is used ONLY for permission prompt detection.

        Args:
            on_permission: Optional callback(details: dict) -> str.
                Called when a permission prompt is detected.
                Should return "y", "n", or "a" (approve always).
                If None, permission prompts are ignored.
            on_progress: Optional callback(partial_text: str) -> None.
                Not used (kept for API compatibility).
        """
        start = time.time()

        while time.time() - start < timeout:
            time.sleep(poll_interval)

            # Check signal file — Stop hook writes clean response here
            signal_response = self._read_signal_file()
            if signal_response:
                self.signal_file.write_text("")
                return signal_response

            # Check for permission prompt via capture-pane
            if on_permission:
                current = self.capture() or ""
                perm = self.detect_permission_prompt(current)
                if perm:
                    response = on_permission(perm)
                    if response == "a":
                        self.approve_always()
                    elif response == "n":
                        self.deny_permission()
                    else:
                        self.approve_permission()
                    time.sleep(2)
                    continue

        return ""

    def capture(self, lines: int = 100) -> str:
        """Capture current psmux pane content."""
        try:
            r = subprocess.run(
                [PSMUX, "capture-pane", "-t", self.name, "-p", "-S", f"-{lines}"],
                capture_output=True, timeout=5,
            )
            # Decode with utf-8, fallback to latin-1 to handle Claude's unicode output
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
        # Use -l for literal text (prevents "Enter", "Escape", "C-c" interpretation)
        subprocess.run(
            [PSMUX, "send-keys", "-t", self.name, "-l", text],
            capture_output=True, timeout=5,
        )
        # Send Enter separately as a key (not literal)
        subprocess.run(
            [PSMUX, "send-keys", "-t", self.name, "Enter"],
            capture_output=True, timeout=5,
        )

    def _has_prompt(self, output: str) -> bool:
        """Check if Claude's input prompt is visible (Claude is waiting for input)."""
        lines = output.strip().split("\n")
        # Look for the prompt indicator in the last few lines
        for line in lines[-5:]:
            stripped = line.strip()
            # Claude Code shows a > prompt or the ─── divider when ready
            if stripped.startswith(">") or "───" in stripped:
                return True
        return False

    def _extract_response(self, before: str, after: str) -> str:
        """Extract Claude's response by diffing before and after captures."""
        # Primary strategy: find Claude's response markers (bullet points)
        response = self._extract_by_markers(after)
        if response and len(response) >= 5:
            return response

        # Fallback: diff-based extraction
        before_lines = set(before.strip().split("\n"))
        after_lines = after.strip().split("\n")

        new_lines = []
        for line in after_lines:
            if line not in before_lines:
                stripped = line.strip()
                if self._is_chrome(stripped):
                    continue
                if stripped:
                    new_lines.append(stripped)

        while new_lines and not new_lines[0]:
            new_lines.pop(0)
        while new_lines and not new_lines[-1]:
            new_lines.pop()

        return "\n".join(new_lines)

    def _is_chrome(self, line: str) -> bool:
        """Check if a line is UI chrome (not actual response content)."""
        if not line:
            return True
        # Prompt lines
        if line.startswith(">") or line.startswith("\u276f"):
            return True
        # Dividers
        if "───" in line or "╭" in line or "╰" in line or "│" in line:
            return True
        # Status/spinners
        if line.startswith("\u273d") or line.startswith("\u2718"):  # ✽ ✘
            return True
        if "thinking" in line.lower() or "running" in line.lower():
            return True
        if "ctrl+" in line.lower() or "Press up" in line:
            return True
        if line.startswith("Opus"):
            return True
        if "effort" in line and "/" in line:
            return True
        # Tool use notifications
        if ("Recalled" in line or "Wrote" in line) and "memory" in line:
            return True
        return False

    def detect_permission_prompt(self, output: str = None) -> dict | None:
        """Check if Claude is blocked on a permission prompt.
        Returns {"tool": str, "context": str} if found, None otherwise.
        """
        if output is None:
            output = self.capture() or ""
        lines = output.strip().split("\n")
        tail = "\n".join(lines[-25:])

        for pattern in PERMISSION_PATTERNS:
            match = pattern.search(tail)
            if match:
                # Don't trigger if the normal input prompt is also present
                # (means Claude already moved past the permission)
                if self._has_prompt(output):
                    last_lines = lines[-3:]
                    # If prompt is in the very last lines, Claude is done
                    for l in last_lines:
                        s = l.strip()
                        if s.startswith(">") or (s.startswith("\u276f")):
                            return None

                # Extract context: tool box content
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

    def approve_permission(self) -> None:
        """Send 'y' to approve a permission prompt."""
        self._send_keys("y")

    def deny_permission(self) -> None:
        """Send 'n' to deny a permission prompt."""
        self._send_keys("n")

    def approve_always(self) -> None:
        """Send 'a' to approve always for this session."""
        self._send_keys("a")

    def _extract_by_markers(self, output: str) -> str:
        """Extract response between Claude's bullet markers and the next prompt."""
        lines = output.strip().split("\n")
        response_lines = []
        in_response = False

        for line in lines:
            stripped = line.strip()

            # Claude responses start with bullet ● or bold text
            if stripped.startswith("\u25cf"):  # ●
                in_response = True
                cleaned = re.sub(r'^[\u25cf\u2022*]\s*', '', stripped)
                if cleaned:
                    response_lines.append(cleaned)
                continue

            if in_response:
                # Stop at next prompt or divider
                if stripped.startswith("\u276f") or stripped.startswith(">"):
                    break
                if "───" in stripped:
                    break
                if self._is_chrome(stripped):
                    continue
                if stripped:
                    response_lines.append(stripped)

        return "\n".join(response_lines)


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
