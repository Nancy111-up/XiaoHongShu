from __future__ import annotations

import pytest
from fastapi import FastAPI

from src.refresh.scheduler import AutoRefreshController, configure_scheduler


async def _succeeds() -> None:
    return None


async def _fails() -> None:
    raise RuntimeError("fixture failure")


def test_scheduler_uses_shanghai_business_hours_without_startup_catchup() -> None:
    app = FastAPI()

    scheduler = configure_scheduler(app, _succeeds)
    job = scheduler.get_job("scheduled-refresh")

    assert job is not None
    assert str(job.trigger) == "cron[hour='9,15,21', minute='0']"
    assert str(job.trigger.timezone) == "Asia/Shanghai"
    assert job.misfire_grace_time == 1


@pytest.mark.asyncio
async def test_scheduler_pauses_after_two_consecutive_failures() -> None:
    app = FastAPI()
    scheduler = configure_scheduler(app, _fails)
    controller = AutoRefreshController(scheduler, _fails)

    assert await controller.run() is False
    assert await controller.run() is False

    job = scheduler.get_job("scheduled-refresh")
    assert job is not None
    assert job.next_run_time is None
