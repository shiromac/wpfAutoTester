"""Tests for wait utilities."""

import pytest

from wpf_agent.core.errors import TimeoutError
from wpf_agent.uia.waits import wait_until


def test_wait_until_immediate():
    result = wait_until(lambda: 42, timeout_ms=1000)
    assert result == 42


def test_wait_until_timeout():
    with pytest.raises(TimeoutError):
        wait_until(lambda: None, timeout_ms=200, poll_ms=50, message="test timeout")


def test_wait_until_eventual():
    counter = {"n": 0}

    def pred():
        counter["n"] += 1
        return "done" if counter["n"] >= 3 else None

    result = wait_until(pred, timeout_ms=5000, poll_ms=50)
    assert result == "done"
