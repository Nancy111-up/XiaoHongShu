from __future__ import annotations

from typing import Literal


def classify_confidence(
    snapshot_count: int,
    valid_notes: int,
    unique_authors: int,
    data_completeness: float,
    comment_samples: int,
    analysis_independent_of_comments: bool,
    partial_success: bool,
) -> Literal["High", "Medium", "Low"]:
    if partial_success:
        return "Medium" if valid_notes >= 3 and unique_authors >= 2 else "Low"
    if (
        snapshot_count >= 2
        and valid_notes >= 5
        and unique_authors >= 3
        and data_completeness >= 0.8
        and (comment_samples >= 10 or analysis_independent_of_comments)
    ):
        return "High"
    if valid_notes >= 3 and unique_authors >= 2:
        return "Medium"
    return "Low"
