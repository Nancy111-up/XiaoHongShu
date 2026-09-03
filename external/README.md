# MediaCrawler external checkout

The Brand Agent integrates with the official MediaCrawler repository only through its CLI.
It does not import MediaCrawler business classes and does not share a database with it.

- Repository: `https://github.com/NanmiCoder/MediaCrawler.git`
- Pinned commit: `d6f7c5bb906b6dac40ddf343ef9e26438a3de092`
- Verified platform: `xhs`
- Verified storage: job-specific `--save_data_path` directories using `jsonl`
- Verified entry point: `uv run --frozen main.py`

Clone and pin the external checkout explicitly:

```text
git clone https://github.com/NanmiCoder/MediaCrawler.git external/MediaCrawler
git -C external/MediaCrawler checkout d6f7c5bb906b6dac40ddf343ef9e26438a3de092
uv --directory external/MediaCrawler sync --frozen
```

`external/MediaCrawler/` is intentionally ignored. Do not commit its login state, browser profile,
cookies, or raw output. The normal login flow may require the user to accept Chrome remote debugging,
scan a QR code, or manually complete platform verification. Never bypass those checks.

The pinned upstream license is `NON-COMMERCIAL LEARNING LICENSE 1.1`; written permission is required
before any commercial use.
