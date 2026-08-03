"""Sync engine — the heart of Tidy.

``sync_repo`` runs the full pipeline for one repo:
    fetch -> pull --rebase (remote edits) -> commit (if changes) -> push

It never deletes or destroys data: a rebase conflict aborts cleanly and is
reported instead of being resolved destructively.
"""

from __future__ import annotations

from datetime import datetime
from time import monotonic

from tidy import git
from tidy.config import update_stats
from tidy.logger import log_error, log_info, log_warn

__all__ = ["sync_all", "sync_repo"]

_OK = {"ok": True, "skipped": True, "committed": False}


def _elapsed(started: float) -> float:
    return round(monotonic() - started, 2)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sync_repo(cfg: dict, repo: dict) -> dict:
    """Sync one repo: fetch, pull --rebase, commit, push. Returns a result dict."""
    git.ensure_git()
    started = monotonic()
    repo_id = repo["id"]
    path = repo["path"]
    branch = repo.get("branch") or git.default_branch(path)

    def fail(message: str, **extra: object) -> dict:
        log_error(message, repo_id)
        update_stats(cfg, last_run=_now_iso(), last_error=message)
        return {
            "ok": False,
            "id": repo_id,
            "message": message,
            **extra,
            "elapsed": _elapsed(started),
        }

    if not git.has_remote(path):
        message = f"{repo_id}: no remote configured — skipping"
        log_warn(message, repo_id)
        update_stats(cfg, last_run=_now_iso(), last_error=message)
        return {**_OK, "ok": False, "id": repo_id, "message": message, "elapsed": _elapsed(started)}

    try:
        git.fetch(path)

        if git.has_commits(path) and git.remote_has_branch(path, branch):
            try:
                git.pull_rebase(path, branch)
            except git.GitError as exc:
                try:
                    git.run_git(path, "rebase", "--abort", check=False)
                except git.GitError:
                    pass
                return fail(f"{repo_id}: merge conflict — {exc}", conflict=True)

        commit_message = f"backup {datetime.now().astimezone():%Y-%m-%d %H:%M}"
        committed = git.commit_all(path, commit_message)
        git.push(path, branch)
    except git.GitError as exc:
        return fail(f"{repo_id}: {exc}")

    elapsed = _elapsed(started)
    stats = cfg["stats"]
    update_stats(
        cfg,
        total_pushes=stats["total_pushes"] + 1,
        last_run=_now_iso(),
        last_error=None,
    )
    detail = "pushed ✓" if committed else "nothing to commit — skipped"
    message = f"{repo_id}: {detail} ({elapsed}s)"
    log_info(message, repo_id)
    return {
        "ok": True,
        "id": repo_id,
        "message": message,
        "committed": committed,
        "skipped": not committed,
        "elapsed": elapsed,
    }


def sync_all(cfg: dict) -> dict:
    """Sync every configured repo. Runs each independently and aggregates."""
    results = [sync_repo(cfg, repo) for repo in cfg["repos"]]
    return {"ok": all(result["ok"] for result in results), "results": results}
