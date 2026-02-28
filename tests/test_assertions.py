"""Tests for assertion result structure (no UIA required)."""

from wpf_agent.testing.assertions import AssertionResult


def test_assertion_result_passed():
    r = AssertionResult(True, "OK", expected="foo", actual="foo")
    d = r.to_dict()
    assert d["passed"] is True
    assert d["expected"] == "foo"
    assert d["actual"] == "foo"


def test_assertion_result_failed():
    r = AssertionResult(False, "Mismatch", expected="bar", actual="baz")
    d = r.to_dict()
    assert d["passed"] is False
    assert d["message"] == "Mismatch"
