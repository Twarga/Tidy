"""Tidy CLI — full command surface.

Exit codes: 0 ok · 1 error · 2 usage (argparse) · 3 sync conflict.
"""

from __future__ import annotations

import argparse
import json
import sys

from tidy import __version__, config, repos, schedules, sync, ui
from tidy import git as git_mod
from tidy import logger as logger_mod

THEMES = ("neon", "crt", "gameboy", "watermelon", "paper")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tidy",
        description="Keep your folders tidy — backup & sync any git repo.",
    )
    parser.add_argument("--version", action="version", version=f"tidy {__version__}")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("status", help="show repos, schedules and activity")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("add", help="register a folder to sync")
    p.add_argument("path")
    p.add_argument("--at", metavar="HH:MM", help="first backup time (optional)")
    p.add_argument("--remote", metavar="URL", help="git remote URL (auto-detected if unset)")

    p = sub.add_parser("remove", help="stop syncing a folder")
    p.add_argument("path")

    p = sub.add_parser("schedule", help="add another backup time to a repo")
    p.add_argument("path")
    p.add_argument("--at", required=True, metavar="HH:MM")

    p = sub.add_parser("unschedule", help="remove a backup time from a repo")
    p.add_argument("path")
    p.add_argument("--at", required=True, metavar="HH:MM")

    p = sub.add_parser("backup", help="push changes now (all repos by default)")
    p.add_argument("repo", nargs="?", default="all", help="repo id/path, or 'all'")

    p = sub.add_parser("pull", help="pull remote changes (no push)")
    p.add_argument("repo", nargs="?", default="all", help="repo id/path, or 'all'")

    p = sub.add_parser("theme", help="set the UI theme")
    p.add_argument("name", choices=THEMES)

    p = sub.add_parser("logs", help="show recent activity")
    p.add_argument("-n", type=int, default=20, metavar="N")

    sub.add_parser("serve", help="run the 24/7 daemon (Phase 4)")
    sub.add_parser("tui", help="full-screen terminal UI (Phase 3)")
    sub.add_parser("gui", help="desktop pixel GUI (Phase 5)")
    return parser


# ---------- handlers ----------


def cmd_status(args: argparse.Namespace) -> int:
    cfg = config.load()
    if args.json:
        payload = {
            "version": cfg["version"],
            "theme": cfg["theme"],
            "autosync": cfg["autosync"],
            "notifications": cfg["notifications"],
            "stats": cfg["stats"],
            "repos": cfg["repos"],
        }
        print(json.dumps(payload, indent=2))
    else:
        ui.render_status(cfg)
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    cfg = config.load()
    repo = repos.add_repo(cfg, args.path, remote=args.remote, time=args.at)
    ui.print_ok(f"added repo [bold]{repo['id']}[/] → {repo['path']}")
    if repo["schedules"]:
        ui.print_info("schedules: " + ", ".join(s["time"] for s in repo["schedules"]))
    if repo.get("remote") is None:
        ui.print_warn("no remote configured — sync will skip until one is set: --remote <url>")
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    cfg = config.load()
    repo = repos.remove_repo(cfg, args.path)
    ui.print_ok(f"removed repo [bold]{repo['id']}[/]")
    return 0


def cmd_schedule(args: argparse.Namespace) -> int:
    cfg = config.load()
    schedules.add_schedule(cfg, args.path, args.at)
    repo = repos.find_repo(cfg, args.path)
    if repo is None:
        raise ValueError(f"repo not found: {args.path}")
    ui.print_ok(
        f"{repo['id']} schedules: "
        + ", ".join(s["time"] for s in schedules.list_schedules(cfg, repo["id"]))
    )
    return 0


def cmd_unschedule(args: argparse.Namespace) -> int:
    cfg = config.load()
    schedules.remove_schedule(cfg, args.path, args.at)
    repo = repos.find_repo(cfg, args.path)
    if repo is None:
        raise ValueError(f"repo not found: {args.path}")
    ui.print_ok(
        f"{repo['id']} schedules: "
        + (", ".join(s["time"] for s in schedules.list_schedules(cfg, repo["id"])) or "—")
    )
    return 0


def _run_target(cfg: dict, target: str, run_one, run_all) -> dict:
    if target == "all":
        return run_all(cfg)
    repo = repos.find_repo(cfg, target)
    if repo is None:
        raise ValueError(f"repo not found: {target}")
    return {"ok": True, "results": [run_one(cfg, repo)]}


def cmd_backup(args: argparse.Namespace) -> int:
    cfg = config.load()
    if not cfg["repos"]:
        ui.print_error("no repos configured — try: tidy add <path>")
        return 1
    with ui.status("syncing…"):
        result = _run_target(cfg, args.repo, sync.sync_repo, sync.sync_all)
    for item in result["results"]:
        ui.print_sync_result(item)
    if not all(item["ok"] for item in result["results"]):
        return 3 if any(item.get("conflict") for item in result["results"]) else 1
    return 0


def cmd_pull(args: argparse.Namespace) -> int:
    cfg = config.load()
    if not cfg["repos"]:
        ui.print_error("no repos configured — try: tidy add <path>")
        return 1
    with ui.status("pulling…"):
        result = _run_target(cfg, args.repo, sync.pull_repo, sync.pull_all)
    for item in result["results"]:
        ui.print_sync_result(item)
    if not all(item["ok"] for item in result["results"]):
        return 3 if any(item.get("conflict") for item in result["results"]) else 1
    return 0


def cmd_theme(args: argparse.Namespace) -> int:
    cfg = config.load()
    cfg["theme"] = args.name
    config.save(cfg)
    ui.print_ok(f"theme set to [bold]{args.name}[/]")
    return 0


def cmd_logs(args: argparse.Namespace) -> int:
    for entry in logger_mod.get_logs(args.n):
        level = entry["level"]
        style = {"INFO": "green", "WARN": "yellow", "ERROR": "red"}.get(level, "dim")
        repo = f"[bold cyan]{entry['repo']}[/] " if entry.get("repo") else ""
        ui.console.print(f"[dim]{entry['ts']}[/] [{style}]{level:5s}[/] {repo}{entry['message']}")
    return 0


def cmd_serve(_: argparse.Namespace) -> int:
    from tidy.daemon import serve

    return serve()


def cmd_tui(_: argparse.Namespace) -> int:
    from tidy.tui.app import TidyApp

    TidyApp().run()
    return 0


def cmd_gui(_: argparse.Namespace) -> int:
    from tidy.gui.main import main as gui_main

    gui_main()
    return 0


COMMANDS = {
    "status": cmd_status,
    "add": cmd_add,
    "remove": cmd_remove,
    "schedule": cmd_schedule,
    "unschedule": cmd_unschedule,
    "backup": cmd_backup,
    "pull": cmd_pull,
    "theme": cmd_theme,
    "logs": cmd_logs,
    "serve": cmd_serve,
    "tui": cmd_tui,
    "gui": cmd_gui,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    try:
        return COMMANDS[args.command](args)
    except (ValueError, git_mod.GitError) as exc:
        ui.print_error(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
