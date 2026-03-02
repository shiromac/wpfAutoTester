"""Build-then-verify: launch an app, run smoke tests, check elements, run interactions."""

from __future__ import annotations

import json
import pathlib
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

import psutil
import yaml

from wpf_agent.core.errors import SelectorNotFoundError, TargetNotFoundError
from wpf_agent.core.session import Session
from wpf_agent.core.target import (
    ResolvedTarget,
    TargetRegistry,
    record_launched_pid,
    remove_launched_pid,
)
from wpf_agent.runner.logging import StepLogger
from wpf_agent.testing.assertions import AssertionResult, check_assertion
from wpf_agent.testing.oracles import (
    check_error_dialogs,
    check_process_alive,
    check_responsive,
)
from wpf_agent.uia.engine import UIAEngine
from wpf_agent.uia.screenshot import capture_screenshot
from wpf_agent.uia.selector import Selector
from wpf_agent.uia.snapshot import capture_snapshot, save_snapshot


# ── Data classes ─────────────────────────────────────────────────


@dataclass
class VerifyConfig:
    """Configuration for a verification run."""

    exe: str = ""
    args: list[str] = field(default_factory=list)
    cwd: str | None = None
    title_re: str = ""
    startup_wait_ms: int = 5000
    expected_controls: list[dict[str, Any]] = field(default_factory=list)
    interactions: list[dict[str, Any]] = field(default_factory=list)
    auto_close: bool = True

    @classmethod
    def from_file(cls, path: pathlib.Path) -> VerifyConfig:
        """Load from a verification-spec YAML file."""
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        app = raw.get("app", {})
        return cls(
            exe=app.get("exe", ""),
            args=app.get("args", []),
            cwd=app.get("cwd"),
            title_re=app.get("title_re", ""),
            startup_wait_ms=app.get("startup_wait_ms", 5000),
            expected_controls=raw.get("expected_controls", []),
            interactions=raw.get("interactions", []),
            auto_close=app.get("auto_close", True),
        )


@dataclass
class VerifyCheck:
    """Result of a single verification check."""

    name: str
    passed: bool
    message: str
    details: dict[str, Any] | None = None


@dataclass
class VerifyResult:
    """Aggregate result of a verification run."""

    passed: bool
    checks: list[VerifyCheck] = field(default_factory=list)
    session_id: str = ""
    screenshot_path: str | None = None
    controls_found: int = 0
    pid: int | None = None


# ── Main entry point ─────────────────────────────────────────────


def run_verify(
    config: VerifyConfig,
    session: Session | None = None,
) -> VerifyResult:
    """Execute the full verification flow.

    Phase 1 — Launch the application
    Phase 2 — Smoke tests  (always)
    Phase 3 — Element verification  (if expected_controls given)
    Phase 4 — Interaction tests  (if interactions given)
    Phase 5 — Cleanup
    """
    if session is None:
        session = Session()
    session.start()

    logger = StepLogger(session)
    logger.open()

    checks: list[VerifyCheck] = []
    pid: int | None = None
    target: ResolvedTarget | None = None
    last_screenshot: str | None = None
    controls_found = 0

    try:
        # ── Phase 1: Launch ──────────────────────────────────────
        pid = _launch_app(config.exe, config.args, config.cwd)
        time.sleep(config.startup_wait_ms / 1000.0)

        alive = psutil.pid_exists(pid)
        checks.append(VerifyCheck(
            name="app_launches",
            passed=alive,
            message="Process alive" if alive else "Process exited during startup",
            details={"pid": pid},
        ))

        step = session.next_step()
        logger.log_step(step, "launch", {"exe": config.exe, "pid": pid},
                        result={"alive": alive})

        if not alive:
            return _build_result(checks, session, last_screenshot, controls_found, pid)

        # Resolve target
        target = _find_target(pid, config.title_re, config.startup_wait_ms)

        # ── Phase 2: Smoke tests ─────────────────────────────────
        smoke_checks, controls_found, last_screenshot = _run_smoke_checks(
            target, session, logger,
        )
        checks.extend(smoke_checks)

        # ── Phase 3: Element verification ────────────────────────
        if config.expected_controls:
            elem_checks = _run_element_checks(target, config.expected_controls)
            checks.extend(elem_checks)

            step = session.next_step()
            logger.log_step(step, "element_checks", {},
                            result={"count": len(elem_checks),
                                    "passed": sum(1 for c in elem_checks if c.passed)})

        # ── Phase 4: Interaction tests ───────────────────────────
        if config.interactions:
            int_checks = _run_interaction_checks(
                target, config.interactions, session, logger,
            )
            checks.extend(int_checks)

    except Exception as exc:
        checks.append(VerifyCheck(
            name="unexpected_error",
            passed=False,
            message=str(exc),
        ))
    finally:
        # ── Phase 5: Cleanup ─────────────────────────────────────
        if config.auto_close and pid is not None:
            _terminate_app(pid)

        logger.close()

    return _build_result(checks, session, last_screenshot, controls_found, pid)


