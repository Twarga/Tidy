# TIDY — Full Plan (simple version)

A small desktop app for your laptop that backs up & syncs your Obsidian vaults (and any other folders) to GitHub, automatically — and lets you (and AI agents) control it.

---

## 0. Deliverables (what you get)

| # | Deliverable | Runs on | What it is |
|---|---|---|---|
| 1 | **Desktop app** (`tidy-gui`) | Your laptop (GNOME/Wayland) | Pixel window + tray mini-panel |
| 2 | **CLI + TUI** (`tidy`)| Any machine, **VPS 24/7 headless** | Beautiful terminal UI, command + daemon mode |
| 3 | **One install script** (`install.sh`) | Laptop or VPS | Sets up venv, deps, systemd service — one command |
| 4 | **AppImage** (`tidy-<ver>.AppImage`) | Any Linux desktop | Portable, double-click, no setup |

Everything shares the **same engine** — so you manage the same repos everywhere.

## 1. The 3 ways to control it

| Door | What it looks like | Best for |
|---|---|---|
| 🖥️ Full window | Pixel dashboard (your 5 themes) | Managing repos, schedules, settings |
| 🍞 Tray mini-panel | Right-click the tray icon → tiny control panel | Quick actions without opening the window |
| 🤖 AI agents | MCP server (Claude/Cursor) + CLI (pi) | "Back up my notes now" |

---

## 2. How it thinks (data model)

- **REPO** = a folder + its git remote (e.g. `Twarga-System` → `Twarga/Obsidian_V`)
- **SCHEDULE** = one backup time attached to a repo
- **One repo can have MANY schedules** (08:00, 12:30, 18:00 — same folder)

```
REPO: Twarga-System
  path: /home/twarga/Documents/Twarga-System
  remote: github.com/Twarga/Obsidian_V
  times: 08:00  12:30  18:00     ← you can add more anytime
```

---

## 3. Tray mini-panel (NEW — what you just asked)

The app lives **hidden** in the system tray 24/7.
**Right-click the tray icon** → a small popup panel pops up with quick controls:

```
┌─ ▓ TIDY ──────────────────┐
│  ◉ all synced ✓            │
│                            │
│  ▶ BACKUP ALL NOW          │
│  ▼ PULL ALL                │
│                            │
│  ▸ Twarga-System  ✓  [▶]   │
│  ▸ Academic-Notes  ✓  [▶]  │
│                            │
│  🎨 theme switch (dots)     │
│  ⚙ OPEN WINDOW    ✕ QUIT   │
└────────────────────────────┘
```

- Tiny, stays near the cursor, closes when you click away
- Per-repo quick push buttons right there
- One-click theme dots
- No need to open the big window for simple stuff

---

## 4. Full window features

- **REPOS section** — one card per folder:
  - path + remote shown
  - list of schedule times (✕ removes one, ＋ ADD TIME adds one)
  - ▶ PUSH NOW button per repo + ✓ status (synced / paused / error)
- **＋ ADD REPO** — pick any folder from your **file manager** (native dialog)
- **Settings panel**
  - Theme: your 5 pixel themes, switch live
  - Default backup hour
  - Font size, reduce-motion, tray badge, desktop notifications on/off
- **Activity log** — timestamps, green = ok / red = errors / yellow = warnings
- **Stats strip** — last backup, repos count, total pushes

---

## 5. The sync engine (what actually happens)

At each scheduled time (or when you press Push):
```
1. git fetch          → check remote
2. git pull --rebase  → bring down any edits from other devices
3. git commit         → "backup 2025-08-11 18:00" (only if changes exist)
4. git push           → to GitHub as Twarga
```
- If nothing changed → skip quietly (no spam commits)
- If laptop was asleep at the time → runs the missed job on wake (catch-up)
- Errors → readable message in log, never silent

---

## 6. AI agents (MCP + CLI)

**MCP server** (for Claude Desktop, Cursor, Cline…):

| Tool | Agent can say |
|---|---|
| `list_repos()` | "what's being backed up?" |
| `add_repo(path)` / `remove_repo(path)` | add or stop a folder |
| `add_schedule(repo, time)` | "add a 21:00 backup to my vault" |
| `remove_schedule(repo, time)` | "remove the 12:30 slot" |
| `backup_now(repo)` | "push my notes now" |
| `pull_now(repo)` | "pull my latest notes" |
| `get_status()` / `get_logs(n)` | "is everything ok?" |
| `set_setting(key, value)` | "switch to Game Boy theme" |

**CLI** (for pi + VPS headless) + **TUI**:
```bash
tidy status              # current state (human + --json)
tidy backup all          # push everything now
tidy add ~/Notes --at 18:00
tidy theme neon

tidy serve               # daemon mode → runs 24/7 (for VPS/systemd)
tidy tui                 # interactive full-screen terminal UI
```

## 6b. VPS headless (24/7 on a server)
- `tidy serve` runs an engine daemon without any GUI
- on a VPS: install with `install.sh --server` → installs a **systemd system service** (runs your schemas 24/7, restarts on crash, starts on boot)
- you still control it from the CLI and MCP, or a small `tidy-mcp` service

---

## 7. Runs 24/7 on your laptop

- **systemd user service** → starts when you log in
- Hides to tray (never closes, unless you quit from the menu)
- Auto-restarts if it crashes
- Survives sleep/wake
- Runs as **you** (no root), reuses your existing GitHub login (Twarga)

---

## 8. Where things live

```
~/.config/tidy/config.json   ← all settings (repos, times, theme)
~/tidy/                      ← the app (or /opt/tidy on a VPS / AppImage on desktop)
```

## 8b. Packaging (AppImage + install script)

**`install.sh`** — one command, two modes:
```bash
bash install.sh              # desktop laptop
bash install.sh --server     # headless VPS
```
- creates a Python venv, installs deps (pywebview/FastMCP/APScheduler/rich/textual)
- puts `tidy` + `tidy-gui` in your PATH
- sets up systemd (user service on laptop / system service on VPS)
- registers the MCP server for Claude/Cursor

**AppImage** (`tidy-<version>.AppImage`)
- bundles Python runtime + all deps + the pixel UI (PyInstaller → AppDir → appimagetool)
- double-click to run on any Linux desktop, no install needed

## 8c. One codebase, two faces

```
        tidy (CLI / TUI / `tidy serve` daemon)   ← works anywhere, even no display
                      ▲
              CORE ENGINE (repos, schedules, git, config, MCP)
                      ▼
        tidy-gui (pywebview pixel window + tray mini-panel)
```

---

## 9. Build order (steps I'll do)

1. Packages + pixel fonts (pywebview, FastMCP, APScheduler, rich, textual)
2. Engine: repos, schedules, git sync, config file
3. CLI + TUI (`tidy status/backup/add/serve/tui`) — works headless on a VPS
4. Full window UI (mockups → working buttons) + tray mini-panel
5. Theme switcher (all 5 themes)
6. MCP server + pi skill
7. systemd service → 24/7 autostart (laptop + VPS mode)
8. `install.sh` (one-command setup) + **AppImage** build
9. Final test with you: pick theme, add times, ask pi "back up my notes"

---

## 10. Questions for you (to start)

1. Default theme when it first opens? (Neon / CRT / Game Boy / Watermelon / Paper)
2. Default backup times for your `Twarga-System` repo? (e.g. 18:00)
3. Ready to build? Say GO.
