# TIDY — Implementation Plan (tasks.md)

> **Goal:** Ship Tidy v0.1.0 — pixel backup & sync for any folder.
> **Deliverables:** Desktop GUI · Headless CLI/TUI · MCP server · install.sh · AppImage · 24/7 via systemd.
> **Identity:** all commits as `Twarga <twarga.touzani.05@gmail.com>`.
> **Repo:** `github.com/Twarga/Tidy` · **Local:** `~/Documents/Tidy`

---

## Architecture (one engine, two faces)

```
        tidy serve (daemon) / tidy CLI / tidy tui      ← headless, works on VPS
                       ▲
        CORE ENGINE (config · repos · schedules · git · logs)
                       ▼
        tidy-gui (pywebview pixel window + tray mini-panel)
                       ▼
        tidy-mcp (FastMCP server → Claude/Cursor/Cline/pi)
```

**Data model**
```
Config  ~/.config/tidy/config.json
  └─ theme            str          (neon|crt|gameboy|watermelon|paper)
  └─ autosync         bool
  └─ notifications    bool
  └─ repos[]          (many)
      └─ id           str          (slug, e.g. "twarga-system")
      └─ path         str          (absolute folder path)
      └─ remote       str          (git remote URL)
      └─ schedules[]  (many times per repo)
          └─ time     "HH:MM"
          └─ enabled  bool
  └─ stats            last_run, total_pushes, last_error
```

---

## PHASE 0 — Foundation ⚙️

| ID | Task | Details | Files | Done |
|---|---|---|---|---|
| 0.1 | ✅ Package skeleton | Confirm `src/tidy/` layout, `pyproject.toml` entry points (`tidy`, `tidy-gui`, `tidy-mcp`) | `src/tidy/*` | ✅ |
| 0.2 | ✅ Repo + GitHub | Repo created, README, LICENSE, .gitignore, devcontainer, tags | `./*` | ✅ |
| 0.3 | Dev environment | `python -m venv .venv` in `~/Documents/Tidy`; install `[dev]` extras | `.venv/` | ✅ |
| 0.4 | Version constant | `__version__` in `src/tidy/__init__.py`, imported everywhere (never hardcoded) | `src/tidy/__init__.py` | ✅ |
| 0.5 | Exit early on git absence | Helper that raises clear error if `git` not on PATH | `src/tidy/git.py` | ✅ |

**Phase 0 exit criteria:** `pip install -e .` works; `tidy --version` prints `0.1.0`.

---

## PHASE 1 — Core Engine 🧠

### 1.1 Config manager
| ID | Task | Details | Files |
|---|---|---|---|
| 1.1.1 | Load/save JSON | `load()` / `save()` with atomic write (write temp + rename), default schema if missing | `src/tidy/config.py` |
| 1.1.2 | Path resolution | Config dir = `$TIDY_CONFIG_DIR` or `~/.config/tidy/` | `src/tidy/config.py` |
| 1.1.3 | Schema validation | Validate types on load; migrate v0→v1 if schema changes | `src/tidy/config.py` |
| 1.1.4 | Settings getters | `get_theme()`, `get_autosync()`, `get_repos()`, … | `src/tidy/config.py` |

### 1.2 Repo manager
| ID | Task | Details | Files |
|---|---|---|---|
| 1.2.1 | Add repo | `add_repo(path, remote=None)` — auto-detect remote via `git config --get remote.origin.url`, create slug id, save | `src/tidy/repos.py` |
| 1.2.2 | Remove repo | `remove_repo(id_or_path)` — no files deleted, just config | `src/tidy/repos.py` |
| 1.2.3 | List repos | `list_repos()` → list of dicts (id, path, remote, schedules, status) | `src/tidy/repos.py` |
| 1.2.4 | Validate folder | `is_git_repo(path)` — has `.git/`; warn + auto-`git init` if not | `src/tidy/repos.py` |

