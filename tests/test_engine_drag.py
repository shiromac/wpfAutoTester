"""Tests for UIAEngine.drag() — mocked to run without Windows."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch


def _make_mock_pywinauto():
    """Create a mock pywinauto module tree sufficient for importing engine."""
    pywinauto = types.ModuleType("pywinauto")
    pywinauto.Desktop = MagicMock()
    pywinauto.mouse = MagicMock()

    controls = types.ModuleType("pywinauto.controls")
    uiawrapper = types.ModuleType("pywinauto.controls.uiawrapper")
    uiawrapper.UIAWrapper = MagicMock()
    controls.uiawrapper = uiawrapper

    findwindows = types.ModuleType("pywinauto.findwindows")
    findwindows.ElementAmbiguousError = type("ElementAmbiguousError", (Exception,), {})

    pywinauto.controls = controls
    pywinauto.findwindows = findwindows

    return {
        "pywinauto": pywinauto,
        "pywinauto.controls": controls,
        "pywinauto.controls.uiawrapper": uiawrapper,
        "pywinauto.findwindows": findwindows,
        "pywinauto.mouse": pywinauto.mouse,
    }


# Patch pywinauto before importing engine
_mocks = _make_mock_pywinauto()
for name, mod in _mocks.items():
    sys.modules.setdefault(name, mod)

from wpf_agent.uia.selector import Selector  # noqa: E402


class _FakeRect:
    def __init__(self, left, top, right, bottom):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    def width(self):
        return self.right - self.left

    def height(self):
        return self.bottom - self.top


def test_drag_calls_mouse_press_move_release():
    """drag() should press at src centre, move to dst centre, release."""
    from wpf_agent.uia.engine import UIAEngine

    src_elem = MagicMock()
    src_elem.rectangle.return_value = _FakeRect(100, 200, 200, 300)

    dst_elem = MagicMock()
    dst_elem.rectangle.return_value = _FakeRect(400, 500, 500, 600)

    target = MagicMock()

    with patch("wpf_agent.uia.engine._find_element") as mock_find, \
         patch("pywinauto.mouse") as mock_mouse:
        mock_find.side_effect = [src_elem, dst_elem]

        src_sel = Selector(automation_id="SrcItem")
        dst_sel = Selector(automation_id="DstItem")
        result = UIAEngine.drag(target, src_sel, dst_sel)

    assert result["dragged"] is True
    assert result["src_point"] == {"x": 150, "y": 250}
    assert result["dst_point"] == {"x": 450, "y": 550}
    assert "SrcItem" in result["src_selector"]
    assert "DstItem" in result["dst_selector"]

    mock_mouse.press.assert_called_once_with(coords=(150, 250))
    mock_mouse.move.assert_called_once_with(coords=(450, 550))
    mock_mouse.release.assert_called_once_with(coords=(450, 550))


def test_drag_result_shape():
    """drag() result must contain expected keys."""
    from wpf_agent.uia.engine import UIAEngine

    elem = MagicMock()
    elem.rectangle.return_value = _FakeRect(0, 0, 100, 100)

    target = MagicMock()

    with patch("wpf_agent.uia.engine._find_element", return_value=elem), \
         patch("pywinauto.mouse"):
        result = UIAEngine.drag(
            target,
            Selector(automation_id="A"),
            Selector(automation_id="B"),
        )

    expected_keys = {"dragged", "src_selector", "dst_selector", "src_point", "dst_point"}
    assert expected_keys == set(result.keys())
