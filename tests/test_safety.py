"""Tests for safety module."""

import pytest

from wpf_agent.config import SafetyConfig
from wpf_agent.core.errors import SafetyViolationError
from wpf_agent.core.safety import check_safety, is_destructive


def test_blocks_destructive():
    config = SafetyConfig(allow_destructive=False)
    with pytest.raises(SafetyViolationError):
        check_safety("click", "DeleteButton", config)


def test_allows_safe():
    config = SafetyConfig(allow_destructive=False)
    # Should not raise
    check_safety("click", "SaveButton", config)


def test_allows_when_permitted():
    config = SafetyConfig(allow_destructive=True)
    # Should not raise even for destructive
    check_safety("click", "DeleteButton", config)


def test_is_destructive_true():
    config = SafetyConfig()
    assert is_destructive("click", {"selector": "DeleteAll"}, config) is True


def test_is_destructive_false():
    config = SafetyConfig()
    assert is_destructive("click", {"selector": "OpenFile"}, config) is False
