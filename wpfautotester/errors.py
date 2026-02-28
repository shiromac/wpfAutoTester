"""Exit codes and error message helpers for wpfautotester."""

# Exit codes
EXIT_OK = 0
EXIT_GENERAL_ERROR = 1
EXIT_ELEMENT_NOT_FOUND = 2
EXIT_ELEMENT_NOT_INTERACTIVE = 3
EXIT_ELEMENT_OFFSCREEN = 4
EXIT_AMBIGUOUS_TARGET = 5
EXIT_TIMEOUT = 6
EXIT_DOCTOR_FAILURE = 10

# Human-readable descriptions keyed by exit code
_EXIT_DESCRIPTIONS = {
    EXIT_OK: "Success",
    EXIT_GENERAL_ERROR: "General error",
    EXIT_ELEMENT_NOT_FOUND: "UI element not found",
    EXIT_ELEMENT_NOT_INTERACTIVE: "UI element is not interactive (disabled or hidden)",
    EXIT_ELEMENT_OFFSCREEN: "UI element is off-screen or obscured",
    EXIT_AMBIGUOUS_TARGET: "Ambiguous target — multiple elements matched the selector",
    EXIT_TIMEOUT: "Operation timed out waiting for the UI element",
    EXIT_DOCTOR_FAILURE: "Environment check failed (run `wpfautotester doctor` for details)",
}


def exit_description(code: int) -> str:
    """Return a human-readable description for *code*."""
    return _EXIT_DESCRIPTIONS.get(code, f"Unknown error (code {code})")


class WpfAutoTesterError(Exception):
    """Base exception; carries an exit code and an actionable message."""

    def __init__(self, message: str, exit_code: int = EXIT_GENERAL_ERROR):
        super().__init__(message)
        self.exit_code = exit_code


class ElementNotFoundError(WpfAutoTesterError):
    """Raised when the requested UI element cannot be located."""

    def __init__(self, selector: str, window_title: str = ""):
        hint = (
            f"  Hint: Verify the selector '{selector}' in Inspect.exe or"
            " UISpy and ensure the target window is in the foreground."
        )
        window_part = f" in window '{window_title}'" if window_title else ""
        msg = (
            f"Element not found{window_part}: no element matched selector '{selector}'.\n{hint}"
        )
        super().__init__(msg, EXIT_ELEMENT_NOT_FOUND)
        self.selector = selector
        self.window_title = window_title


class ElementNotInteractiveError(WpfAutoTesterError):
    """Raised when the element exists but cannot be interacted with."""

    def __init__(self, selector: str, reason: str = ""):
        reason_part = f" ({reason})" if reason else ""
        hint = (
            f"  Hint: The element matched selector '{selector}' but is disabled or hidden."
            " Check application state before interacting."
        )
        msg = f"Element not interactive{reason_part}: '{selector}'.\n{hint}"
        super().__init__(msg, EXIT_ELEMENT_NOT_INTERACTIVE)
        self.selector = selector


class ElementOffscreenError(WpfAutoTesterError):
    """Raised when the element is off-screen or obscured by another window."""

    def __init__(self, selector: str):
        hint = (
            f"  Hint: Scroll or resize the application window so that"
            f" '{selector}' is fully visible before interacting."
        )
        msg = f"Element off-screen or obscured: '{selector}'.\n{hint}"
        super().__init__(msg, EXIT_ELEMENT_OFFSCREEN)
        self.selector = selector


class AmbiguousTargetError(WpfAutoTesterError):
    """Raised when more than one element matches the given selector."""

    def __init__(self, selector: str, count: int):
        hint = (
            f"  Hint: Refine selector '{selector}' with an index, unique automation ID,"
            " or a narrower control-type filter."
        )
        msg = f"Ambiguous target: {count} elements matched selector '{selector}'.\n{hint}"
        super().__init__(msg, EXIT_AMBIGUOUS_TARGET)
        self.selector = selector
        self.count = count


class TargetingTimeoutError(WpfAutoTesterError):
    """Raised when waiting for an element times out."""

    def __init__(self, selector: str, timeout: float):
        hint = (
            "  Hint: Increase the timeout, or confirm the application is running"
            " and the window is visible."
        )
        msg = (
            f"Timeout after {timeout:.1f}s waiting for element '{selector}'.\n{hint}"
        )
        super().__init__(msg, EXIT_TIMEOUT)
        self.selector = selector
        self.timeout = timeout
