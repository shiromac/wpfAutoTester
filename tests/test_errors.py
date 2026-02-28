"""Tests for error hierarchy."""

from wpf_agent.core.errors import (
    ReplayError,
    SafetyViolationError,
    ScenarioError,
    SelectorNotFoundError,
    SessionError,
    TargetNotFoundError,
    TimeoutError,
    WpfAgentError,
)


def test_hierarchy():
    assert issubclass(TargetNotFoundError, WpfAgentError)
    assert issubclass(SelectorNotFoundError, WpfAgentError)
    assert issubclass(TimeoutError, WpfAgentError)
    assert issubclass(SafetyViolationError, WpfAgentError)
    assert issubclass(SessionError, WpfAgentError)
    assert issubclass(ScenarioError, WpfAgentError)
    assert issubclass(ReplayError, WpfAgentError)


def test_exception_message():
    e = TargetNotFoundError("PID 999 not found")
    assert "PID 999" in str(e)
