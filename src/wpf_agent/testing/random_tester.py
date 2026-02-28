"""Random (exploratory) tester with seed-based determinism."""

from __future__ import annotations

import pathlib
import random
import time
from dataclasses import dataclass, field
from typing import Any

import yaml

from wpf_agent.config import SafetyConfig
from wpf_agent.core.errors import SafetyViolationError
from wpf_agent.core.safety import is_destructive
from wpf_agent.core.session import Session
from wpf_agent.core.target import ResolvedTarget
from wpf_agent.runner.logging import ActionRecorder, StepLogger
from wpf_agent.testing.oracles import OracleVerdict, run_all_oracles
from wpf_agent.uia.engine import UIAEngine
from wpf_agent.uia.screenshot import capture_screenshot
from wpf_agent.uia.selector import Selector
from wpf_agent.uia.snapshot import capture_snapshot, save_snapshot


@dataclass
class ActionSpace:
    """Weighted action definitions for random testing."""
    actions: list[dict[str, Any]] = field(default_factory=lambda: [
        {"action": "click", "weight": 5},
        {"action": "type_text", "weight": 2, "texts": ["test", "hello", "123", ""]},
        {"action": "toggle", "weight": 1},
        {"action": "select_combo", "weight": 1},
    ])


@dataclass
class RandomConfig:
    max_steps: int = 200
    seed: int | None = None
    action_space: ActionSpace = field(default_factory=ActionSpace)
    invariants: list[dict[str, Any]] = field(default_factory=list)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    step_delay_ms: int = 500
    oracle_interval: int = 5  # run oracles every N steps
    profile: str = ""  # profile name (resolved by CLI)

    @classmethod
    def from_file(cls, path: pathlib.Path) -> RandomConfig:
        """Load RandomConfig from a YAML file."""
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))

        action_space = ActionSpace()
        if "action_space" in raw and "actions" in raw["action_space"]:
            action_space = ActionSpace(actions=raw["action_space"]["actions"])

        safety = SafetyConfig()
        if "safety" in raw:
            safety = SafetyConfig(**raw["safety"])

        return cls(
            max_steps=raw.get("max_steps", 200),
            seed=raw.get("seed"),
            action_space=action_space,
            invariants=raw.get("invariants", []),
            safety=safety,
            step_delay_ms=raw.get("step_delay_ms", 500),
            oracle_interval=raw.get("oracle_interval", 5),
            profile=raw.get("profile", ""),
        )


@dataclass
class RandomTestResult:
    seed: int
    steps_run: int
    failures: list[dict[str, Any]] = field(default_factory=list)
    session_id: str = ""
    passed: bool = True


def run_random_test(
    target: ResolvedTarget,
    config: RandomConfig,
    session: Session | None = None,
) -> RandomTestResult:
    """Run a random exploration test."""
    seed = config.seed if config.seed is not None else random.randint(0, 2**32 - 1)
    rng = random.Random(seed)

    if session is None:
        session = Session()
    session.start()

    logger = StepLogger(session)
    recorder = ActionRecorder(session)
    logger.open()

    result = RandomTestResult(
        seed=seed, steps_run=0, session_id=session.session_id
    )

    try:
        for _ in range(config.max_steps):
            step = session.next_step()
            result.steps_run = step

            # Get available controls
            try:
                controls = UIAEngine.list_controls(target, depth=3)
            except Exception as exc:
                result.passed = False
                result.failures.append({
                    "step": step, "oracle": "Cannot list controls", "error": str(exc)
                })
                break

            if not controls:
                break

            # Pick a random action and target element
            action_def = _weighted_choice(rng, config.action_space.actions)
            action = action_def["action"]
            ctrl = rng.choice(controls)

            selector = Selector(
                automation_id=ctrl.get("automation_id") or None,
                name=ctrl.get("name") or None,
                control_type=ctrl.get("control_type") or None,
            )

            args: dict[str, Any] = {"selector": selector.model_dump(exclude_none=True)}

            if action == "type_text":
                texts = action_def.get("texts", ["test"])
                args["text"] = rng.choice(texts)

            # Safety check
            if is_destructive(action, args, config.safety):
                logger.log_step(step, action, args, error="Blocked by safety")
                recorder.record(action, args)
                continue

            # Execute
            recorder.record(action, args)
            try:
                _execute_random_action(target, action, selector, args)
                logger.log_step(step, action, args, result={"ok": True})
            except Exception as exc:
                logger.log_step(step, action, args, error=str(exc))

            # Periodic oracle check
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


def _weighted_choice(rng: random.Random, actions: list[dict[str, Any]]) -> dict[str, Any]:
    weights = [a.get("weight", 1) for a in actions]
    return rng.choices(actions, weights=weights, k=1)[0]


def _execute_random_action(
    target: ResolvedTarget,
    action: str,
    selector: Selector,
    args: dict[str, Any],
) -> None:
    if action == "click":
        UIAEngine.click(target, selector)
    elif action == "type_text":
        UIAEngine.type_text(target, selector, args.get("text", ""))
    elif action == "toggle":
        UIAEngine.toggle(target, selector)
    elif action == "select_combo":
        # Try to select first available item
        try:
            state = UIAEngine.get_state(target, selector)
            UIAEngine.select_combo(target, selector, "")
        except Exception:
            pass
    else:
        UIAEngine.click(target, selector)


def _capture_failure_evidence(
    target: ResolvedTarget, session: Session, step: int
) -> None:
    try:
        capture_screenshot(target=target, save_path=session.screenshot_path(step))
    except Exception:
        pass
    try:
        snap = capture_snapshot(target)
        save_snapshot(snap, session.uia_snapshot_path(step))
    except Exception:
        pass
