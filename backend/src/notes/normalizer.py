from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit, urlunsplit

from src.notes.schemas import NormalizedComment, NormalizedNote

_SENSITIVE_KEYS = {"authorization", "cookie", "cookies", "set-cookie", "xsec_token"}
_COUNT_MULTIPLIERS = {"万": Decimal(10_000), "千": Decimal(1_000)}


def _required_string(raw: dict[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _optional_string(raw: dict[str, object], key: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string or null")
    return value


def _parse_count(value: object, field: str) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")
    if isinstance(value, int):
        result = value
    else:
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        text = text.removesuffix("+")
        multiplier = Decimal(1)
        if text[-1:] in _COUNT_MULTIPLIERS:
            multiplier = _COUNT_MULTIPLIERS[text[-1]]
            text = text[:-1]
        try:
            parsed = Decimal(text) * multiplier
        except InvalidOperation as exc:
            raise ValueError(f"{field} must be numeric") from exc
        if parsed != parsed.to_integral_value():
            raise ValueError(f"{field} must resolve to an integer")
        result = int(parsed)
    if result < 0:
        raise ValueError(f"{field} cannot be negative")
    return result


def _parse_milliseconds(value: object, field: str) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} must be Unix epoch milliseconds")
    if not isinstance(value, (int, str)):
        raise ValueError(f"{field} must be Unix epoch milliseconds")
    try:
        milliseconds = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be Unix epoch milliseconds") from exc
    if milliseconds < 0:
        raise ValueError(f"{field} cannot be negative")
    try:
        return datetime.fromtimestamp(milliseconds / 1000, tz=UTC)
    except (OSError, OverflowError, ValueError) as exc:
        raise ValueError(f"{field} is outside the supported timestamp range") from exc


def _sanitize_url(value: str | None) -> str | None:
    if value is None:
        return None
    parsed = urlsplit(value)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _sanitize_raw(value: object) -> object:
    if isinstance(value, dict):
        sanitized: dict[str, object] = {}
        for key, item in value.items():
            if key.lower() in _SENSITIVE_KEYS:
                continue
            if key.lower().endswith("url") and isinstance(item, str):
                sanitized[key] = _sanitize_url(item)
            else:
                sanitized[key] = _sanitize_raw(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_raw(item) for item in value]
    return value


def _completeness(values: tuple[object, ...]) -> float:
    present = sum(value is not None and value != "" for value in values)
    return present / len(values)


def normalize_search_record(
    raw: dict[str, object], captured_at: datetime
) -> NormalizedNote:
    if captured_at.tzinfo is None:
        raise ValueError("captured_at must be timezone-aware")
    note_id = _required_string(raw, "note_id")
    title = _optional_string(raw, "title")
    body = _optional_string(raw, "desc")
    author_id = _optional_string(raw, "creator_hash")
    author_name = _optional_string(raw, "nickname")
    published_at = _parse_milliseconds(raw.get("time"), "time")
    likes = _parse_count(raw.get("liked_count"), "liked_count")
    collects = _parse_count(raw.get("collected_count"), "collected_count")
    comments = _parse_count(raw.get("comment_count"), "comment_count")
    shares = _parse_count(raw.get("share_count"), "share_count")
    url = _sanitize_url(_optional_string(raw, "note_url"))
    keyword = _optional_string(raw, "source_keyword")
    position_value = raw.get("_search_position")
    search_position = _parse_count(position_value, "_search_position")
    sanitized = _sanitize_raw(raw)
    assert isinstance(sanitized, dict)
    return NormalizedNote(
        note_id=note_id,
        title=title,
        body=body,
        author_id=author_id,
        author_name=author_name,
        published_at=published_at,
        captured_at=captured_at.astimezone(UTC),
        likes=likes,
        collects=collects,
        comments=comments,
        shares=shares,
        url=url,
        raw_payload=sanitized,
        data_completeness=_completeness(
            (title, body, author_id, author_name, published_at, likes, collects, comments, url)
        ),
        keyword=keyword,
        search_position=search_position,
    )


def normalize_comment_record(raw: dict[str, object], job_id: str) -> NormalizedComment:
    comment_id = _required_string(raw, "comment_id")
    note_id = _required_string(raw, "note_id")
    if not job_id.strip():
        raise ValueError("job_id must be non-empty")
    parent = _optional_string(raw, "parent_comment_id")
    sanitized = _sanitize_raw(raw)
    assert isinstance(sanitized, dict)
    return NormalizedComment(
        comment_id=comment_id,
        note_id=note_id,
        job_id=job_id,
        content=_optional_string(raw, "content"),
        likes=_parse_count(raw.get("like_count"), "like_count"),
        captured_at=_parse_milliseconds(raw.get("last_modify_ts"), "last_modify_ts"),
        parent_comment_id=parent or None,
        raw_payload=sanitized,
    )
