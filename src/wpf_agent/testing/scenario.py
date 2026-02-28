"""Scenario test runner — YAML-defined step sequences with assertions."""

from __future__ import annotations

import pathlib
import time
from dataclasses import dataclass, field
from typing import Any

import yaml

from wpf_agent.config import ProfileStore
from wpf_agent.core.errors import ScenarioError
from wpf_agent.core.session import Session
from wpf_agent.core.target import ResolvedTarget, TargetRegistry
from wpf_agent.runner.logging import ActionRecorder, StepLogger
from wpf_agent.testing.assertions import AssertionResult, check_assertion
from wpf_agent.testing.oracles import run_all_oracles
from wpf_agent.uia.engine import UIAEngine
from wpf_agent.uia.screenshot import capture_screenshot
from wpf_agent.uia.selector import Selector
from wpf_agent.uia.snapshot import capture_snapshot, save_snapshot


@dataclass
class ScenarioStep:
    action: str
    selector: dict[str, Any] = field(default_factory=dict)
    args: dict[str, Any] = field(default_factory=dict)
    expected: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Scenario:
    id: str
    title: str
    tags: list[str] = field(default_factory=list)
    owner: str = ""
    profile: str = ""
    target_spec: dict[str, Any] | None = None
    steps: list[ScenarioStep] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: pathlib.Path) -> Scenario:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        steps = []
        for s in raw.get("steps", []):
            steps.append(ScenarioStep(
                action=s["action"],
                selector=s.get("selector", {}),
                args=s.get("args", {}),
                expected=s.get("expected", []),
            ))
        return cls(
            id=raw.get("id", path.stem),
            title=raw.get("title", path.stem),
            tags=raw.get("tags", []),
            owner=raw.get("owner", ""),
            profile=raw.get("profile", ""),
            target_spec=raw.get("target_spec"),
            steps=steps,
        )


@dataclass
class ScenarioResult:
    scenario_id: str
    passed: bool
    steps_run: int
    failures: list[dict[str, Any]] = field(default_factory=list)
    session_id: str = ""


def run_scenario(
    scenario: Scenario,
    target: ResolvedTarget | None = None,
    session: Session | None = None,
    step_delay_ms: int = 100,
) -> ScenarioResult:
    """Execute a scenario and return results."""
    if session is None:
        session = Session()
    session.start()

    if target is None:
        registry = TargetRegistry.get_instance()
        if scenario.profile:
            store = ProfileStore()
            profile = store.get(scenario.profile)
            if profile is None:
                raise ScenarioError(f"Profile '{scenario.profile}' not found")
            _, target = registry.resolve_profile(profile)
        elif scenario.target_spec:
            _, target = registry.resolve(scenario.target_spec)
        else:
            raise ScenarioError("Scenario must specify profile or target_spec")

    logger = StepLogger(session)
    recorder = ActionRecorder(session)
    logger.open()
    result = ScenarioResult(
        scenario_id=scenario.id, passed=True, steps_run=0, session_id=session.session_id
    )

    try:
        for scenario_step in scenario.steps:
            step = session.next_step()
            result.steps_run = step
            action = scenario_step.action
            sel = Selector(**scenario_step.selector) if scenario_step.selector else Selector()
            args = scenario_step.args

            recorder.record(action, {**args, "selector": scenario_step.selector})

            # Execute action
            try:
                _run_action(target, action, sel, args)
                logger.log_step(step, action, args)
            except Exception as exc:
                logger.log_step(step, action, args, error=str(exc))
                _capture_failure_evidence(target, session, step)
                result.passed = False
                result.failures.append({
                    "step": step,
                    "action": action,
                    "error": str(exc),
                })
                break

            # Check assertions
            for exp in scenario_step.expected:
                exp_sel = Selector(**exp.get("selector", scenario_step.selector))
                assertion_result = check_assertion(
                    target, exp_sel, exp["type"], exp.get("value")
                )
                if not assertion_result.passed:
                    _capture_failure_evidence(target, session, step)
                    result.passed = False
                    result.failures.append({
                        "step": step,
                        "assertion": exp["type"],
                        **assertion_result.to_dict(),
                    })

            # Run oracles
            verdicts = run_all_oracles(target)
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

            if step_delay_ms > 0:
                time.sleep(step_delay_ms / 1000.0)

    finally:
        recorder.save()
        logger.close()

    return result


def _run_action(
    target: ResolvedTarget, action: str, selector: Selector, args: dict[str, Any]
) -> None:
    if action == "click":
        UIAEngine.click(target, selector)
    elif action == "type_text":
        UIAEngine.type_text(target, selector, args.get("text", ""), clear=args.get("clear", True))
    elif action == "select_combo":
        UIAEngine.select_combo(target, selector, args.get("item_text", ""))
    elif action == "toggle":
        UIAEngine.toggle(target, selector, args.get("state"))
    elif action == "focus_window":
        UIAEngine.focus_window(target)
    elif action == "wait_for":
        UIAEngine.wait_for(
            target, selector,
            args.get("condition", "exists"),
            args.get("value", True),
            args.get("timeout_ms", 10000),
        )
    elif action == "screenshot":
        capture_screenshot(target=target, save_path=session.screenshot_path())
    else:
        raise ScenarioError(f"Unknown action: {action}")


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
