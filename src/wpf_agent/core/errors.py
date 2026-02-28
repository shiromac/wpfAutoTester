"""Custom exception hierarchy."""


class WpfAgentError(Exception):
    """Base exception for wpf-agent."""


class TargetNotFoundError(WpfAgentError):
    """Target application/window could not be found."""


class SelectorNotFoundError(WpfAgentError):
    """UI element matching the selector was not found."""


class TimeoutError(WpfAgentError):
    """Operation timed out."""


class SafetyViolationError(WpfAgentError):
    """A destructive operation was blocked by safety policy."""


class SessionError(WpfAgentError):
    """Session lifecycle error."""


class ScenarioError(WpfAgentError):
    """Scenario definition or execution error."""


class ReplayError(WpfAgentError):
    """Replay execution error."""


class UserInterruptError(WpfAgentError):
    """User interrupted the operation via mouse movement or pause state."""

    def __init__(self, reason: str, detail: str = ""):
        self.reason = reason
        self.detail = detail
        super().__init__(f"User interrupt: {reason}. {detail}")
