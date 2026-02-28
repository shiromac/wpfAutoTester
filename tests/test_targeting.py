"""Tests for wpfautotester.targeting module (cross-platform, no real pywinauto)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from wpfautotester.errors import (
    AmbiguousTargetError,
    ElementNotFoundError,
    ElementNotInteractiveError,
    ElementOffscreenError,
    TargetingTimeoutError,
)


def _make_fake_pywinauto(matches=None, connect_raises=False):
    """Build a minimal fake pywinauto module for mocking."""
    fake = MagicMock()

    if connect_raises:
        fake.findwindows = MagicMock()
        fake.findwindows.ElementNotFoundError = ElementNotFoundError

        def bad_connect(title_re):
            raise fake.findwindows.ElementNotFoundError(
                selector="x", window_title=title_re
            )

        fake.Application.return_value.connect.side_effect = bad_connect
    else:
        window = MagicMock()
        if matches is not None:
            window.descendants.return_value = matches
        else:
            window.descendants.return_value = []
        fake.Application.return_value.connect.return_value = MagicMock()
        fake.Application.return_value.connect.return_value.top_window.return_value = (
            window
        )
        # Store for assertions
        fake._window = window

    return fake


@pytest.mark.skipif(sys.platform == "win32", reason="Mocked on Windows via pywinauto")
def test_find_element_raises_import_error_on_non_windows():
    """On non-Windows, calling find_element should raise ImportError."""
    from wpfautotester import targeting

    # Reset the cached module so the platform check runs fresh
    targeting._pywinauto = None

    with pytest.raises(ImportError, match="Windows"):
        targeting.find_element("MyApp", "OKButton")


def test_find_element_raises_element_not_found_when_connect_fails():
    """ElementNotFoundError when pywinauto can't connect to the window."""
    from wpfautotester import targeting

    fake_pw = MagicMock()
    fake_pw.findwindows = MagicMock()
    # Make connect raise a plain Exception to trigger the ElementNotFoundError path
    fake_pw.Application.return_value.connect.side_effect = Exception("no window")

    targeting._pywinauto = fake_pw

    with pytest.raises(ElementNotFoundError):
        targeting.find_element("NoSuchApp", "OKButton")

    targeting._pywinauto = None


def test_find_element_raises_ambiguous_when_multiple_matches():
    """AmbiguousTargetError when more than one element matches."""
    from wpfautotester import targeting

    el1, el2 = MagicMock(), MagicMock()
    fake_pw = _make_fake_pywinauto(matches=[el1, el2])
    targeting._pywinauto = fake_pw

    with pytest.raises(AmbiguousTargetError) as exc_info:
        targeting.find_element("MyApp", "Button", timeout=0.1)

    assert exc_info.value.count == 2
    targeting._pywinauto = None


def test_find_element_raises_timeout_when_no_matches():
    """TargetingTimeoutError when no element appears within the timeout."""
    from wpfautotester import targeting

    fake_pw = _make_fake_pywinauto(matches=[])
    targeting._pywinauto = fake_pw

    with pytest.raises(TargetingTimeoutError) as exc_info:
        targeting.find_element("MyApp", "GhostButton", timeout=0.1)

    assert exc_info.value.timeout == pytest.approx(0.1, abs=0.05)
    targeting._pywinauto = None


def test_find_element_raises_not_interactive_when_disabled():
    """ElementNotInteractiveError for a disabled element."""
    from wpfautotester import targeting

    element = MagicMock()
    element.rectangle.return_value = MagicMock(right=100, bottom=100)
    element.is_enabled.return_value = False
    element.is_visible.return_value = True

    fake_pw = _make_fake_pywinauto(matches=[element])
    targeting._pywinauto = fake_pw

    with pytest.raises(ElementNotInteractiveError):
        targeting.find_element("MyApp", "DisabledBtn", timeout=0.1)

    targeting._pywinauto = None


def test_find_element_raises_offscreen_when_rect_negative():
    """ElementOffscreenError for an element with a negative bounding rect."""
    from wpfautotester import targeting

    element = MagicMock()
    element.rectangle.return_value = MagicMock(right=-10, bottom=-10)

    fake_pw = _make_fake_pywinauto(matches=[element])
    targeting._pywinauto = fake_pw

    with pytest.raises(ElementOffscreenError):
        targeting.find_element("MyApp", "OffscreenEl", timeout=0.1)

    targeting._pywinauto = None


def test_find_element_succeeds_for_valid_element():
    """find_element returns the element when everything is fine."""
    from wpfautotester import targeting

    element = MagicMock()
    element.rectangle.return_value = MagicMock(right=200, bottom=200)
    element.is_enabled.return_value = True
    element.is_visible.return_value = True

    fake_pw = _make_fake_pywinauto(matches=[element])
    targeting._pywinauto = fake_pw

    result = targeting.find_element("MyApp", "GoodButton", timeout=0.5)
    assert result is element

    targeting._pywinauto = None
