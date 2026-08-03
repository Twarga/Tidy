"""MCP server — exposes Tidy as tools AI agents can drive over stdio.

Run headless on a VPS or laptop (``tidy-mcp`` or ``python -m tidy.mcp``),
then connect Claude Desktop / Cursor / Cline / pi to it. Every tool wraps the
core engine (repos, schedules, sync, config, logger) and returns JSON.

See ``docs/mcp-claude.json`` for a Claude Desktop config sample and
``~/.agents/skills/tidy/SKILL.md`` for the pi skill (CLI-based).
"""

from __future__ import annotations

from fastmcp import FastMCP

from tidy import config, logger, repos, schedules, sync
from tidy.gui.themes import validate_theme

mcp = FastMCP("Tidy")


# ------------------------------------------------------------------ read


@mcp.tool()
def list_repos() -> list[dict]:
    """List all registered repos with their paths, remotes, branches and schedules."""
    return config.load()["repos"]


@mcp.tool()
def get_status() -> dict:
    """High-level summary: repos, schedules, last run, errors and settings."""
    cfg = config.load()
    return {
        "theme": cfg["theme"],
        "autosync": cfg["autosync"],
        "notifications": cfg["notifications"],
        "repos": cfg["repos"],
        "stats": cfg["stats"],
    }


@mcp.tool()
def get_logs(n: int = 20) -> list[dict]:
    """Return the last ``n`` activity-log entries (ts, level, repo, message)."""
    return logger.get_logs(n)


# ------------------------------------------------------------------ repos


@mcp.tool()
def add_repo(path: str, remote: str | None = None, time: str | None = None) -> dict:
    """Register a folder as a Tidy repo. Optionally set a remote URL and/or an initial daily backup time (HH:MM)."""
    try:
        repo = repos.add_repo(config.load(), path, remote=remote, time=time)
        return {"ok": True, "repo": repo}
    except (ValueError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def remove_repo(path_or_id: str) -> dict:
    """Stop syncing a repo (by path or id)."""
    try:
        removed = repos.remove_repo(config.load(), path_or_id)
        return {"ok": True, "id": removed["id"]}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


# --------------------------------------------------------------- schedules


@mcp.tool()
def add_schedule(repo: str, time: str) -> dict:
    """Add a daily backup time (HH:MM) to a repo (by path or id)."""
    try:
        updated = schedules.add_schedule(config.load(), repo, time)
        return {"ok": True, "schedules": updated}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def remove_schedule(repo: str, time: str) -> dict:
    """Remove a daily backup time (HH:MM) from a repo (by path or id)."""
    try:
        updated = schedules.remove_schedule(config.load(), repo, time)
        return {"ok": True, "schedules": updated}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


# ------------------------------------------------------------------- sync


@mcp.tool()
def backup_now(repo: str | None = None) -> dict:
    """Commit + push a repo now (all repos if omitted). Returns per-repo results."""
    cfg = config.load()
    if repo is None:
        return sync.sync_all(cfg)
    found = repos.find_repo(cfg, repo)
    if found is None:
        return {"ok": False, "error": f"repo not found: {repo}", "results": []}
    return {"ok": True, "results": [sync.sync_repo(cfg, found)]}


@mcp.tool()
def pull_now(repo: str | None = None) -> dict:
    """Pull remote changes into a repo (all repos if omitted). No push."""
    cfg = config.load()
    if repo is None:
        return sync.pull_all(cfg)
    found = repos.find_repo(cfg, repo)
    if found is None:
        return {"ok": False, "error": f"repo not found: {repo}", "results": []}
    return {"ok": True, "results": [sync.pull_repo(cfg, found)]}


# --------------------------------------------------------------- settings


@mcp.tool()
def set_setting(key: str, value: str | bool) -> dict:
    """Set a UI setting. Keys: theme (neon/crt/gameboy/watermelon/paper), autosync, notifications."""
    if key not in {"theme", "autosync", "notifications"}:
        return {"ok": False, "error": f"unknown setting: {key}"}
    if key == "theme" and not validate_theme(str(value)):
        return {"ok": False, "error": f"unknown theme: {value}"}
    cfg = config.load()
    if key == "theme":
        cfg["theme"] = str(value)
    else:
        cfg[key] = bool(value)
    config.save(cfg)
    return {"ok": True, "key": key, "value": cfg[key]}


def main() -> None:
    """Run the MCP server over stdio (blocking)."""
    mcp.run()


if __name__ == "__main__":
    main()
