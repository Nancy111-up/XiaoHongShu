from __future__ import annotations

from collections.abc import Awaitable, Callable
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

SCHEDULED_REFRESH_JOB_ID = "scheduled-refresh"
SHANGHAI_TIMEZONE = ZoneInfo("Asia/Shanghai")

RefreshRunner = Callable[[], Awaitable[None]]


class AutoRefreshController:
    def __init__(self, scheduler: AsyncIOScheduler, refresh: RefreshRunner) -> None:
        self._scheduler = scheduler
        self._refresh = refresh
        self._consecutive_failures = 0

    async def run(self) -> bool:
        try:
            await self._refresh()
        except Exception:
            self._consecutive_failures += 1
            if self._consecutive_failures >= 2:
                self._scheduler.pause_job(SCHEDULED_REFRESH_JOB_ID)
            return False
        self._consecutive_failures = 0
        return True


def configure_scheduler(app: FastAPI, refresh: RefreshRunner) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=SHANGHAI_TIMEZONE)
    controller = AutoRefreshController(scheduler, refresh)
    scheduler.add_job(
        controller.run,
        "cron",
        id=SCHEDULED_REFRESH_JOB_ID,
        hour="9,15,21",
        minute=0,
        misfire_grace_time=1,
        coalesce=True,
        replace_existing=True,
    )
    app.state.scheduler = scheduler
    app.state.auto_refresh_controller = controller
    return scheduler
