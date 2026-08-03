# tidy — CLI reference

`tidy` is the terminal front-end of Tidy. Everything is one command:

```bash
tidy <command> [args]
```

Global behaviors:

- Config + logs live in `~/.config/tidy/` (override with `TIDY_CONFIG_DIR`).
- A **repo** is a git-backed folder; a repo can have **many** daily backup times.
- Commands are safe to re-run; nothing destructive without you asking.

---

## `tidy status [--json]`

Show all repos, schedules, remotes and last activity. `--json` prints the
machine-readable payload (see tests for the golden schema).

## `tidy add PATH [--at HH:MM] [--remote URL]`

Register a folder to sync. Creates a git repo if needed; auto-detects the
remote + branch. `--at` sets the first daily backup time (more via `schedule`).

## `tidy remove PATH`

Stop syncing a folder (config only — the folder is untouched).

## `tidy schedule PATH --at HH:MM`

Add **another** daily backup time to a repo. Times are validated (`HH:MM`, 24 h),
deduplicated and kept sorted. Example: `tidy add ~/vault --at 18:00` then
`tidy schedule ~/vault --at 21:00` → backups at both 18:00 and 21:00.

## `tidy unschedule PATH --at HH:MM`

Remove one daily backup time. Other times stay.

## `tidy backup [REPO]`

Commit + push now. `REPO` defaults to `all`. Clean trees are skipped (not an error).

## `tidy pull [REPO]`

Fetch + pull `--rebase` remote changes. No commit, no push.

## `tidy theme NAME`

Set the UI theme: `neon | crt | gameboy | watermelon | paper`.

## `tidy logs [-n N]`

Show the last `N` activity-log entries (default 20).

## `tidy serve`

Run the 24/7 daemon in the foreground (APScheduler + systemd units in
`packaging/`). Prints start/stop markers for journalctl.

## `tidy tui`

Full-screen terminal UI: `b` backup, `p` pull, Enter backup, `r` refresh,
`t` cycle theme, `q` quit.

## `tidy gui`

Desktop pixel GUI (pywebview) — needs a display + PyGObject/webkit2gtk.
Falls back gracefully headless.

## `tidy mcp`

Run the MCP server over stdio (see `docs/MCP.md`).

---

Exit codes: `0` success, `1` runtime error, `2` usage error (argparse).
