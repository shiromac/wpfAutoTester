"""Failure oracles — detect crashes, freezes, exceptions, and invariant violations."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import psutil

from wpf_agent.core.target import ResolvedTarget
from wpf_agent.uia.engine import UIAEngine
from wpf_agent.uia.selector import Selector


@dataclass
class OracleVerdict:
    failed: bool
    reason: str
    details: dict[str, Any] | None = None


def check_process_alive(target: ResolvedTarget) -> OracleVerdict:
    """Check if the target process is still running."""
    if not target.is_alive:
        return OracleVerdict(True, "Process terminated", {"pid": target.pid})
    return OracleVerdict(False, "Process alive")


def check_responsive(target: ResolvedTarget, timeout_ms: int = 5000) -> OracleVerdict:
    """Check if the app responds within timeout (UI freeze detection)."""
    try:
        start = time.monotonic()
        UIAEngine.list_controls(target, depth=1)
        elapsed = (time.monotonic() - start) * 1000
        if elapsed > timeout_ms:
            return OracleVerdict(
                True, f"UI freeze: response took {elapsed:.0f}ms", {"elapsed_ms": elapsed}
            )
        return OracleVerdict(False, "Responsive")
    except Exception as exc:
        return OracleVerdict(True, f"UI unresponsive: {exc}")


def check_error_dialogs(target: ResolvedTarget) -> OracleVerdict:
    """Scan for common error/exception dialogs."""
    error_patterns = [
        "exception", "error", "fatal", "unhandled", "crash",
        "stopped working", "not responding",
    ]
    try:
        controls = UIAEngine.list_controls(target, depth=3)
        for ctrl in controls:
            text = (ctrl.get("name", "") or "").lower()
            for pat in error_patterns:
                if pat in text:
                    return OracleVerdict(
                        True,
                        f"Error dialog detected: {ctrl.get('name', '')}",
                        {"control": ctrl},
                    )
    except Exception:
        pass
    return OracleVerdict(False, "No error dialogs found")


def check_element_exists(
    target: ResolvedTarget, selector: Selector
) -> OracleVerdict:
    """Verify that an expected element exists in the UIA tree."""
    try:
        from wpf_agent.uia.engine import _find_element
        _find_element(target, selector)
        return OracleVerdict(False, "Element exists")
    except Exception:
        return OracleVerdict(
            True,
            f"Expected element missing: {selector.describe()}",
            {"selector": selector.describe()},
        )


def run_all_oracles(
    target: ResolvedTarget,
    invariants: list[dict[str, Any]] | None = None,
) -> list[OracleVerdict]:
    """Run all oracles and return verdicts. Any failed = defect detected."""
    verdicts = [
        check_process_alive(target),
        check_responsive(target),
        check_error_dialogs(target),
    ]

    if invariants:
        for inv in invariants:
            sel = Selector(**inv.get("selector", {}))
            verdicts.append(check_element_exists(target, sel))

    return verdicts
