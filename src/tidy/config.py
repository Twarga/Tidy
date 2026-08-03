"""Configuration manager — load, validate, migrate and save Tidy's config.

Config lives at ``$TIDY_CONFIG_DIR/config.json`` (default ``~/.config/tidy/``).
Writes are atomic (temp file + rename) so a crash never corrupts the file.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

__all__ = [
    "DEFAULT_CONFIG",
    "config_dir",
    "config_path",
    "get_autosync",
    "get_notifications",
    "get_stats",
    "get_theme",
    "load",
    "save",
    "update_stats",
]

CONFIG_VERSION = 1

DEFAULT_CONFIG: dict = {
    "version": CONFIG_VERSION,
    "theme": "neon",
    "autosync": True,
    "notifications": True,
    "repos": [],
    "stats": {"total_pushes": 0, "last_run": None, "last_error": None},
}


def config_dir() -> Path:
    """Directory holding config.json and log.jsonl."""
    env = os.environ.get("TIDY_CONFIG_DIR")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".config" / "tidy"


def config_path() -> Path:
    return config_dir() / "config.json"


def _deep_copy(value: dict) -> dict:
    return json.loads(json.dumps(value))


def _merge(base: dict, override: dict) -> dict:
    """Deep-merge ``override`` onto ``base``, returning a new dict."""
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def load() -> dict:
    """Load config, creating defaults (or healing a corrupt file) if needed."""
    path = config_path()

    if not path.exists():
        cfg = _deep_copy(DEFAULT_CONFIG)
        save(cfg)
        return cfg

    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        # Corrupt config: keep a backup copy, start fresh rather than crash.
        try:
            path.replace(path.with_name(path.name + ".bak"))
        except OSError:
            pass
        cfg = _deep_copy(DEFAULT_CONFIG)
        save(cfg)
        return cfg

    cfg = _merge(DEFAULT_CONFIG, raw)
    cfg["version"] = CONFIG_VERSION
    if not isinstance(cfg.get("repos"), list):
        cfg["repos"] = []
    save(cfg)  # persist any migration
    return cfg


def save(cfg: dict) -> None:
    """Atomically write config to disk."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(cfg, indent=2) + "\n")
    os.replace(tmp, path)


def get_theme(cfg: dict) -> str:
    return cfg.get("theme", DEFAULT_CONFIG["theme"])


def get_autosync(cfg: dict) -> bool:
    return cfg.get("autosync", DEFAULT_CONFIG["autosync"])


def get_notifications(cfg: dict) -> bool:
    return cfg.get("notifications", DEFAULT_CONFIG["notifications"])


def get_stats(cfg: dict) -> dict:
    return cfg.get("stats", DEFAULT_CONFIG["stats"])


def update_stats(cfg: dict, **updates: object) -> None:
    """Update any provided stat and persist. Passing ``last_error=None`` clears it."""
    stats = cfg.setdefault("stats", _deep_copy(DEFAULT_CONFIG["stats"]))
    for key, value in updates.items():
        stats[key] = value
    save(cfg)
