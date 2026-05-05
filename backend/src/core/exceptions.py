"""Custom application exceptions."""


class XHSAgentError(Exception):
    """Base exception for XHS Brand Agent."""


class TaskNotFoundError(XHSAgentError):
    """Raised when thread_id does not match any task."""


class TaskNotCancellableError(XHSAgentError):
    """Raised when task is already done or cancelled."""


class InvalidStateTransitionError(XHSAgentError):
    """Raised when attempting an invalid status transition."""


class AssetNotFoundError(XHSAgentError):
    """Raised when a brand asset file is missing."""
