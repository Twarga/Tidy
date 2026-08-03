"""Git worker — every git interaction in Tidy goes through here.

Safe subprocess runner plus the primitives the sync engine composes:
fetch, pull --rebase, commit, push.
"""

from __future__ import annotations

import shutil
import subprocess

__all__ = [
    "GitError",
    "commit_all",
    "default_branch",
    "ensure_git",
    "fetch",
    "git_available",
    "has_changes",
    "has_commits",
    "has_remote",
    "pull_rebase",
    "push",
    "remote_has_branch",
    "run_git",
]


class GitError(Exception):
    """Raised when a git command fails or git is unavailable."""


def git_available() -> bool:
    """Return True if a `git` executable is on PATH."""
    return shutil.which("git") is not None


def ensure_git() -> None:
    """Raise a clear GitError when git is missing from the system."""
    if not git_available():
        raise GitError(
            "git is not installed or not on PATH. "
            "Install git (e.g. `sudo dnf install git`) and try again."
        )


def run_git(
    repo: str,
    *args: str,
    timeout: int = 120,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a git command inside ``repo``. Raises GitError on failure."""
    ensure_git()
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            text=True,
            check=False,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitError(f"git {' '.join(args)} timed out after {timeout}s") from exc
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise GitError(f"git {' '.join(args)} failed: {detail}")
    return result


def has_remote(repo: str) -> bool:
    try:
        run_git(repo, "remote", "get-url", "origin")
        return True
    except GitError:
        return False


def has_commits(repo: str) -> bool:
    try:
        run_git(repo, "rev-parse", "HEAD")
        return True
    except GitError:
        return False


def default_branch(repo: str) -> str:
    try:
        return run_git(repo, "symbolic-ref", "--short", "HEAD").stdout.strip()
    except GitError:
        return "main"


def remote_has_branch(repo: str, branch: str) -> bool:
    try:
        return bool(run_git(repo, "ls-remote", "--heads", "origin", branch).stdout.strip())
    except GitError:
        return False


def has_changes(repo: str) -> bool:
    """True when the working tree has uncommitted changes."""
    return bool(run_git(repo, "status", "--porcelain").stdout.strip())


def fetch(repo: str) -> None:
    run_git(repo, "fetch", "origin")


def pull_rebase(repo: str, branch: str) -> None:
    run_git(repo, "pull", "--rebase", "origin", branch)


def commit_all(repo: str, message: str) -> bool:
    """Stage and commit everything. Returns False (and changes nothing) if clean."""
    if not has_changes(repo):
        return False
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-m", message)
    return True


def push(repo: str, branch: str) -> None:
    run_git(repo, "push", "origin", branch)
