from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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

    def verify_checkout(self) -> None:
        if not self.checkout_path.is_dir():
            raise RuntimeError(f"MediaCrawler checkout missing: {self.checkout_path}")

        def git(*args: str) -> str:
            try:
                result = subprocess.run(
                    ["git", *args],
                    cwd=self.checkout_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(
                    f"checkout git verification failed: {exc.stderr.strip()}"
                ) from exc
            return result.stdout.strip()

        origin = git("remote", "get-url", "origin")
        if _canonical_origin(origin) != _canonical_origin(self.repository_url):
            raise RuntimeError(f"checkout origin mismatch: {origin}")
        if git("rev-parse", "HEAD") != self.commit:
            raise RuntimeError("checkout HEAD does not match pinned commit")
        if git("status", "--porcelain"):
            raise RuntimeError("checkout working tree is dirty")


def _canonical_origin(value: str) -> str:
    value = value.strip().rstrip("/")
    if value.startswith("git@"):
        host, _, path = value.partition(":")
        value = f"https://{host.removeprefix('git@')}/{path}"
    parsed = urlparse(value if "://" in value else f"https://{value}")
    if parsed.scheme != "https" or not parsed.hostname:
        raise RuntimeError("checkout origin must use official HTTPS or SSH transport")
    path = parsed.path.rstrip("/").removesuffix(".git")
    canonical = f"{parsed.hostname.lower()}{path}".rstrip("/")
    if canonical != "github.com/NanmiCoder/MediaCrawler":
        raise RuntimeError(f"checkout origin is not the official repository: {value}")
    return canonical
