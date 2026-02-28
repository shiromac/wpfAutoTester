"""Agent loop: capture → AI → execute → verify → repeat."""

from __future__ import annotations

import json
import sys
import time
from typing import Any, Callable

from wpf_agent.core.session import Session
from wpf_agent.core.target import ResolvedTarget
from wpf_agent.runner.logging import ActionRecorder, StepLogger
from wpf_agent.uia.engine import UIAEngine
from wpf_agent.uia.screenshot import capture_screenshot
from wpf_agent.uia.snapshot import capture_snapshot, save_snapshot


class AgentLoop:
    """Main agent loop coordinating AI analysis and UI operations.

    In MCP mode the AI drives via tool calls.  This loop is for
    the standalone runner (CLI `wpf-agent run`).
    """

    def __init__(
        self,
        target: ResolvedTarget,
        session: Session,
        max_steps: int = 100,
        step_delay_ms: int = 100,
        on_step: Callable[[int, dict], None] | None = None,
    ):
        self.target = target
        self.session = session
        self.max_steps = max_steps
        self.step_delay_ms = step_delay_ms
        self.on_step = on_step
        self.logger = StepLogger(session)
        self.recorder = ActionRecorder(session)
        self._running = False

    def run(self, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Execute a pre-planned list of actions (from AI or scenario)."""
        self.session.start()
        self.logger.open()
        self._running = True
        results: list[dict[str, Any]] = []

        try:
            for action_spec in actions:
                if not self._running:
                    break
                step = self.session.next_step()
                if step > self.max_steps:
                    break

                action = action_spec.get("tool") or action_spec.get("action", "")
                args = action_spec.get("args", {})

                # Record for replay
                self.recorder.record(action, args)

                # Execute
                result = self._execute_step(step, action, args)
                results.append(result)

                if self.on_step:
                    self.on_step(step, result)

                if self.step_delay_ms > 0:
                    time.sleep(self.step_delay_ms / 1000.0)
        finally:
            self.recorder.save()
            self.logger.close()
            self._running = False

        return results

    def stop(self) -> None:
        self._running = False

    def _execute_step(
        self, step: int, action: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        from wpf_agent.runner.replay import _execute_action

        # Capture pre-step snapshot
        try:
            snap = capture_snapshot(self.target)
            snap_path = self.session.uia_snapshot_path(step)
            save_snapshot(snap, snap_path)
        except Exception:
            snap_path = None

        # Execute action
        try:
            result = _execute_action(self.target, action, args)
            self.logger.log_step(
                step, action, args,
                result=result,
                uia_snapshot_path=str(snap_path) if snap_path else None,
            )
            return {"step": step, "action": action, "result": result, "success": True}
        except Exception as exc:
            # Capture failure screenshot
            try:
                ss_path = capture_screenshot(
                    target=self.target,
                    save_path=self.session.screenshot_path(step),
                )
            except Exception:
                ss_path = None

            self.logger.log_step(
                step, action, args,
                error=str(exc),
                screenshot_path=str(ss_path) if ss_path else None,
                uia_snapshot_path=str(snap_path) if snap_path else None,
            )
            return {"step": step, "action": action, "error": str(exc), "success": False}
