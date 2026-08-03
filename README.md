<p align="center">
  <img src="https://img.shields.io/badge/TIDY-v0.1.0-8ef0c4?style=for-the-badge" alt="Tidy">
  <img src="https://img.shields.io/badge/Python-3.11%2B-57e39a?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-7d8dff?style=for-the-badge" alt="License">
</p>

<h1 align="center">🕹️ TIDY</h1>

<p align="center">
  <b>Keep your folders tidy.</b><br>
  A pixel-styled backup &amp; sync app for <i>any</i> folder or git repository —
  desktop GUI, headless CLI/TUI, and MCP for AI agents.
</p>

<p align="center">
  <a href="#✨-features">Features</a> ·
  <a href="#🚀-quickstart">Quickstart</a> ·
  <a href="#🖥️-cli--tui">CLI</a> ·
  <a href="#🤖-mcp-for-ai-agents">MCP</a> ·
  <a href="#🎨-themes">Themes</a> ·
  <a href="#🛠️-development">Development</a>
</p>

---

## ✨ Features

- 📁 **Any folder, any repo** — not locked to one tool. Point Tidy at a folder + a git remote and it handles the rest.
- ⏰ **Per-repo schedules, many times** — one folder can back up at `08:00`, `12:30`, `18:00` — add as many as you like.
- 🔄 **True two-way sync** — `fetch → pull --rebase → commit → push`. Edits from other devices merge cleanly.
- 🍞 **Tray mini-panel** — right-click the tray icon for a tiny control panel. No window needed for quick actions.
- 🎨 **5 pixel themes** — Neon Grid, CRT Terminal, Game Boy, Watermelon, Paper Desk. Switch live.
- 🖥️ **Desktop app + headless CLI/TUI** — same engine, two faces. Runs 24/7 on your laptop *or* a VPS.
- 🤖 **MCP server + CLI** — Claude, Cursor, Cline, and pi can control Tidy with natural language.
- 📦 **One install script + AppImage** — `install.sh` (laptop or `--server` VPS mode) and a portable AppImage.

---

## 🚀 Quickstart

### Desktop (laptop)
```bash
bash install.sh
tidy-gui
```

### Headless (VPS, 24/7)
```bash
bash install.sh --server
tidy add /srv/notes --at 18:00
systemctl --user enable --now tidy
```

### AppImage
Download `tidy-<version>.AppImage`, make it executable, double-click:

```bash
chmod +x tidy-0.1.0.AppImage
./tidy-0.1.0.AppImage
```

---

## 🖥️ CLI & TUI

```bash
tidy status              # state of all repos (human + --json)
tidy add ~/Notes --at 18:00      # register a folder + schedule
tidy remove ~/Notes
tidy schedule ~/Notes --at 21:00 # add another time to a repo
tidy backup all          # push everything now
tidy pull ~/Notes
tidy serve               # daemon mode → 24/7 engine, no GUI
tidy tui                 # interactive full-screen terminal UI
tidy gui                 # desktop pixel GUI (window + system tray mini-panel)
tidy-gui                 # same as `tidy gui` (direct entry point)
```

### 🖥️ Desktop GUI (Phase 5)

`tidy gui` (or `tidy-gui`) opens a pywebview window with the pixel dashboard:

- **Repo cards** — path, remote status, schedule chips (click ✕ to remove, ＋ ADD TIME for another slot)
- **Actions** — BACKUP + PUSH ALL, PULL ALL, per-repo ▶ PUSH, ＋ ADD REPO (native folder dialog)
- **Theme switcher** — live pixel theme dots (Neon Grid, CRT Terminal, Game Boy, Watermelon, Paper Desk)
- **Activity log** — live tail of the JSONL log (polls every 4s)
- **System tray** — right-click mini-panel: status line, per-repo push, backup/pull all, theme menu, show window, quit

The tray is skipped automatically when no display is available (headless VPS).

---

## 🤖 MCP for AI agents

Tidy exposes an [MCP](https://modelcontextprotocol.io) server so AI agents can control backups:

| Tool | Example |
|---|---|
| `list_repos()` | "what's being backed up?" |
| `add_repo(path)` | "watch my notes folder" |
| `add_schedule(repo, time)` | "add a 21:00 backup to my vault" |
| `backup_now(repo)` | "push my notes now" |
| `pull_now(repo)` | "pull my latest notes" |
| `get_status()` / `get_logs(n)` | "is everything ok?" |
| `set_setting(key, value)` | "switch to the Game Boy theme" |

Register it with Claude Desktop:

```json
{
  "mcpServers": {
    "tidy": { "command": "tidy-mcp", "args": [] }
  }
}
```

---

## 🎨 Themes

Five built-in pixel themes, switchable live from the GUI, CLI, or MCP:

| Theme | Vibe |
|---|---|
| 🌃 **Neon Grid** | Synthwave — purple, pink & cyan |
| 🖥️ **CRT Terminal** | Classic green phosphor + scanlines |
| 🎮 **Game Boy** | Grey handheld, retro LCD green |
| 🍉 **Watermelon** | Fresh pink & green, seeded strip |
| 📄 **Paper Desk** | Clean paper & ink, desk binder |

Design mockups live in [`designs/`](designs/).

---

## 🛠️ Development

```bash
git clone https://github.com/Twarga/Tidy
cd Tidy
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
tidy status
```

This repo ships a [devcontainer](.devcontainer/devcontainer.json) — open it in **GitHub Codespaces** or VS Code for a secure, configured development environment with everything preinstalled.

### Structure
```
Tidy/
├── src/tidy/          # the engine + CLI + GUI + MCP
├── designs/           # 5 pixel theme mockups
├── install.sh         # one-command setup (laptop / --server)
├── pyproject.toml     # package metadata (tidy, tidy-gui, tidy-mcp)
└── .devcontainer/     # Codespaces dev environment
```

---

## 📄 License

[MIT](LICENSE) © 2025 Twarga
