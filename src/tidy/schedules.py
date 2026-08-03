"""Schedule manager — many backup times per repo.

Each repo holds a list of ``{"time": "HH:MM", "enabled": true}`` entries.
"""

from __future__ import annotations

import re

from tidy.config import save
from tidy.repos import find_repo

__all__ = [
    "add_schedule",
    "list_schedules",
    "normalize_time",
    "remove_schedule",
    "set_schedule_enabled",
]

_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def normalize_time(time: object) -> str:
    """Validate and normalize a time string to zero-padded ``HH:MM``."""
    value = str(time).strip()
    match = _TIME_RE.match(value)
    if not match:
        raise ValueError(f"invalid time {time!r} — use HH:MM (24h format)")
    return f"{int(match.group(1)):02d}:{match.group(2)}"


def _require_repo(cfg: dict, repo_id: str) -> dict:
    repo = find_repo(cfg, repo_id)
    if repo is None:
        raise ValueError(f"repo not found: {repo_id}")
    return repo


def add_schedule(cfg: dict, repo_id: str, time: object) -> list[dict]:
    """Attach another backup time to a repo. Deduplicates and sorts by time."""
    repo = _require_repo(cfg, repo_id)
    normalized = normalize_time(time)
    if not any(schedule["time"] == normalized for schedule in repo["schedules"]):
        repo["schedules"].append({"time": normalized, "enabled": True})
        repo["schedules"].sort(key=lambda s: s["time"])
        save(cfg)
    return list(repo["schedules"])


def remove_schedule(cfg: dict, repo_id: str, time: object) -> list[dict]:
    """Remove one backup time from a repo."""
    repo = _require_repo(cfg, repo_id)
    normalized = normalize_time(time)
    before = len(repo["schedules"])
    repo["schedules"] = [s for s in repo["schedules"] if s["time"] != normalized]
    if len(repo["schedules"]) != before:
        save(cfg)
    return list(repo["schedules"])


def list_schedules(cfg: dict, repo_id: str) -> list[dict]:
    return list(_require_repo(cfg, repo_id)["schedules"])


def set_schedule_enabled(cfg: dict, repo_id: str, time: object, enabled: bool) -> list[dict]:
    """Enable or disable a specific schedule time."""
    repo = _require_repo(cfg, repo_id)
    normalized = normalize_time(time)
    for schedule in repo["schedules"]:
        if schedule["time"] == normalized:
            schedule["enabled"] = bool(enabled)
            save(cfg)
            break
    return list(repo["schedules"])
