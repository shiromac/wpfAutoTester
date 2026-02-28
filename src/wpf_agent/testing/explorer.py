"""AI-guided exploratory tester using Claude Vision."""

from __future__ import annotations

import base64
import json
import pathlib
import time
from dataclasses import dataclass, field
from typing import Any

import yaml

from wpf_agent.config import SafetyConfig
from wpf_agent.core.safety import is_destructive
from wpf_agent.core.session import Session
from wpf_agent.core.target import ResolvedTarget
from wpf_agent.runner.logging import ActionRecorder, StepLogger
from wpf_agent.testing.oracles import run_all_oracles
from wpf_agent.uia.engine import UIAEngine
from wpf_agent.uia.screenshot import capture_screenshot
from wpf_agent.uia.selector import Selector
from wpf_agent.uia.snapshot import capture_snapshot, save_snapshot


@dataclass
class ExploreConfig:
    max_steps: int = 50
    goal: str = ""
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    step_delay_ms: int = 100
    oracle_interval: int = 5
    model: str = "claude-sonnet-4-20250514"
    history_window: int = 10
    invariants: list[dict[str, Any]] = field(default_factory=list)
    profile: str = ""

    @classmethod
    def from_file(cls, path: pathlib.Path) -> ExploreConfig:
        """Load ExploreConfig from a YAML file."""
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))

        safety = SafetyConfig()
        if "safety" in raw:
            safety = SafetyConfig(**raw["safety"])

        return cls(
            max_steps=raw.get("max_steps", 50),
            goal=raw.get("goal", ""),
            safety=safety,
            step_delay_ms=raw.get("step_delay_ms", 100),
            oracle_interval=raw.get("oracle_interval", 5),
            model=raw.get("model", "claude-sonnet-4-20250514"),
            history_window=raw.get("history_window", 10),
            invariants=raw.get("invariants", []),
            profile=raw.get("profile", ""),
        )


@dataclass
class ExploreTestResult:
    steps_run: int = 0
    failures: list[dict[str, Any]] = field(default_factory=list)
    session_id: str = ""
    passed: bool = True


# -- Tool definition for Claude tool_use --

_ACTION_TOOL = {
    "name": "perform_action",
    "description": (
        "Execute a single UI action on the application under test. "
        "Choose the best action based on the screenshot and control list."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["click", "type_text", "toggle", "select_combo", "read_text", "done"],
                "description": "The UI action to perform.",
            },
            "selector": {
                "type": "object",
                "description": "Identifies the target UI element.",
                "properties": {
                    "automation_id": {"type": "string"},
                    "name": {"type": "string"},
                    "control_type": {"type": "string"},
                },
            },
            "text": {
                "type": "string",
                "description": "Text to type (only for type_text action).",
            },
            "reasoning": {
                "type": "string",
                "description": "Why you chose this action.",
            },
        },
        "required": ["action", "selector", "reasoning"],
    },
}


def _build_system_prompt(goal: str) -> str:
    """Build the system prompt for the LLM."""
    goal_line = f"\n目標: {goal}" if goal else ""
    return (
        "あなたはWPF UIの探索テスターです。\n"
        "スクリーンショットとUI要素一覧を見て、次に実行すべき操作を1つ決定してください。\n\n"
        "ルール:\n"
        "- まだ操作していない要素を優先してください\n"
        "- エラーダイアログが出たら reasoning に詳細を報告してください\n"
        "- 破壊的操作（閉じる、削除、終了）は避けてください\n"
        "- 同じ操作の繰り返しを避け、幅広く探索してください\n"
        "- すべての画面・機能を一通り試すことを目指してください\n"
        "- 探索が完了したと判断したら action='done' を使ってください\n"
        f"{goal_line}"
    )


def _build_user_content(
    screenshot_b64: str,
    controls: list[dict[str, Any]],
    history: list[dict[str, Any]],
    step: int,
    max_steps: int,
) -> list[dict[str, Any]]:
    """Build the user message content with image + text."""
    # Summarize controls to reduce tokens
    controls_summary = []
    for c in controls:
        entry: dict[str, Any] = {}
        if c.get("automation_id"):
            entry["automation_id"] = c["automation_id"]
        if c.get("name"):
            entry["name"] = c["name"]
        if c.get("control_type"):
            entry["control_type"] = c["control_type"]
        if c.get("is_enabled") is not None:
            entry["enabled"] = c["is_enabled"]
        if entry:
            controls_summary.append(entry)

    # Summarize history
    history_text = ""
    if history:
        lines = []
        for h in history:
            line = f"Step {h.get('step')}: {h.get('action')}"
            if h.get('selector'):
                line += f" on {h['selector']}"
            if h.get('reasoning'):
                line += f" — {h['reasoning']}"
            if h.get('error'):
                line += f" [ERROR: {h['error']}]"
            lines.append(line)
        history_text = "\n".join(lines)

    text_parts = [
        f"ステップ {step}/{max_steps}",
        "",
        "=== UI要素一覧 ===",
        json.dumps(controls_summary, ensure_ascii=False, indent=1),
    ]

    if history_text:
        text_parts.extend(["", "=== 操作履歴 ===", history_text])

    text_parts.extend(["", "次に実行すべき操作を perform_action ツールで指定してください。"])

    return [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": screenshot_b64,
            },
        },
        {
            "type": "text",
            "text": "\n".join(text_parts),
        },
    ]


