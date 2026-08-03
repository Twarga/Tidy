# MCP integration

Tidy exposes every engine action (repos, schedules, sync, settings, logs) as
MCP tools over stdio, so AI agents — Claude Desktop, Cursor, Cline, and others
that speak MCP — can drive backups with natural language.

## Tools

| Tool | What it does |
|---|---|
| `list_repos` | all repos + paths + remotes + schedules |
| `add_repo(path, remote?, time?)` | register a folder; optional remote URL + initial daily time |
| `remove_repo(path_or_id)` | stop syncing a repo |
| `add_schedule(repo, time)` | add a daily backup time (HH:MM) |
| `remove_schedule(repo, time)` | remove a daily backup time |
| `backup_now(repo?)` | commit + push now (all repos if omitted) |
| `pull_now(repo?)` | pull remote changes (no push) |
| `get_status()` | summary: repos, settings, stats |
| `get_logs(n=20)` | recent activity entries |
| `set_setting(key, value)` | theme / autosync / notifications |

## Run the server

```bash
tidy-mcp            # or: python -m tidy.mcp
```

It speaks MCP over **stdio** — no ports, no daemon needed.

## Claude Desktop

Point Claude Desktop at the server. On macOS the app config lives at:

```
~/Library/Application Support/Claude/claude_desktop_config.json
```

On Linux:

```
~/.config/Claude/claude_desktop_config.json
```

Add:

```json
{
  "mcpServers": {
    "tidy": {
      "command": "/home/twarga/.local/bin/tidy-mcp"
    }
  }
}
```

A ready-to-merge sample lives in [`docs/mcp-claude.json`](mcp-claude.json).
Adjust the `command` path to wherever `tidy-mcp` was installed (`which tidy-mcp`).

Then you can say things like:

> "Back up all my repos now" · "Add a 21:00 backup for my notes" · "What happened in the last sync?"

## Cursor / Cline

In Cursor: Settings → MCP → Add new MCP server → type `stdio`, command
`tidy-mcp`. In Cline: MCP servers → Add → stdio → same command.

## pi (CLI-based)

`pi` prefers CLI over MCP. The [`tidy` skill](SKILL.md) (installed at
`~/.agents/skills/tidy/`) teaches pi to drive Tidy through the `tidy` CLI
instead — same power, no server process needed.
