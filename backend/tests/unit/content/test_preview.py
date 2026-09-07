import pytest
from pydantic import ValidationError

from src.content.schemas import CopyPreview


def preview_body(length: int = 100) -> str:
    return "跑" * length


def test_preview_requires_exactly_three_titles_and_complete_directions() -> None:
    preview = CopyPreview(
        titles=["标题一", "标题二", "标题三"],
        body=preview_body(),
        angle="城市夜跑",
        format="图文",
        tags=["跑步", "夜跑"],
        cover_direction="夜色人物",
        product_connection="自然穿着",
        cost="low",
    )
    assert len(preview.titles) == 3
    assert 80 <= len(preview.body) <= 150


def test_preview_rejects_long_form_body() -> None:
    with pytest.raises(ValidationError):
        CopyPreview(
            titles=["一", "二", "三"],
            body=preview_body(151),
            angle="角度",
            format="图文",
            tags=[],
            cover_direction="封面",
            product_connection="无",
            cost="low",
        )


def test_preview_rejects_wrong_title_count() -> None:
    with pytest.raises(ValidationError):
        CopyPreview(
            titles=["一", "二"],
            body=preview_body(),
            angle="角度",
            format="图文",
            tags=[],
            cover_direction="封面",
            product_connection="无",
            cost="low",
        )
