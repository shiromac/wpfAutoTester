"""Assertion functions for scenario testing."""

from __future__ import annotations

import re
from typing import Any

from wpf_agent.core.errors import ScenarioError
from wpf_agent.core.target import ResolvedTarget
from wpf_agent.uia.engine import UIAEngine, _find_element
from wpf_agent.uia.selector import Selector


class AssertionResult:
    __slots__ = ("passed", "message", "expected", "actual")

    def __init__(self, passed: bool, message: str, expected: Any = None, actual: Any = None):
        self.passed = passed
        self.message = message
        self.expected = expected
        self.actual = actual

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "message": self.message,
            "expected": self.expected,
            "actual": self.actual,
        }


def check_assertion(
    target: ResolvedTarget,
    selector: Selector,
    assertion_type: str,
    expected: Any = None,
) -> AssertionResult:
    """Run a single assertion against a UI element."""
    try:
        if assertion_type == "exists":
            try:
                _find_element(target, selector)
                return AssertionResult(True, "Element exists")
            except Exception:
                return AssertionResult(
                    False, "Element does not exist", expected=True, actual=False
                )

        elem = _find_element(target, selector)

        if assertion_type == "text_equals":
            actual = elem.window_text()
            ok = actual == expected
            return AssertionResult(
                ok,
                f"text_equals: {actual!r} == {expected!r}" if ok else f"text_equals failed",
                expected=expected,
                actual=actual,
            )

        if assertion_type == "text_contains":
            actual = elem.window_text()
            ok = expected in actual
            return AssertionResult(
                ok,
                f"text_contains: {expected!r} in {actual!r}" if ok else f"text_contains failed",
                expected=expected,
                actual=actual,
            )

        if assertion_type == "enabled":
            actual = elem.is_enabled()
            exp = expected if isinstance(expected, bool) else True
            ok = actual == exp
            return AssertionResult(ok, f"enabled={actual}", expected=exp, actual=actual)

        if assertion_type == "visible":
            actual = elem.is_visible()
            exp = expected if isinstance(expected, bool) else True
            ok = actual == exp
            return AssertionResult(ok, f"visible={actual}", expected=exp, actual=actual)

        if assertion_type == "selected":
            try:
                actual = elem.is_selected()
            except Exception:
                actual = None
            exp = expected if isinstance(expected, bool) else True
            ok = actual == exp
            return AssertionResult(ok, f"selected={actual}", expected=exp, actual=actual)

        if assertion_type == "value_equals":
            try:
                actual = elem.get_value()
            except Exception:
                actual = None
            ok = actual == expected
            return AssertionResult(
                ok, f"value_equals: {actual!r}", expected=expected, actual=actual
            )

        if assertion_type == "regex":
            actual = elem.window_text()
            ok = bool(re.search(expected, actual))
            return AssertionResult(
                ok,
                f"regex: pattern={expected!r} text={actual!r}",
                expected=expected,
                actual=actual,
            )

        return AssertionResult(False, f"Unknown assertion type: {assertion_type}")

    except Exception as exc:
        return AssertionResult(False, f"Assertion error: {exc}")
