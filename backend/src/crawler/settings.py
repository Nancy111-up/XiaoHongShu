from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

OFFICIAL_REPOSITORY_URL = "https://github.com/NanmiCoder/MediaCrawler.git"
PINNED_COMMIT = "d6f7c5bb906b6dac40ddf343ef9e26438a3de092"


@dataclass(frozen=True)
class MediaCrawlerSettings:
    """Immutable settings for the pinned MediaCrawler CLI boundary."""

    checkout_path: Path
    python_executable: str = "uv"
    runner_args: tuple[str, ...] = ("run", "--frozen", "main.py")
    repository_url: str = OFFICIAL_REPOSITORY_URL
    commit: str = PINNED_COMMIT
    platform: str = "xhs"
    login_type: str = "qrcode"
    save_data_option: str = "jsonl"
    max_concurrency: int = 1
    search_max_notes: int = 40
    detail_max_comments_per_note: int = 20
    headless: bool = False

    @classmethod
    def from_yaml(cls, path: Path) -> MediaCrawlerSettings:
        """Load the checked-in config and resolve its checkout from the project root."""

        config_path = path.resolve()
        payload: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        project_root = config_path.parent.parent
        checkout = Path(payload["checkout"]["path"])
        if not checkout.is_absolute():
            checkout = project_root / checkout
        repository = payload["repository"]
        runner = payload["runner"]
        crawl = payload["crawl"]
        return cls(
            checkout_path=checkout.resolve(),
            python_executable=str(runner["executable"]),
            runner_args=tuple(str(value) for value in runner["args"]),
            repository_url=str(repository["url"]),
            commit=str(repository["commit"]),
            platform=str(crawl["platform"]),
            login_type=str(crawl["login_type"]),
            save_data_option=str(crawl["save_data_option"]),
            max_concurrency=int(crawl["max_concurrency"]),
            search_max_notes=int(crawl["search_max_notes"]),
            detail_max_comments_per_note=int(crawl["detail_max_comments_per_note"]),
            headless=bool(crawl["headless"]),
        )
