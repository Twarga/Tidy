"""Git helpers — every git interaction in Tidy goes through here.

Phase 0 provides the availability guard and error type.
Phase 1 adds the safe subprocess runner and the sync primitives.
"""

from __future__ import annotations

import shutil

__all__ = ["GitError", "ensure_git", "git_available"]


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
