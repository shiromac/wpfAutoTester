"""Core UIA automation engine wrapping pywinauto."""

from __future__ import annotations

import re
from typing import Any

from pywinauto import Desktop
from pywinauto.controls.uiawrapper import UIAWrapper

from wpf_agent.constants import DEFAULT_DEPTH, MAX_CONTROLS
from wpf_agent.core.errors import (
    MultipleElementsFoundError,
    SelectorNotFoundError,
    TargetNotFoundError,
)
from wpf_agent.core.target import ResolvedTarget
from wpf_agent.uia.selector import Selector


class UIAEngine:
    """Stateless UIA operations against a resolved target."""

    # ------------------------------------------------------------------
    # Window management
    # ------------------------------------------------------------------

    @staticmethod
    def list_windows() -> list[dict[str, Any]]:
        desktop = Desktop(backend="uia")
        results = []
        for w in desktop.windows():
            try:
                results.append({
                    "title": w.window_text(),
                    "pid": w.process_id(),
                    "handle": w.handle,
                    "control_type": w.element_info.control_type,
                    "visible": w.is_visible(),
                    "rect": _rect_dict(w.rectangle()),
                })
            except Exception:
                continue
        return results

    @staticmethod
    def focus_window(target: ResolvedTarget) -> dict[str, Any]:
        win = _top_window(target)
        win.set_focus()
        return {"focused": True, "title": win.window_text()}

    @staticmethod
    def wait_window(target: ResolvedTarget, timeout_ms: int) -> dict[str, Any]:
        from wpf_agent.uia.waits import wait_until

        def _find():
            try:
                return _top_window(target)
            except Exception:
                return None

        win = wait_until(_find, timeout_ms=timeout_ms, message="Window not found")
        return {"found": True, "title": win.window_text(), "pid": target.pid}

    # ------------------------------------------------------------------
    # Control enumeration
    # ------------------------------------------------------------------

    @staticmethod
    def list_controls(
        target: ResolvedTarget,
        depth: int = DEFAULT_DEPTH,
        filter_type: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        win = _top_window(target)
        controls: list[dict[str, Any]] = []
        _walk(win, controls, depth=depth, current=0, filter_type=filter_type)
        if search:
            queries = [s.strip().lower() for s in search.split(",") if s.strip()]
            controls = [
                c for c in controls
                if any(
                    q in (c.get("automation_id") or "").lower()
                    or q in (c.get("name") or "").lower()
                    or q in (c.get("value") or "").lower()
                    for q in queries
                )
            ]
        return controls[:MAX_CONTROLS]

    # ------------------------------------------------------------------
    # Element actions
    # ------------------------------------------------------------------

    @staticmethod
    def click(target: ResolvedTarget, selector: Selector) -> dict[str, Any]:
        elem = _find_element(target, selector)
        elem.click_input()
        return {"clicked": True, "selector": selector.describe()}

    @staticmethod
    def type_text(
        target: ResolvedTarget,
        selector: Selector,
        text: str,
        clear: bool = True,
        method: str = "keyboard",
    ) -> dict[str, Any]:
        elem = _find_element(target, selector)
        if method == "value_pattern":
            if clear:
                elem.set_edit_text(text)
            else:
                elem.type_keys(text, with_spaces=True)
        else:
            # keyboard method — fires WPF TextChanged / bindings
            elem.click_input()
            if clear:
                elem.type_keys("^a", with_spaces=False)
            elem.type_keys(text, with_spaces=True)
        return {
            "typed": True,
            "selector": selector.describe(),
            "length": len(text),
            "method": method,
        }

    @staticmethod
    def send_keys(
        target: ResolvedTarget,
        keys: str,
        selector: Selector | None = None,
    ) -> dict[str, Any]:
        """Send keyboard keys (shortcuts, special keys) to the target.

        If *selector* is provided, the matching element is focused first.
        Otherwise the top window receives focus.
        *keys* uses pywinauto key notation, e.g. ``"{ENTER}"``, ``"^a"`` (Ctrl+A).
        """
        from pywinauto.keyboard import send_keys as _send_keys

        if selector and selector.to_find_kwargs():
            elem = _find_element(target, selector)
            elem.click_input()
        else:
            win = _top_window(target)
            win.set_focus()
        _send_keys(keys)
        return {"sent": True, "keys": keys}

    @staticmethod
    def select_combo(
        target: ResolvedTarget, selector: Selector, item_text: str
    ) -> dict[str, Any]:
        elem = _find_element(target, selector)
        elem.select(item_text)
        return {"selected": True, "item": item_text}

    @staticmethod
    def toggle(
        target: ResolvedTarget, selector: Selector, state: bool | None = None
    ) -> dict[str, Any]:
        elem = _find_element(target, selector)
        if state is None:
            elem.toggle()
        elif state:
            if not elem.get_toggle_state():
                elem.toggle()
        else:
            if elem.get_toggle_state():
                elem.toggle()
        return {
            "toggled": True,
            "new_state": bool(elem.get_toggle_state()),
        }

    # ------------------------------------------------------------------
    # State retrieval
    # ------------------------------------------------------------------

    @staticmethod
    def read_text(target: ResolvedTarget, selector: Selector) -> dict[str, Any]:
        elem = _find_element(target, selector)
        text = ""
        try:
            text = elem.window_text()
        except Exception:
            pass
        if not text:
            try:
                text = elem.get_value()
            except Exception:
                pass
        return {"text": text, "selector": selector.describe()}

    @staticmethod
    def get_state(target: ResolvedTarget, selector: Selector) -> dict[str, Any]:
        elem = _find_element(target, selector)
        state: dict[str, Any] = {
            "selector": selector.describe(),
            "enabled": elem.is_enabled(),
            "visible": elem.is_visible(),
        }
        try:
            state["value"] = elem.get_value()
        except Exception:
            state["value"] = None
        try:
            state["selected"] = elem.is_selected()
        except Exception:
            state["selected"] = None
        try:
            state["rect"] = _rect_dict(elem.rectangle())
        except Exception:
            state["rect"] = None
        return state

    @staticmethod
    def wait_for(
        target: ResolvedTarget,
        selector: Selector,
        condition: str,
        value: Any,
        timeout_ms: int,
    ) -> dict[str, Any]:
        from wpf_agent.uia.waits import wait_until

        # For text_changed: capture initial text before polling starts
        initial_text: str | None = None
        if condition == "text_changed":
            try:
                elem = _find_element(target, selector)
                initial_text = elem.window_text()
            except SelectorNotFoundError:
                initial_text = None

        def _check():
            try:
                elem = _find_element(target, selector)
            except SelectorNotFoundError:
                if condition == "exists":
                    return None
                raise
            if condition == "exists":
                return True
            if condition == "enabled":
                return elem.is_enabled() == value or None
            if condition == "visible":
                return elem.is_visible() == value or None
            if condition == "text_equals":
                t = elem.window_text()
                return (t == value) or None
            if condition == "text_contains":
                t = elem.window_text()
                return (value in t) or None
            if condition == "text_not_equals":
                t = elem.window_text()
                return (t != value) or None
            if condition == "text_changed":
                t = elem.window_text()
                return (t != initial_text) or None
            return True

        wait_until(
            _check, timeout_ms=timeout_ms, message=f"wait_for({condition}) failed"
        )
        return {"condition_met": True, "condition": condition}


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------


def _top_window(target: ResolvedTarget) -> UIAWrapper:
    """Get the main window for a target."""
    app = target.app
    try:
        if target.window_handle:
            return app.window(handle=target.window_handle)
        return app.top_window()
    except Exception as exc:
        raise TargetNotFoundError(f"Cannot get window for {target}: {exc}") from exc


def _find_element(target: ResolvedTarget, selector: Selector) -> UIAWrapper:
    """Find a single element matching the selector."""
    from pywinauto.findwindows import ElementAmbiguousError

    win = _top_window(target)
    kw = selector.to_find_kwargs()

    if not kw and selector.bounding_rect:
        # Coordinate fallback
        r = selector.bounding_rect
        cx = r["left"] + r.get("width", 0) // 2
        cy = r["top"] + r.get("height", 0) // 2
        from pywinauto import mouse
        mouse.click(coords=(cx, cy))
        # Return the window itself as a proxy
        return win

    if not kw:
        raise SelectorNotFoundError(f"Empty selector: {selector}")

    try:
        child = win.child_window(**kw)
        return child.wrapper_object()
    except ElementAmbiguousError:
        candidates = _enumerate_candidates(win, kw)
        raise MultipleElementsFoundError(selector.describe(), candidates)
    except Exception as exc:
        raise SelectorNotFoundError(
            f"Element not found: {selector.describe()} — {exc}"
        ) from exc


def _enumerate_candidates(
    win: UIAWrapper, find_kwargs: dict[str, Any]
) -> list[dict[str, Any]]:
    """List elements matching *find_kwargs* for error reporting."""
    try:
        children = win.child_window(**find_kwargs).find_all()
    except Exception:
        children = []
    results = []
    for child in children[:10]:
        info: dict[str, Any] = {
            "automation_id": child.element_info.automation_id or "",
            "name": child.window_text(),
            "control_type": child.element_info.control_type,
        }
        try:
            info["rect"] = _rect_dict(child.rectangle())
        except Exception:
            info["rect"] = None
        results.append(info)
    return results


def _walk(
    elem: UIAWrapper,
    out: list[dict[str, Any]],
    depth: int,
    current: int,
    filter_type: str | None,
) -> None:
    if current > depth or len(out) >= MAX_CONTROLS:
        return
    for child in elem.children():
        try:
            ct = child.element_info.control_type
            if filter_type and ct != filter_type:
                _walk(child, out, depth, current + 1, filter_type)
                continue
            info: dict[str, Any] = {
                "automation_id": child.element_info.automation_id or "",
                "name": child.window_text(),
                "control_type": ct,
                "enabled": child.is_enabled(),
                "visible": child.is_visible(),
            }
            try:
                info["rect"] = _rect_dict(child.rectangle())
            except Exception:
                info["rect"] = None
            try:
                info["value"] = child.get_value()
            except Exception:
                info["value"] = None
            out.append(info)
        except Exception:
            pass
        _walk(child, out, depth, current + 1, filter_type)


def _rect_dict(r) -> dict[str, int]:
    return {
        "left": r.left,
        "top": r.top,
        "right": r.right,
        "bottom": r.bottom,
        "width": r.width(),
        "height": r.height(),
    }