### 1.3 Schedule manager
| ID | Task | Details | Files |
|---|---|---|---|
| 1.3.1 | Add schedule | `add_schedule(repo_id, time)` — validate `HH:MM`, dedupe, sort | `src/tidy/schedules.py` |
| 1.3.2 | Remove schedule | `remove_schedule(repo_id, time)` | `src/tidy/schedules.py` |
| 1.3.3 | List schedules | per-repo list, enabled flag | `src/tidy/schedules.py` |
| 1.3.4 | Enable/disable | `set_schedule_enabled(repo_id, time, bool)` | `src/tidy/schedules.py` |

### 1.4 Git worker (the heart)
| ID | Task | Details | Files |
|---|---|---|---|
| 1.4.1 | Safe git runner | `run_git(repo, *args, timeout=120)` → subprocess, capture stdout/stderr, raise `GitError` on non-zero | `src/tidy/git.py` |
| 1.4.2 | `fetch` | `git fetch origin` — return False if no remote | `src/tidy/git.py` |
| 1.4.3 | `pull --rebase` | `git pull --rebase origin <branch>` with conflict detection | `src/tidy/git.py` |
| 1.4.4 | Auto-commit | `git add -A` + commit only **if** `git status --porcelain` non-empty; message `backup YYYY-MM-DD HH:MM` | `src/tidy/git.py` |
| 1.4.5 | `push` | `git push origin <branch>` | `src/tidy/git.py` |
| 1.4.6 | Branch detection | default branch from `git symbolic-ref` (main/master) | `src/tidy/git.py` |
| 1.4.7 | **Full sync** | `sync_repo(repo)` = fetch → pull --rebase → commit → push; returns result dict `{ok, message, commits, elapsed}` | `src/tidy/sync.py` |
| 1.4.8 | Conflict resolution | On rebase conflict → abort, leave local safe, report error (never destroy data) | `src/tidy/sync.py` |
| 1.4.9 | Skip-if-clean | No changes → `{ok: True, skipped: True}` (no spam commits) | `src/tidy/sync.py` |

### 1.5 Logger
| ID | Task | Details | Files |
|---|---|---|---|
| 1.5.1 | File log | append `~/.config/tidy/log.jsonl` — `{ts, level, repo, message}` | `src/tidy/logger.py` |
| 1.5.2 | Recent log | `get_logs(n)` returns last n entries | `src/tidy/logger.py` |
| 1.5.3 | Stats update | bump `total_pushes`, `last_run`, clear `last_error` on success | `src/tidy/config.py` |

**Phase 1 exit criteria:** Python REPL can `add_repo(Twarga-System)`, run a real `sync_repo` → pushes to GitHub as Twarga, logs everything, and a second run with no changes skips.

---

## PHASE 2 — CLI ⌨️

### 2.1 Command surface
| ID | Task | Command | Files |
|---|---|---|---|
| 2.1.1 | argparse entry | `tidy` root + subcommands | `src/tidy/cli.py` |
| 2.1.2 | `tidy status` | table of repos: id, path, schedules, last status (`--json` for machines) | `src/tidy/cli.py` |
| 2.1.3 | `tidy add PATH [--at HH:MM] [--remote URL]` | registers repo + first schedule | `src/tidy/cli.py` |
| 2.1.4 | `tidy remove PATH` | remove repo | `src/tidy/cli.py` |
| 2.1.5 | `tidy schedule PATH --at HH:MM` | add another time to a repo | `src/tidy/cli.py` |
| 2.1.6 | `tidy unschedule PATH --at HH:MM` | remove one time | `src/tidy/cli.py` |
| 2.1.7 | `tidy backup [PATH\|all]` | run sync now (all repos or one) | `src/tidy/cli.py` |
| 2.1.8 | `tidy pull [PATH\|all]` | pull-only pass | `src/tidy/cli.py` |
| 2.1.9 | `tidy theme NAME` | set theme | `src/tidy/cli.py` |
| 2.1.10 | `tidy logs [-n 20]` | show recent log | `src/tidy/cli.py` |
| 2.1.11 | `tidy serve` | daemon (Phase 4) | `src/tidy/cli.py` |
| 2.1.12 | `tidy tui` | launch TUI (Phase 3) | `src/tidy/cli.py` |

