"""Git worktree operations for parallel Claude sessions."""

import subprocess
from pathlib import Path

WORKTREE_DIR = Path.home() / ".claude" / "worktrees"
BRANCH_PREFIX = "the_box/nferr/"


def _git(repo_path: str, *args, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", repo_path, *args],
        capture_output=True, text=True, timeout=30,
    )


def is_git_repo(path: str) -> bool:
    r = _git(path, "rev-parse", "--is-inside-work-tree")
    return r.returncode == 0 and r.stdout.strip() == "true"


def next_task_number(repo_path: str, session_name: str) -> int:
    """Find the next available task number by scanning existing worktrees."""
    worktrees = list_worktrees(repo_path)
    prefix = f"{session_name}-task-"
    nums = []
    for wt in worktrees:
        branch = wt.get("branch", "")
        if prefix in branch:
            try:
                n = int(branch.rsplit("-", 1)[-1])
                nums.append(n)
            except ValueError:
                pass
    # Also check worktree directories on disk
    if WORKTREE_DIR.exists():
        for d in WORKTREE_DIR.iterdir():
            if d.is_dir() and d.name.startswith(prefix):
                try:
                    n = int(d.name.rsplit("-", 1)[-1])
                    nums.append(n)
                except ValueError:
                    pass
    return max(nums, default=0) + 1


def create_worktree(repo_path: str, task_name: str) -> tuple[bool, str]:
    """Create a worktree with a new branch.

    Returns (success, worktree_path or error message).
    """
    branch = f"{BRANCH_PREFIX}{task_name}"
    wt_path = str(WORKTREE_DIR / task_name)

    WORKTREE_DIR.mkdir(parents=True, exist_ok=True)

    # Fetch latest to branch from a clean base
    _git(repo_path, "fetch", "origin")

    r = _git(repo_path, "worktree", "add", "-b", branch, wt_path)
    if r.returncode != 0:
        # Branch might already exist — try without -b
        r = _git(repo_path, "worktree", "add", wt_path, branch)
        if r.returncode != 0:
            return False, r.stderr.strip()

    return True, wt_path


def list_worktrees(repo_path: str) -> list[dict]:
    """List all worktrees for a repo."""
    r = _git(repo_path, "worktree", "list", "--porcelain")
    if r.returncode != 0:
        return []

    worktrees = []
    current = {}
    for line in r.stdout.split("\n"):
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line[9:]}
        elif line.startswith("HEAD "):
            current["head"] = line[5:]
        elif line.startswith("branch "):
            current["branch"] = line[7:].replace("refs/heads/", "")
        elif line == "bare":
            current["bare"] = True
        elif line == "detached":
            current["detached"] = True
        elif not line.strip() and current:
            worktrees.append(current)
            current = {}
    if current:
        worktrees.append(current)

    return worktrees


def remove_worktree(repo_path: str, worktree_path: str) -> tuple[bool, str]:
    """Remove a worktree (force)."""
    r = _git(repo_path, "worktree", "remove", "--force", worktree_path)
    if r.returncode != 0:
        return False, r.stderr.strip()
    return True, ""


def diff_stat(repo_path: str, branch: str) -> str:
    """Get diff --stat between main and branch."""
    # Try main, then master
    for base in ("main", "master"):
        r = _git(repo_path, "diff", f"{base}...{branch}", "--stat")
        if r.returncode == 0:
            return r.stdout.strip() or "No changes."
    return "Could not diff (no main/master branch found)."


def merge_branch(repo_path: str, branch: str) -> tuple[bool, str]:
    """Merge branch into current branch (should be main)."""
    r = _git(repo_path, "merge", branch, "--no-ff",
             "-m", f"Merge {branch} (parallel task)")
    if r.returncode != 0:
        return False, r.stderr.strip()
    return True, r.stdout.strip()


def delete_branch(repo_path: str, branch: str) -> tuple[bool, str]:
    """Delete a local branch."""
    r = _git(repo_path, "branch", "-D", branch)
    if r.returncode != 0:
        return False, r.stderr.strip()
    return True, ""
