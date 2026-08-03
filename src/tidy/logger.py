"""Logger — append-only JSONL activity log for Tidy."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from tidy.config import config_dir

__all__ = ["get_logs", "log", "log_error", "log_info", "log_warn"]


def log_path() -> Path:
    return config_dir() / "log.jsonl"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def log(level: str, message: str, repo: str | None = None) -> dict:
    """Append one entry to the log file. Never raises on IO errors."""
    entry = {"ts": _now(), "level": level, "message": message, "repo": repo}
    try:
        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as handle:
            handle.write(json.dumps(entry) + "\n")
    except OSError:
        pass
    return entry


def log_info(message: str, repo: str | None = None) -> dict:
    return log("INFO", message, repo)


def log_warn(message: str, repo: str | None = None) -> dict:
    return log("WARN", message, repo)


def log_error(message: str, repo: str | None = None) -> dict:
    return log("ERROR", message, repo)


def get_logs(n: int = 20) -> list[dict]:
    """Return the last ``n`` log entries (oldest first)."""
    path = log_path()
    if not path.exists():
        return []
    entries: list[dict] = []
    try:
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return entries[-n:]