def _resize_screenshot(path: pathlib.Path, max_size: int = 1024) -> bytes:
    """Load and resize a screenshot to limit token usage, return PNG bytes."""
    from PIL import Image
    import io

    img = Image.open(path)
    w, h = img.size
    if max(w, h) > max_size:
        ratio = max_size / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _parse_llm_response(response: Any) -> dict[str, Any]:
    """Extract the perform_action tool call from the LLM response."""
    for block in response.content:
        if block.type == "tool_use" and block.name == "perform_action":
            return block.input
    # Fallback: if no tool_use found, return done
    return {"action": "done", "selector": {}, "reasoning": "No tool_use in response"}


def run_explore_test(
    target: ResolvedTarget,
    config: ExploreConfig,
    session: Session | None = None,
) -> ExploreTestResult:
    """Run an AI-guided exploration test."""
    import anthropic

    client = anthropic.Anthropic()

    if session is None:
        session = Session()
    session.start()

    logger = StepLogger(session)
    recorder = ActionRecorder(session)
    logger.open()

    result = ExploreTestResult(session_id=session.session_id)

    system_prompt = _build_system_prompt(config.goal)
    history: list[dict[str, Any]] = []

    try:
        for _ in range(config.max_steps):
            step = session.next_step()
            result.steps_run = step

            # 1. Capture screenshot
            try:
                ss_path = capture_screenshot(
                    target=target, save_path=session.screenshot_path(step)
                )
            except Exception as exc:
                logger.log_step(step, "screenshot", {}, error=str(exc))
                continue

            # 2. Get controls
            try:
                controls = UIAEngine.list_controls(target, depth=3)
            except Exception as exc:
                result.passed = False
                result.failures.append({
                    "step": step, "oracle": "Cannot list controls", "error": str(exc)
                })
                break

            # 3. Resize screenshot and encode
            ss_bytes = _resize_screenshot(ss_path)
            ss_b64 = base64.b64encode(ss_bytes).decode("ascii")

            # 4. Build prompt and call LLM
            recent_history = history[-config.history_window:]
            user_content = _build_user_content(
                ss_b64, controls, recent_history, step, config.max_steps
            )

            try:
                response = client.messages.create(
                    model=config.model,
                    max_tokens=1024,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_content}],
                    tools=[_ACTION_TOOL],
                    tool_choice={"type": "tool", "name": "perform_action"},
                )
            except Exception as exc:
                logger.log_step(step, "llm_call", {}, error=str(exc))
                result.failures.append({
                    "step": step, "oracle": "LLM call failed", "error": str(exc)
                })
                break

            # 5. Parse response
            parsed = _parse_llm_response(response)
            action = parsed.get("action", "done")
            selector_dict = parsed.get("selector", {})
            text = parsed.get("text", "")
            reasoning = parsed.get("reasoning", "")

            # 6. Check for done
            if action == "done":
                logger.log_step(step, "done", {}, result={"reasoning": reasoning})
                history.append({
                    "step": step, "action": "done",
                    "reasoning": reasoning,
                })
                break

            # 7. Build selector
            selector = Selector(
                automation_id=selector_dict.get("automation_id") or None,
                name=selector_dict.get("name") or None,
                control_type=selector_dict.get("control_type") or None,
            )

            args: dict[str, Any] = {
                "selector": selector.model_dump(exclude_none=True),
                "reasoning": reasoning,
            }
            if action == "type_text":
                args["text"] = text

            # 8. Safety check
            if is_destructive(action, args, config.safety):
                logger.log_step(step, action, args, error="Blocked by safety")
                recorder.record(action, args)
                history.append({
                    "step": step, "action": action,
                    "selector": selector.describe(),
                    "reasoning": reasoning,
                    "error": "Blocked by safety",
                })
                continue

            # 9. Execute action
            recorder.record(action, args)
            try:
                _execute_action(target, action, selector, args)
                logger.log_step(step, action, args, result={"ok": True})
                history.append({
                    "step": step, "action": action,
                    "selector": selector.describe(),
                    "reasoning": reasoning,
                })
            except Exception as exc:
                logger.log_step(step, action, args, error=str(exc))
                history.append({
                    "step": step, "action": action,
                    "selector": selector.describe(),
                    "reasoning": reasoning,
                    "error": str(exc),
                })

            # 10. Oracle check
            if step % config.oracle_interval == 0:
                verdicts = run_all_oracles(target, config.invariants)
                for v in verdicts:
                    if v.failed:
                        _capture_failure_evidence(target, session, step)
                        result.passed = False
                        result.failures.append({
                            "step": step,
                            "oracle": v.reason,
                            "details": v.details,
                        })

                if not result.passed:
                    break

            if config.step_delay_ms > 0:
                time.sleep(config.step_delay_ms / 1000.0)

    finally:
        recorder.save()
        logger.close()

    return result


def _execute_action(
    target: ResolvedTarget,
    action: str,
    selector: Selector,
    args: dict[str, Any],
) -> None:
    """Execute a single UI action."""
    if action == "click":
        UIAEngine.click(target, selector)
    elif action == "type_text":
        UIAEngine.type_text(target, selector, args.get("text", ""))
    elif action == "toggle":
        UIAEngine.toggle(target, selector)
    elif action == "select_combo":
        UIAEngine.select_combo(target, selector, args.get("text", ""))
    elif action == "read_text":
        UIAEngine.read_text(target, selector)
    else:
        UIAEngine.click(target, selector)


def _capture_failure_evidence(
    target: ResolvedTarget, session: Session, step: int
) -> None:
    """Capture screenshot and UIA snapshot for failure evidence."""
    try:
        capture_screenshot(target=target, save_path=session.screenshot_path(step))
    except Exception:
        pass
    try:
        snap = capture_snapshot(target)
        save_snapshot(snap, session.uia_snapshot_path(step))
    except Exception:
        pass
