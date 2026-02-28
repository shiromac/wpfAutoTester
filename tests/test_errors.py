"""Tests for wpfautotester.errors module."""

from __future__ import annotations

from wpfautotester.errors import (
    EXIT_AMBIGUOUS_TARGET,
    EXIT_ELEMENT_NOT_FOUND,
    EXIT_ELEMENT_NOT_INTERACTIVE,
    EXIT_ELEMENT_OFFSCREEN,
    EXIT_TIMEOUT,
    AmbiguousTargetError,
    ElementNotFoundError,
    ElementNotInteractiveError,
    ElementOffscreenError,
    TargetingTimeoutError,
    WpfAutoTesterError,
    exit_description,
)


def test_exit_description_ok():
    assert exit_description(0) == "Success"


def test_exit_description_unknown():
    desc = exit_description(999)
    assert "999" in desc


def test_wpf_auto_tester_error_default_code():
    err = WpfAutoTesterError("something went wrong")
    assert err.exit_code == 1
    assert "something went wrong" in str(err)


def test_element_not_found_error():
    err = ElementNotFoundError(selector="OKButton", window_title="MyApp")
    assert err.exit_code == EXIT_ELEMENT_NOT_FOUND
    assert "OKButton" in str(err)
    assert "MyApp" in str(err)
    assert "Hint" in str(err)


def test_element_not_found_error_no_window():
    err = ElementNotFoundError(selector="OKButton")
    assert err.exit_code == EXIT_ELEMENT_NOT_FOUND
    assert err.window_title == ""


def test_element_not_interactive_error():
    err = ElementNotInteractiveError(selector="SubmitBtn", reason="disabled")
    assert err.exit_code == EXIT_ELEMENT_NOT_INTERACTIVE
    assert "SubmitBtn" in str(err)
    assert "disabled" in str(err)
    assert "Hint" in str(err)


def test_element_not_interactive_error_no_reason():
    err = ElementNotInteractiveError(selector="SubmitBtn")
    assert "SubmitBtn" in str(err)
    # no trailing "()" for an empty reason
    assert "()" not in str(err)


def test_element_offscreen_error():
    err = ElementOffscreenError(selector="MyControl")
    assert err.exit_code == EXIT_ELEMENT_OFFSCREEN
    assert "MyControl" in str(err)
    assert "Hint" in str(err)


def test_ambiguous_target_error():
    err = AmbiguousTargetError(selector="Button", count=3)
    assert err.exit_code == EXIT_AMBIGUOUS_TARGET
    assert "3" in str(err)
    assert "Button" in str(err)
    assert "Hint" in str(err)


def test_targeting_timeout_error():
    err = TargetingTimeoutError(selector="Spinner", timeout=5.0)
    assert err.exit_code == EXIT_TIMEOUT
    assert "5.0" in str(err)
    assert "Spinner" in str(err)
    assert "Hint" in str(err)


def test_all_errors_are_subclasses_of_base():
    for cls in (
        ElementNotFoundError,
        ElementNotInteractiveError,
        ElementOffscreenError,
        AmbiguousTargetError,
        TargetingTimeoutError,
    ):
        assert issubclass(cls, WpfAutoTesterError)