# ── Helper functions ─────────────────────────────────────────────


def _build_result(
    checks: list[VerifyCheck],
    session: Session,
    last_screenshot: str | None,
    controls_found: int,
    pid: int | None = None,
) -> VerifyResult:
    all_passed = all(c.passed for c in checks)
    return VerifyResult(
        passed=all_passed,
        checks=checks,
        session_id=session.session_id,
        screenshot_path=last_screenshot,
        controls_found=controls_found,
        pid=pid,
    )


def _launch_app(exe: str, args: list[str], cwd: str | None) -> int:
    """Start the application and return its PID."""
    cmd = [exe] + args
    proc = subprocess.Popen(cmd, cwd=cwd)
    record_launched_pid(proc.pid, exe)
    return proc.pid


def _find_target(
    pid: int, title_re: str, timeout_ms: int,
) -> ResolvedTarget:
    """Resolve a ResolvedTarget from a PID, optionally matching title_re."""
    registry = TargetRegistry.get_instance()

    if title_re:
        # Try title-based resolution with retries
        deadline = time.monotonic() + timeout_ms / 1000.0
        last_err: Exception | None = None
        while time.monotonic() < deadline:
            try:
                _, target = registry.resolve({"title_re": title_re})
                if target.pid == pid:
                    return target
            except TargetNotFoundError as exc:
                last_err = exc
            time.sleep(0.5)
        # Fall through to PID-based if title never matched
        if last_err:
            pass  # will try PID below

    _, target = registry.resolve({"pid": pid})
    return target


def _run_smoke_checks(
    target: ResolvedTarget,
    session: Session,
    logger: StepLogger,
) -> tuple[list[VerifyCheck], int, str | None]:
    """Run standard smoke tests: window visible, responsive, no error dialogs."""
    checks: list[VerifyCheck] = []
    controls_found = 0
    last_screenshot: str | None = None

    # Check window visible
    try:
        UIAEngine.focus_window(target)
        checks.append(VerifyCheck(
            name="window_visible",
            passed=True,
            message="Window is visible and focusable",
        ))
    except Exception as exc:
        checks.append(VerifyCheck(
            name="window_visible",
            passed=False,
            message=f"Cannot focus window: {exc}",
        ))

    # Check responsive (list_controls succeeds)
    verdict = check_responsive(target)
    checks.append(VerifyCheck(
        name="responsive",
        passed=not verdict.failed,
        message=verdict.reason,
        details=verdict.details,
    ))

    # Check no error dialogs
    verdict = check_error_dialogs(target)
    checks.append(VerifyCheck(
        name="no_error_dialogs",
        passed=not verdict.failed,
        message=verdict.reason,
        details=verdict.details,
    ))

    # Capture screenshot
    step = session.next_step()
    try:
        ss_path = capture_screenshot(target, save_path=session.screenshot_path(step))
        last_screenshot = str(ss_path)
    except Exception:
        last_screenshot = None

    # Capture UIA snapshot
    try:
        snapshot = capture_snapshot(target)
        controls_found = len(snapshot)
        save_snapshot(snapshot, session.uia_snapshot_path(step))
    except Exception:
        pass

    logger.log_step(
        step, "smoke_test", {},
        result={"checks": [c.name for c in checks], "controls_found": controls_found},
        screenshot_path=last_screenshot,
        uia_snapshot_path=str(session.uia_snapshot_path(step)),
    )

    return checks, controls_found, last_screenshot


