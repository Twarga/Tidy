# Manual test sheet

Work through this against a **throwaway folder** first (or a copy of a real repo),
then against your real `Twarga-System` vault. Tick each box as you go.

Prep:

```bash
cd ~/Documents/Tidy
./dev.sh            # env + GUI
source .venv/bin/activate
tidy --version      # expect: tidy 0.1.0
```

---

## 1. CLI & schema

- [ ] `tidy status` shows your repo, schedule `12:30`, remote ✓
- [ ] `tidy status --json` is valid JSON with keys `version,theme,autosync,notifications,stats,repos`
- [ ] `tidy add /tmp/cli-demo --at 09:00` registers a folder
- [ ] `tidy schedule /tmp/cli-demo --at 21:00` adds a **second** time
- [ ] `tidy unschedule /tmp/cli-demo --at 21:00` removes it (the first survives)
- [ ] `tidy backup all` with a dirty file → commits + pushes; re-run → "skipped"
- [ ] `tidy pull /tmp/cli-demo` → pulls remote changes (no push)
- [ ] `tidy theme gameboy` → persists; `tidy theme nope` → error
- [ ] `tidy logs -n 5` → shows recent INFO/WARN/ERROR entries

## 2. 24/7 daemon

- [ ] `tidy serve` starts, prints `daemon started`, installs signals
- [ ] Ctrl-C → clean stop, `daemon stopped`
- [ ] **single-instance**: starting a 2nd daemon exits (lock file)
- [ ] **config reload**: edit a schedule while running → daemon reschedules without restart
- [ ] `systemctl --user restart tidy` (after install) keeps it alive across reboots

## 3. GUI (needs a display)

- [ ] `./dev.sh gui` opens the landscape window (toolbar + sidebar + detail + log)
- [ ] Left sidebar lists your repos with a health dot
- [ ] Click a repo → detail shows path, remote/branch badges, schedule chips
- [ ] Click `✕ 12:30` chip → schedule removed; `＋ ADD TIME` + time input → added
- [ ] **PUSH NOW** → real push; toolbar status flips to "last run failed" on error
- [ ] **Theme dots** in the toolbar switch `data-theme` live and persist
- [ ] **Activity log** updates by itself (4s poll)
- [ ] **Close window (✕)** → window hides, process stays alive (check `ps` / tray)
- [ ] Tray **Quit** → the app actually exits

## 4. Tray mini-panel

- [ ] Right-click the tray icon → menu shows: status, per-repo items, Backup all, Pull all, Theme submenu, Show window, Quit
- [ ] "Show window" restores a hidden window
- [ ] Theme from tray changes the GUI live (same config)
- [ ] On a **headless** box (`unset DISPLAY`) → `tidy gui` warns and runs without tray (no crash)

## 5. Wake catch-up

- [ ] Schedule a time in the past, run `tidy serve` after that time → the missed run fires (misfire grace 1 h)
- [ ] Repo with several schedules → a job per (repo × time), none skipped

## 6. MCP (real stdio)

- [ ] `tidy mcp` starts the server; connect with the MCP client → `list_tools` shows 10 tools
- [ ] `backup_now` / `add_schedule` mutate real config
- [ ] `set_setting(new, invalid)` → returns `ok:false` (never crashes)

## 7. Packaging

- [ ] `bash install.sh --no-service` in a sandbox: clone, venv, links, exit 0; re-run → same (idempotent)
- [ ] `bash install.sh --mcp` writes `~/.config/Claude/claude_desktop_config.json`
- [ ] `APPIMAGE_EXTRACT_AND_RUN=1 ./tidy-0.1.0-x86_64.AppImage --version` → `tidy 0.1.0`
- [ ] AppImage `status` shows your real vault; `gui` opens if webkit2gtk present