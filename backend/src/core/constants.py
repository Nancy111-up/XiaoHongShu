"""Centralised enumerations and magic numbers."""

from __future__ import annotations

from enum import StrEnum


class TaskStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    WAITING_FOR_HUMAN = "waiting_for_human"
    DONE = "done"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TaskSource(StrEnum):
    MANUAL = "manual"
    INSPIRATION_POOL = "inspiration_pool"


class KanbanColumn(StrEnum):
    INSPIRATION = "inspiration"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    DONE = "done"


class ComplianceSeverity(StrEnum):
    PASS = "pass"
    MILD_WARNING = "mild_warning"
    SEVERE_VIOLATION = "severe_violation"


class FeedbackAction(StrEnum):
    APPROVE = "approve"
    REVISE = "revise"


# ---- Limits ----
MAX_REVISION_ROUNDS = 5
MAX_SEARCH_RESULTS = 5
SEARCH_TIMEOUT_SECONDS = 30
TOKEN_SLIM_THRESHOLD = 8000
MAX_VIOLATIONS_BEFORE_TERMINATE = 3
