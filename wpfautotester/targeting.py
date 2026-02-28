"""UI element targeting helpers with improved error messages and exit codes.

On non-Windows platforms the pywinauto import is skipped gracefully so that
unit tests and the doctor CLI can run on any OS.
"""

from __future__ import annotations

import sys
import time
from typing import Any, Optional

from .errors import (
    AmbiguousTargetError,
    ElementNotFoundError,
    ElementNotInteractiveError,
    ElementOffscreenError,
    TargetingTimeoutError,
)

# pywinauto is a Windows-only dependency.  Import it lazily so the package
# remains importable on Linux/macOS (e.g. in CI lint/test jobs).
_pywinauto: Any = None


def _get_pywinauto() -> Any:
    global _pywinauto
    if _pywinauto is None:
        if sys.platform != "win32":
            raise ImportError(
                "pywinauto is only available on Windows. "
                "UI automation cannot run on this platform."
            )
        import pywinauto  # noqa: PLC0415

        _pywinauto = pywinauto
    return _pywinauto


def find_element(
    window_title: str,
    selector: str,
    *,
    timeout: float = 10.0,
    backend: str = "uia",
) -> Any:
    """Return the first UI element matching *selector* inside *window_title*.

    Parameters
    ----------
    window_title:
        Title (or substring) of the top-level WPF window.
    selector:
        A ``best_match`` control-type string such as ``"OKButton"`` or a
        ``auto_id`` value like ``"btnOK"``.
    timeout:
        Maximum seconds to wait for the element to appear.
    backend:
        pywinauto backend — ``"uia"`` (default) or ``"win32"``.

    Raises
    ------
    ElementNotFoundError
        When no element matches within *timeout* seconds.
    AmbiguousTargetError
        When more than one element matches *selector*.
    ElementNotInteractiveError
        When the element is disabled or not visible.
    ElementOffscreenError
        When the element exists but is outside the visible viewport.
    TargetingTimeoutError
        When the element does not appear within *timeout* seconds.
    """
    pywinauto = _get_pywinauto()

    try:
        app = pywinauto.Application(backend=backend).connect(title_re=window_title)
    except Exception:
        raise ElementNotFoundError(selector=selector, window_title=window_title)

    window = app.top_window()
    deadline = time.monotonic() + timeout

    while True:
        try:
            matches = window.descendants(best_match=selector)
        except Exception:
            matches = []

        if len(matches) == 1:
            element = matches[0]
            _assert_interactive(element, selector)
            return element

        if len(matches) > 1:
            raise AmbiguousTargetError(selector=selector, count=len(matches))

        if time.monotonic() >= deadline:
            raise TargetingTimeoutError(selector=selector, timeout=timeout)

        time.sleep(0.25)


def _assert_interactive(element: Any, selector: str) -> None:
    """Raise if *element* cannot be interacted with."""
    try:
        rect = element.rectangle()
    except Exception:
        rect = None

    # Off-screen check: element rectangle fully outside the screen.
    if rect is not None:
        if rect.right <= 0 or rect.bottom <= 0:
            raise ElementOffscreenError(selector=selector)

    try:
        enabled = element.is_enabled()
        visible = element.is_visible()
    except Exception:
        return

    if not enabled:
        raise ElementNotInteractiveError(selector=selector, reason="disabled")
    if not visible:
        raise ElementNotInteractiveError(selector=selector, reason="not visible")


def click_element(
    window_title: str,
    selector: str,
    *,
    timeout: float = 10.0,
    backend: str = "uia",
) -> None:
    """Find and click the UI element identified by *selector*.

    Wraps :func:`find_element` — all its exceptions propagate unchanged.
    """
    element = find_element(
        window_title, selector, timeout=timeout, backend=backend
    )
    element.click_input()


def set_text(
    window_title: str,
    selector: str,
    text: str,
    *,
    timeout: float = 10.0,
    backend: str = "uia",
) -> None:
    """Clear and type *text* into the element identified by *selector*."""
    element = find_element(
        window_title, selector, timeout=timeout, backend=backend
    )
    element.set_edit_text(text)


def get_text(
    window_title: str,
    selector: str,
    *,
    timeout: float = 10.0,
    backend: str = "uia",
) -> Optional[str]:
    """Return the text content of the element identified by *selector*."""
    element = find_element(
        window_title, selector, timeout=timeout, backend=backend
    )
    return element.window_text()