### 2.2 Rich output
| ID | Task | Details | Files |
|---|---|---|---|
| 2.2.1 | Tables/panels | `rich.Table` for status, `rich.Panel` for results, colored ok/fail | `src/tidy/ui.py` |
| 2.2.2 | Spinner on sync | `rich.Progress` while pushing | `src/tidy/ui.py` |
| 2.2.3 | Exit codes | 0 ok · 1 error · 2 usage · 3 sync conflict | `src/tidy/cli.py` |

**Phase 2 exit criteria:** every command works headless; `tidy status --json` is valid JSON; `tidy backup all` pushes both a dirty and a clean repo correctly.

---

## PHASE 3 — TUI 🖥️ (textual)

| ID | Task | Details | Files |
|---|---|---|---|
| 3.1 | App shell | `TextualApp` — header, repo list, log panel, footer keymap | `src/tidy/tui/app.py` |
| 3.2 | Repo list view | per-repo row: name, schedules, status color | `src/tidy/tui/views.py` |
| 3.3 | Actions | key `b` = backup all, `p` = pull, `r` = refresh, `q` = quit | `src/tidy/tui/app.py` |
| 3.4 | Log panel | live tail of `log.jsonl` | `src/tidy/tui/views.py` |
| 3.5 | Worker thread | sync runs in background thread → updates UI via message bus | `src/tidy/tui/worker.py` |
| 3.6 | Theme accents | terminal-safe color mapping for the 5 themes | `src/tidy/tui/themes.py` |

**Phase 3 exit criteria:** `tidy tui` opens full-screen; pressing `b` syncs all repos; log updates live.

---

## PHASE 4 — Daemon + 24/7 ⏰

| ID | Task | Details | Files |
|---|---|---|---|
| 4.1 | Scheduler init | APScheduler `BlockingScheduler` loading all repo schedules from config | `src/tidy/scheduler.py` |
| 4.2 | Job per time | Cron trigger `HH:MM` → `sync_repo(repo)`; dedupe same-time jobs | `src/tidy/scheduler.py` |
| 4.3 | Catch-up on wake | `misfire_grace_time=3600` → missed slot runs after sleep/wake | `src/tidy/scheduler.py` |
| 4.4 | `serve` mode | `tidy serve` = scheduler + signal handling (SIGINT/SIGTERM clean stop) | `src/tidy/daemon.py` |
| 4.5 | Lock file | single instance via `fcntl` lock on `~/.config/tidy/tidy.lock` | `src/tidy/daemon.py` |
| 4.6 | systemd user unit | `~/.config/systemd/user/tidy.service` (laptop) | `packaging/tidy.service` |
| 4.7 | systemd system unit | `tidy.service` for VPS (`install.sh --server`) | `packaging/tidy.service` |
| 4.8 | Notification hook | on push ok/fail → `notify-send` (desktop) / syslog (VPS), off if disabled | `src/tidy/notify.py` |

**Phase 4 exit criteria:** `tidy serve` runs 2 repos on different times; editing config adds a job without restart (or documented restart); process survives wake from sleep; `systemctl --user status tidy` green.

---

## PHASE 5 — Desktop GUI 🎮

