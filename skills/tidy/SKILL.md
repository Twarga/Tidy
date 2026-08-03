---
name: tidy
description: Drive the Tidy backup & sync tool from the terminal. Use whenever the user asks to back up, sync, schedule, push, pull, or manage their git-backed folders/repos (e.g. an Obsidian vault). Tidy is a git-based backup tool — each repo folder has one or more daily backup times, and every other goal is mapped to a `tidy` CLI command.
metadata:
  trigger: backup, sync, push, pull, schedule, status, git, obsidian vault
---

# Tidy

Tidy is a backup & sync app that mirrors a folder/git repo to a remote. It's CLI-first:
prefer the `tidy` command over raw git. Always run commands (never fabricate output).

Check config first: `tidy status --json` shows repos, paths, remotes, schedules, and last-run stats.

## Quick reference

```bash
tidy status [--json]                       # show repos + schedules + activity
tidy add ~/folder --at 18:00 [--remote URL] # register a folder (auto-detects git remote)
tidy remove ~/folder                        # stop syncing a folder
tidy schedule ~/folder --at 21:00           # add ANOTHER daily backup time  (a folder can have several)
tidy unschedule ~/folder --at 21:00         # remove a daily backup time
tidy backup [all | <repo>]                  # commit + push NOW (defaults to all)
tidy pull [all | <repo>]                    # pull remote changes, no push
tidy theme <neon|crt|gameboy|watermelon|paper>
tidy logs -n 20                             # recent activity
tidy serve                                  # run the 24/7 daemon in the foreground
tidy tui                                    # full-screen terminal UI
tidy gui                                    # desktop pixel GUI (needs a display)
```

## Workflow rules

- **A repo maps to a folder.** A repo can have **many** schedule times; add extras with `tidy schedule PATH --at HH:MM`. To change the time, remove the old one then add the new.
- **Config is at `~/.config/tidy/config.json`** (or `$TIDY_CONFIG_DIR`). Avoid editing it by hand — use the CLI.
- **Prefer that user's commands**: after an action, confirm with `tidy status` (or `--json` for scripting).
- **Push** is `backup`; **pull-only** is `pull`. `all` is the default target.
- If a repo has no remote, sync will skip until one is set: `tidy add <path> --remote <url>`, or set the git remote manually.

## Troubleshooting

- "nothing to commit — skipped": the folder had no changes; that's the expected clean outcome, not an error.
- Multiple repos: list them first, then target by id or path.
- If `tidy` isn't on PATH, it lives inside the project venv: `~/Documents/Tidy/.venv/bin/tidy`.