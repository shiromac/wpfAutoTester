"""AI-free replay from recorded action sequences."""

from __future__ import annotations

import json
import pathlib
import time
from typing import Any

from wpf_agent.core.errors import ReplayError
from wpf_agent.core.session import Session
from wpf_agent.core.target import ResolvedTarget, TargetRegistry
from wpf_agent.runner.logging import StepLogger
from wpf_agent.uia.engine import UIAEngine
from wpf_agent.uia.selector import Selector


def load_actions(path: pathlib.Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def replay_actions(
    actions: list[dict[str, Any]],
    target: ResolvedTarget,
    session: Session | None = None,
    step_delay_ms: int = 100,
) -> list[dict[str, Any]]:
    """Replay a list of recorded actions without AI.

    Returns a list of step results.
    """
    if session is None:
        session = Session()
        session.start()

    logger = StepLogger(session)
    logger.open()
    results = []

    try:
        for i, action_rec in enumerate(actions):
            step = session.next_step()
            action = action_rec["action"]
            args = action_rec.get("args", {})

            try:
                result = _execute_action(target, action, args)
                logger.log_step(step, action, args, result=result)
                results.append({"step": step, "action": action, "result": result})
            except Exception as exc:
                logger.log_step(step, action, args, error=str(exc))
                results.append({"step": step, "action": action, "error": str(exc)})

            if step_delay_ms > 0:
                time.sleep(step_delay_ms / 1000.0)
    finally:
        logger.close()

    return results


def _execute_action(
    target: ResolvedTarget, action: str, args: dict[str, Any]
) -> dict[str, Any]:
    """Execute a single action."""
    selector_data = args.get("selector")
    selector = Selector(**selector_data) if selector_data else None

    if action == "click":
        if selector is None:
            raise ReplayError("click requires a selector")
        return UIAEngine.click(target, selector)

    elif action == "type_text":
        if selector is None:
            raise ReplayError("type_text requires a selector")
        return UIAEngine.type_text(
            target, selector, args.get("text", ""), clear=args.get("clear", True)
        )

    elif action == "select_combo":
        if selector is None:
            raise ReplayError("select_combo requires a selector")
        return UIAEngine.select_combo(target, selector, args.get("item_text", ""))

    elif action == "toggle":
        if selector is None:
            raise ReplayError("toggle requires a selector")
        return UIAEngine.toggle(target, selector, args.get("state"))

    elif action == "focus_window":
        return UIAEngine.focus_window(target)

    elif action == "wait_for":
        if selector is None:
            raise ReplayError("wait_for requires a selector")
        return UIAEngine.wait_for(
            target,
            selector,
            args.get("condition", "exists"),
            args.get("value", True),
            args.get("timeout_ms", 10000),
        )

    elif action == "read_text":
        if selector is None:
            raise ReplayError("read_text requires a selector")
        return UIAEngine.read_text(target, selector)

    elif action == "get_state":
        if selector is None:
            raise ReplayError("get_state requires a selector")
        return UIAEngine.get_state(target, selector)

    elif action == "screenshot":
        from wpf_agent.uia.screenshot import capture_screenshot
        path = capture_screenshot(target=target, save_path=session.screenshot_path())
        return {"path": str(path)}

    elif action == "list_controls":
        return {
            "controls": UIAEngine.list_controls(
                target, depth=args.get("depth", 4), filter_type=args.get("filter")
            )
        }

    elif action == "list_windows":
        return {"windows": UIAEngine.list_windows()}

    else:
        raise ReplayError(f"Unknown action: {action}")
