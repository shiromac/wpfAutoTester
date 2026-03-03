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


class MultipleElementsFoundError(WpfAgentError):
    """Multiple UI elements matched the selector — ambiguous."""

    def __init__(self, selector_desc: str, candidates: list[dict]):
        self.selector_desc = selector_desc
        self.candidates = candidates
        lines = [f"Multiple elements match selector: {selector_desc}"]
        for i, c in enumerate(candidates):
            lines.append(
                f"  [{i}] automation_id={c.get('automation_id', '')!r} "
                f"name={c.get('name', '')!r} "
                f"control_type={c.get('control_type', '')} "
                f"rect={c.get('rect')}"
            )
        super().__init__("\n".join(lines))


class UserInterruptError(WpfAgentError):
    """User interrupted the operation via mouse movement or pause state."""

    def __init__(self, reason: str, detail: str = ""):
        self.reason = reason
        self.detail = detail
        super().__init__(f"User interrupt: {reason}. {detail}")
