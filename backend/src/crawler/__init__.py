"""MediaCrawler CLI integration boundary."""

from src.crawler.adapter import CrawlExecution, MediaCrawlerAdapter
from src.crawler.settings import MediaCrawlerSettings

__all__ = ["CrawlExecution", "MediaCrawlerAdapter", "MediaCrawlerSettings"]
