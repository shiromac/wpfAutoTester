"""Wait utilities for UIA operations."""

from __future__ import annotations

import time
from typing import Callable, TypeVar

from wpf_agent.constants import DEFAULT_TIMEOUT_MS
from wpf_agent.core.errors import TimeoutError

T = TypeVar("T")


def wait_until(
    predicate: Callable[[], T | None],
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    poll_ms: int = 100,
    message: str = "Condition not met",
) -> T:
    """Poll predicate until truthy or timeout."""
    deadline = time.monotonic() + timeout_ms / 1000.0
    last_result: T | None = None
    while time.monotonic() < deadline:
        last_result = predicate()
        if last_result:
            return last_result
        time.sleep(poll_ms / 1000.0)
    raise TimeoutError(f"{message} (timeout={timeout_ms}ms)")


def wait_for_window(
    find_fn: Callable[[], object | None],
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> object:
    """Wait for a window to appear."""
    return wait_until(find_fn, timeout_ms=timeout_ms, message="Window not found")
