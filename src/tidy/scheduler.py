"""Scheduler — turns per-repo backup times into APScheduler jobs.

Jobs are rebuilt live from config, so editing schedules takes effect without a
restart. Missed runs (e.g. laptop asleep) are re-fired via ``misfire_grace_time``
and coalesced so only one run happens per slot.
"""

from __future__ import annotations

from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from tidy import config, repos, sync

__all__ = ["SyncScheduler"]

_JOB_PREFIX = "repo:"
_MISFIRE_GRACE = 3600


def _local_timezone():
    try:
        return datetime.now().astimezone().tzinfo
    except (AttributeError, OSError):  # pragma: no cover - defensive
        from zoneinfo import ZoneInfo

        return ZoneInfo("UTC")


def build_job_id(repo_id: str, time: str) -> str:
    return f"{_JOB_PREFIX}{repo_id}:{time.replace(':', '')}"


class SyncScheduler:
    """Wraps a background scheduler populated from the current config."""

    def __init__(self) -> None:
        self._scheduler = BackgroundScheduler(timezone=_local_timezone())
        self._scheduler.start()

    # ------------------------------------------------------------------ jobs

    def reconfigure(self, cfg: dict) -> None:
        """Build jobs to match config: one CronTrigger per enabled schedule."""
        desired: set[str] = set()
        for repo in cfg.get("repos", []):
            for schedule in repo.get("schedules", []):
                if not schedule.get("enabled", True):
                    continue
                job_id = build_job_id(repo["id"], schedule["time"])
                desired.add(job_id)
                if self._scheduler.get_job(job_id) is None:
                    hour, minute = (int(part) for part in schedule["time"].split(":"))
                    self._scheduler.add_job(
                        self._sync_one,
                        CronTrigger(hour=hour, minute=minute),
                        args=(repo["id"],),
                        id=job_id,
                        coalesce=True,
                        misfire_grace_time=_MISFIRE_GRACE,
                    )

        # Drop jobs whose repo/schedule was removed from config.
        for job in list(self._scheduler.get_jobs()):
            if job.id.startswith(_JOB_PREFIX) and job.id not in desired:
                self._scheduler.remove_job(job.id)

    def jobs(self) -> list[str]:
        return [job.id for job in self._scheduler.get_jobs() if job.id.startswith(_JOB_PREFIX)]

    # -------------------------------------------------------------- execution

    def _sync_one(self, repo_id: str) -> None:
        cfg = config.load()
        repo = repos.find_repo(cfg, repo_id)
        if repo is None:
            return
        result = sync.sync_repo(cfg, repo)
        _notify_result(repo_id, result)

    # ----------------------------------------------------------------- teardown

    def shutdown(self) -> None:
        try:
            self._scheduler.shutdown(wait=False)
        except Exception:  # noqa: BLE001, S110 - already stopping, nothing to do
            pass


def _notify_result(repo_id: str, result: dict) -> None:
    from tidy.notify import notify

    if result["ok"]:
        notify(f"Tidy · {repo_id}", result["message"], level="info")
    else:
        notify(f"Tidy · {repo_id} failed", result["message"], level="error")
