from datetime import UTC, datetime, timedelta

from src.topics.representatives import CandidateNote, choose_representatives


def test_representatives_prioritize_relevance_then_author_diversity() -> None:
    now = datetime(2026, 9, 7, tzinfo=UTC)
    notes = [
        CandidateNote("high-a", "author-a", 0.9, 100, now, True),
        CandidateNote("high-a-2", "author-a", 0.8, 99, now, True),
        CandidateNote("diverse-b", "author-b", 0.8, 60, now - timedelta(hours=1), True),
        CandidateNote("unreadable", "author-c", 1.0, 500, now, False),
    ]

    selected = choose_representatives(notes)

    assert [note.note_id for note in selected] == ["high-a", "diverse-b", "high-a-2"]


def test_representatives_never_return_more_than_five() -> None:
    now = datetime(2026, 9, 7, tzinfo=UTC)
    notes = [CandidateNote(str(index), str(index), 1, index, now, True) for index in range(8)]

    assert len(choose_representatives(notes, limit=10)) == 5