### 5.1 pywebview shell
| ID | Task | Details | Files |
|---|---|---|---|
| ✅ 5.1.1 | Window | `webview.create_window("Tidy", url=local assets, js_api=Api())` | `src/tidy/gui/main.py` |
| ✅ 5.1.2 | JS ⇄ Python bridge | `Api` class methods callable from JS (`backup_all`, `list_repos`, …) | `src/tidy/gui/api.py` |
| ✅ 5.1.3 | Assets | `web/` folder: index.html + theme CSS + JS, fonts bundled locally (offline) | `src/tidy/gui/web/` |
| ✅ 5.1.4 | Ports/conflicts | run on fixed local port if `server=True`, else file:// | `src/tidy/gui/main.py` |

### 5.2 UI from mockups
| ID | Task | Details | Files |
|---|---|---|---|
| ✅ 5.2.1 | Base layout | header, status banner, stats, repos cards, actions, log (from `designs/mockup.html`) | `src/tidy/gui/web/index.html` |
| ✅ 5.2.2 | Repo card | path, remote, schedule time chips (✕ remove, ＋ ADD TIME), ▶ PUSH NOW, status dot | `src/tidy/gui/web/index.html` |
| ✅ 5.2.3 | Add repo | native folder dialog (`tkinter`/`zenity` fallback → or webkit file input) | `src/tidy/gui/api.py` |
| ✅ 5.2.4 | Log panel | live entries pushed from Python via JS callback | `src/tidy/gui/web/index.html` |
| ✅ 5.2.5 | Stats strip | last backup, repo count, total pushes | `src/tidy/gui/web/index.html` |
| ✅ 5.2.6 | Tray icon | `pystray` + `Pillow` icon; click = open window, right-click = menu | `src/tidy/gui/tray.py` |
| ✅ 5.2.7 | **Tray mini-panel** | right-click popup: status · BACKUP ALL · PULL ALL · per-repo ▶ · theme dots · OPEN WINDOW · QUIT | `src/tidy/gui/tray.py` |
| ✅ 5.2.8 | Notifications | desktop notify on success/failure (config-gated) | `src/tidy/notify.py` |

### 5.3 Themes
| ID | Task | Details | Files |
|---|---|---|---|
| ✅ 5.3.1 | Theme registry | `THEMES = {neon, crt, gameboy, watermelon, paper}` with CSS vars | `src/tidy/gui/themes.py` |
| ✅ 5.3.2 | Live switcher | JS sets `data-theme` on `<html>`; persisted via `set_setting("theme", …)` | `src/tidy/gui/web/index.html` |
| ✅ 5.3.3 | Fonts offline | bundle VT323 + Press Start 2P as `.woff2` in `web/assets/fonts/` | `src/tidy/gui/web/assets/fonts/` |

**Phase 5 exit criteria:** GUI opens with chosen default theme; add repo via file dialog; PUSH NOW works; tray right-click mini-panel controls backup + theme; closing window hides to tray (app alive) — Quit/SIGTERM do a real shutdown.

---

## PHASE 6 — MCP + pi integration 🤖

| ID | Task | Details | Files |
|---|---|---|---|
| ✅ 6.1 | MCP server | FastMCP app exposing tools below; stdio transport | `src/tidy/mcp.py` |
| ✅ 6.2 | `list_repos` | → repos + schedules + status | `src/tidy/mcp.py` |
| ✅ 6.3 | `add_repo(path, remote?)` | → added repo | `src/tidy/mcp.py` |
| ✅ 6.4 | `remove_repo(path)` | → removed | `src/tidy/mcp.py` |
| ✅ 6.5 | `add_schedule(repo, time)` | → updated schedule list | `src/tidy/mcp.py` |
| ✅ 6.6 | `remove_schedule(repo, time)` | → updated schedule list | `src/tidy/mcp.py` |
| ✅ 6.7 | `backup_now(repo?)` | → run sync, return result (all if omitted) | `src/tidy/mcp.py` |
| ✅ 6.8 | `pull_now(repo?)` | → pull result | `src/tidy/mcp.py` |
| ✅ 6.9 | `get_status()` | → summary | `src/tidy/mcp.py` |
| ✅ 6.10 | `get_logs(n=20)` | → recent entries | `src/tidy/mcp.py` |
| ✅ 6.11 | `set_setting(key, value)` | theme/autosync/notifications | `src/tidy/mcp.py` |
| ✅ 6.12 | MCP config sample | `docs/mcp-claude.json` for Claude Desktop + Cursor instructions | `docs/` |
| ✅ 6.13 | pi skill | SKILL.md that tells pi to use `tidy` CLI commands | `~/.agents/skills/tidy/` |