def _run_element_checks(
    target: ResolvedTarget,
    expected_controls: list[dict[str, Any]],
) -> list[VerifyCheck]:
    """Verify expected UI elements exist with correct state."""
    checks: list[VerifyCheck] = []

    for spec in expected_controls:
        selector_dict = spec.get("selector", {})
        selector = Selector(**selector_dict)
        expects = spec.get("expect", {})
        name = selector.describe()

        # Check existence first
        if expects.get("exists", True):
            result = check_assertion(target, selector, "exists")
            if not result.passed:
                checks.append(VerifyCheck(
                    name=f"element_{name}",
                    passed=False,
                    message=f"Element not found: {name}",
                    details={"selector": selector_dict},
                ))
                continue

        # Check additional state properties
        for prop, value in expects.items():
            if prop == "exists":
                continue

            assertion_type = prop
            if prop == "text":
                assertion_type = "text_equals"

            result = check_assertion(target, selector, assertion_type, expected=value)
            checks.append(VerifyCheck(
                name=f"element_{name}_{prop}",
                passed=result.passed,
                message=result.message,
                details={"selector": selector_dict, "expected": value,
                         "actual": result.actual},
            ))

        # If only exists was checked (and passed), add a pass entry
        if set(expects.keys()) <= {"exists"}:
            checks.append(VerifyCheck(
                name=f"element_{name}",
                passed=True,
                message=f"Element exists: {name}",
                details={"selector": selector_dict},
            ))

    return checks


def _run_interaction_checks(
    target: ResolvedTarget,
    interactions: list[dict[str, Any]],
    session: Session,
    logger: StepLogger,
) -> list[VerifyCheck]:
    """Execute interaction steps and verify post-conditions."""
    checks: list[VerifyCheck] = []

    for interaction in interactions:
        int_name = interaction.get("name", "interaction")
        action = interaction.get("action", "")
        selector_dict = interaction.get("selector", {})
        selector = Selector(**selector_dict)

        step = session.next_step()

        # Execute the action
        try:
            if action == "click":
                UIAEngine.click(target, selector)
            elif action == "type_text":
                text = interaction.get("text", "")
                clear = interaction.get("clear", True)
                UIAEngine.type_text(target, selector, text, clear=clear)
            elif action == "select_combo":
                item = interaction.get("item_text", "")
                UIAEngine.select_combo(target, selector, item)
            elif action == "toggle":
                state = interaction.get("state")
                UIAEngine.toggle(target, selector, state=state)
            else:
                checks.append(VerifyCheck(
                    name=int_name,
                    passed=False,
                    message=f"Unknown action: {action}",
                ))
                continue

            # Small delay for UI to settle
            time.sleep(0.5)

        except Exception as exc:
            checks.append(VerifyCheck(
                name=int_name,
                passed=False,
                message=f"Action failed: {exc}",
                details={"action": action, "selector": selector_dict},
            ))
            logger.log_step(step, action, {"selector": selector_dict},
                            error=str(exc))
            continue

        # Take screenshot after action
        try:
            ss_path = capture_screenshot(target, save_path=session.screenshot_path(step))
            ss_str = str(ss_path)
        except Exception:
            ss_str = None

        # Check post-conditions
        after_specs = interaction.get("after", [])
        action_passed = True
        for after in after_specs:
            after_sel_dict = after.get("selector", selector_dict)
            after_sel = Selector(**after_sel_dict)
            after_expect = after.get("expect", {})

            for prop, value in after_expect.items():
                assertion_type = prop
                if prop == "text":
                    assertion_type = "text_equals"

                result = check_assertion(
                    target, after_sel, assertion_type, expected=value,
                )
                if not result.passed:
                    action_passed = False

                checks.append(VerifyCheck(
                    name=f"{int_name}_{prop}",
                    passed=result.passed,
                    message=result.message,
                    details={
                        "selector": after_sel_dict,
                        "expected": value,
                        "actual": result.actual,
                    },
                ))

        if not after_specs:
            # No post-conditions — just check the action didn't crash
            checks.append(VerifyCheck(
                name=int_name,
                passed=True,
                message=f"Action {action} executed successfully",
            ))

        logger.log_step(
            step, action, {"selector": selector_dict, "name": int_name},
            result={"passed": action_passed},
            screenshot_path=ss_str,
        )

    return checks


def _terminate_app(pid: int) -> None:
    """Gracefully terminate, then force-kill if needed."""
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except psutil.TimeoutExpired:
            proc.kill()
    except psutil.NoSuchProcess:
        pass
    remove_launched_pid(pid)
