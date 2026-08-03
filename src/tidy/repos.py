"""Repository manager — register folders to be synced.

A repo = a folder + a git remote. A single folder can have many schedules
(managed in :mod:`tidy.schedules`).
"""

from __future__ import annotations

import re
from pathlib import Path

from tidy import git
from tidy.config import save

__all__ = [
    "add_repo",
    "detect_branch",
    "detect_remote",
    "ensure_git_repo",
    "find_repo",
    "is_git_repo",
    "list_repos",
    "remove_repo",
    "slugify",
]


def slugify(path: str | Path) -> str:
    """Turn a folder name into a clean repo id (``My Notes/`` -> ``my-notes``)."""
    name = Path(path).name.strip()
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "repo"


def is_git_repo(path: str | Path) -> bool:
    return (Path(path) / ".git").is_dir()


def ensure_git_repo(path: str | Path) -> None:
    """Make sure ``path`` is a git repository (init on the spot if needed)."""
    folder = Path(path)
    if not folder.is_dir():
        raise ValueError(f"not a directory: {path}")
    if not is_git_repo(path):
        git.run_git(str(folder), "init", "-b", "main")


def detect_remote(path: str | Path) -> str | None:
    """Return the origin remote URL, or None."""
    try:
        return git.run_git(str(path), "config", "--get", "remote.origin.url").stdout.strip() or None
    except git.GitError:
        return None


def detect_branch(path: str | Path) -> str:
    return git.default_branch(str(path))


def _unique_id(cfg: dict, base: str) -> str:
    existing = {repo["id"] for repo in cfg["repos"]}
    candidate, n = base, 2
    while candidate in existing:
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def add_repo(
    cfg: dict,
    path: str | Path,
    remote: str | None = None,
    time: str | None = None,
) -> dict:
    """Register a folder as a Tidy repo. Idempotent for the same path."""
    folder = str(Path(path).expanduser().resolve())
    existing = find_repo(cfg, folder)
    if existing:
        return existing

    ensure_git_repo(folder)
    if remote is None:
        remote = detect_remote(folder)

    repo = {
        "id": _unique_id(cfg, slugify(folder)),
        "path": folder,
        "remote": remote,
        "branch": detect_branch(folder),
        "schedules": [],
    }
    cfg["repos"].append(repo)
    save(cfg)

    if time is not None:
        from tidy.schedules import add_schedule

        add_schedule(cfg, repo["id"], time)
    return repo


def find_repo(cfg: dict, path_or_id: str) -> dict | None:
    """Find a repo by id, exact path, or resolved path."""
    for repo in cfg["repos"]:
        if repo["id"] == path_or_id or repo["path"] == path_or_id:
            return repo
    try:
        resolved = str(Path(path_or_id).expanduser().resolve())
    except OSError:
        return None
    for repo in cfg["repos"]:
        if repo["path"] == resolved:
            return repo
    return None


def remove_repo(cfg: dict, path_or_id: str) -> dict:
    """Remove a repo from config. Does not delete any files."""
    repo = find_repo(cfg, path_or_id)
    if repo is None:
        raise ValueError(f"repo not found: {path_or_id}")
    cfg["repos"] = [r for r in cfg["repos"] if r["id"] != repo["id"]]
    save(cfg)
    return repo


def list_repos(cfg: dict) -> list[dict]:
    return list(cfg["repos"])