**Phase 6 exit criteria:** Claude Desktop can add a schedule and push; `pi` can run `tidy backup all` via the skill.

---

## PHASE 7 — Packaging 📦

| ID | Task | Details | Files |
|---|---|---|---|
| 7.1 | `install.sh` polish | tested both modes; idempotent (re-run safe) | `install.sh` |
| 7.2 | MCP auto-register | install.sh optionally writes Claude Desktop config | `install.sh` |
| 7.3 | AppImage build script | PyInstaller → AppDir → `appimagetool` → `tidy-0.1.0-x86_64.AppImage` | `packaging/build-appimage.sh` |
| 7.4 | AppImage runtime | bundle python runtime + pywebview + fonts; verify runs on fresh Fedora/Ubuntu | `packaging/` |
| 7.5 | Release | GitHub Release v0.1.0 with AppImage + install.sh + changelog | GitHub |

**Phase 7 exit criteria:** clean VM install with `install.sh` (desktop & --server) works; AppImage launches on another machine.

---

## PHASE 8 — QA, Docs, Release 🧪

| ID | Task | Details | Files |
|---|---|---|---|
| 8.1 | Unit tests | config (load/save/migrate), schedules (add/dup/remove), logger | `tests/test_config.py` etc. |
| 8.2 | Integration tests | fake git repo fixture → sync commits/pushes/skips | `tests/test_sync.py` |
| 8.3 | CLI golden tests | `tidy status --json` schema | `tests/test_cli.py` |
| 8.4 | Manual test sheet | checklist: theme switch, tray panel, sleep catch-up, conflict | `docs/MANUAL_TEST.md` |
| 8.5 | Docs | README polish, CONTRIBUTING.md, docs/CLI.md, docs/MCP.md | `docs/` |
| 8.6 | Ruff + format | `ruff check` clean, `ruff format` | — |
| 8.7 | Final demo | run `tidy tui`, `tidy-gui`, `tidy-mcp` with real Twarga-System repo | — |

**Phase 8 exit criteria:** all tests green, ruff clean, release tag pushed.

---

## Dependencies & sequencing

```
Phase 0 → Phase 1 → Phase 2 ─┬→ Phase 3 (needs 1,2)
                             ├→ Phase 4 (needs 1,2)
                             └→ Phase 5 (needs 1,2) → Phase 6 (needs 1,4)
                                            └→ Phase 7 (needs 5) → Phase 8 (all)
```

## Risk register
| Risk | Mitigation |
|---|---|
| Push conflicts with remote edits | `pull --rebase` before commit; abort + report on conflict |
| Laptop asleep at schedule time | `misfire_grace_time` catch-up |
| pywebview font/theme drift | bundle fonts locally; test in webkit |
| AppImage webkit dependency | document webkit2gtk requirement; test on clean box |
| Config corruption | atomic writes + schema migration + backup of config |
| Running twice (GUI + daemon) | lock file; GUI talks to running daemon if present |

## Definition of Done (v0.1.0)
- [ ] All phases above complete with exit criteria met
- [ ] 5 themes live in GUI
- [ ] `tidy status / backup / add / schedule / serve / tui` working headless
- [ ] MCP tools usable from Claude Desktop
- [ ] `install.sh` works (desktop + VPS) · AppImage launches
- [ ] 24/7 systemd service with catch-up
- [ ] Tests + ruff clean · release v0.1.0 on GitHub
