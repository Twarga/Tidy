# Changelog

All notable changes to Tidy are tracked here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [v0.1.0] — 2026-08-03

First release. A pixel-styled backup & sync app for any folder/git repo.

### Added

- **Core engine** — atomic JSON config with corruption healing, repo registry
  (auto-init git, remote/branch detection), multi-time schedules per repo
  (dedupe, sorted, enabled/disabled), safe git runner, pull --rebase +
  commit + push sync, JSONL activity log with stats.
- **CLI** — `tidy status|add|remove|schedule|unschedule|backup|pull|theme|logs|serve|tui|gui|mcp`.
- **TUI** — full-screen terminal UI (Textual) with theme cycling.
- **Desktop GUI** — pywebview pixel dashboard (toolbar + repo sidebar + detail
  panel + activity log strip), 5 themes (Neon Grid, CRT Terminal, Game Boy,
  Watermelon, Paper Desk), offline VT323/Press Start 2P fonts, system tray
  mini-panel (pystray xorg backend — no GTK-loop crash), close-to-tray,
  native folder picker.
- **24/7 daemon** — APScheduler jobs per (repo × time), wake catch-up
  (`misfire_grace_time=3600`), single-instance lock, config-watch reload,
  desktop notifications, systemd units (user + system).
- **MCP server** — stdio FastMCP server with 10 tools for Claude Desktop /
  Cursor / Cline, plus a `tidy` skill for pi.
- **Packaging** — one-command `install.sh` (desktop / `--server` VPS /
  `--mcp` register / `--no-service`), portable **AppImage** with bundled
  runtime + web assets + typelibs, GitHub Release.

### Verified

- 76 unit/integration tests, ruff clean.
- Live end-to-end: real vault backup pushed to GitHub as Twarga, GUI + tray
  verified on a real display, MCP driven over real stdio.
