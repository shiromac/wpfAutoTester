"""Ticket generator — creates structured issue tickets with evidence."""

from __future__ import annotations

import json
import pathlib
import time
from typing import Any

from wpf_agent.constants import TICKET_DIR
from wpf_agent.core.session import Session
from wpf_agent.core.target import ResolvedTarget
from wpf_agent.tickets.evidence import collect_evidence, package_evidence
from wpf_agent.tickets.templates import default_environment, render_ticket_md


def generate_ticket(
    session: Session,
    target: ResolvedTarget | None,
    title: str,
    summary: str,
    repro_steps: list[str],
    actual_result: str,
    expected_result: str,
    failure_step: int | None = None,
    root_cause_hypothesis: str = "",
    extra_env: dict[str, Any] | None = None,
    seed: int | None = None,
    profile_name: str = "",
) -> pathlib.Path:
    """Generate a complete ticket directory with all evidence.

    Returns the path to the ticket directory.
    """
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    short_id = session.session_id[:8]
    ticket_name = f"TICKET-{timestamp}-{short_id}"
    ticket_dir = pathlib.Path(TICKET_DIR) / session.session_id / ticket_name
    ticket_dir.mkdir(parents=True, exist_ok=True)

    # Collect and package evidence
    evidence = collect_evidence(session, target, failure_step=failure_step)
    package_evidence(evidence, ticket_dir)

    # Build environment info
    env = default_environment()
    if extra_env:
        env.update(extra_env)
    if seed is not None:
        env["Seed"] = str(seed)
    if profile_name:
        env["Profile"] = profile_name
    if target:
        env["Target PID"] = str(target.pid)
        env["Target Process"] = target.process_name

    # Gather evidence file list
    evidence_files = []
    for p in sorted(ticket_dir.rglob("*")):
        if p.is_file() and p.name != "ticket.md" and p.name != "ticket.json":
            evidence_files.append(str(p.relative_to(ticket_dir)))

    # Render ticket.md
    md = render_ticket_md(
        title=title,
        summary=summary,
        repro_steps=repro_steps,
        actual_result=actual_result,
        expected_result=expected_result,
        environment=env,
        evidence_files=evidence_files,
        root_cause_hypothesis=root_cause_hypothesis,
        uia_diff=evidence.get("uia_diff"),
    )
    (ticket_dir / "ticket.md").write_text(md, encoding="utf-8")

    # Save repro.actions.json
    actions_src = session.actions_path()
    if actions_src.exists():
        import shutil
        shutil.copy2(actions_src, ticket_dir / "repro.actions.json")

    # Save ticket.json (machine-readable)
    ticket_json = {
        "title": title,
        "summary": summary,
        "repro_steps": repro_steps,
        "actual_result": actual_result,
        "expected_result": expected_result,
        "environment": env,
        "evidence_files": evidence_files,
        "root_cause_hypothesis": root_cause_hypothesis,
        "session_id": session.session_id,
        "timestamp": timestamp,
    }
    (ticket_dir / "ticket.json").write_text(
        json.dumps(ticket_json, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    return ticket_dir


def generate_ticket_from_scenario(
    session: Session,
    target: ResolvedTarget | None,
    scenario_id: str,
    failures: list[dict[str, Any]],
    profile_name: str = "",
) -> pathlib.Path:
    """Generate a ticket from scenario test failures."""
    first = failures[0] if failures else {}

    repro_steps = []
    from wpf_agent.runner.logging import StepLogger
    logger = StepLogger(session)
    for entry in logger.read_last_n(50):
        repro_steps.append(
            f"[Step {entry.get('step')}] {entry.get('action')}: {entry.get('args', {})}"
        )

    actual_parts = []
    for f in failures:
        if "assertion" in f:
            actual_parts.append(
                f"Assertion '{f['assertion']}' failed: expected={f.get('expected')}, actual={f.get('actual')}"
            )
        elif "oracle" in f:
            actual_parts.append(f"Oracle: {f['oracle']}")
        elif "error" in f:
            actual_parts.append(f"Error: {f['error']}")

    return generate_ticket(
        session=session,
        target=target,
        title=f"Scenario '{scenario_id}' failed",
        summary=f"Scenario test '{scenario_id}' detected {len(failures)} failure(s).",
        repro_steps=repro_steps,
        actual_result="\n".join(actual_parts),
        expected_result="All scenario steps and assertions should pass.",
        failure_step=first.get("step"),
        root_cause_hypothesis=_guess_root_cause(failures),
        profile_name=profile_name,
    )


def generate_ticket_from_random(
    session: Session,
    target: ResolvedTarget | None,
    seed: int,
    failures: list[dict[str, Any]],
    profile_name: str = "",
) -> pathlib.Path:
    """Generate a ticket from random test failures."""
    first = failures[0] if failures else {}

    repro_steps = [f"Run random test with seed={seed}"]
    from wpf_agent.runner.logging import StepLogger
    logger = StepLogger(session)
    for entry in logger.read_last_n(30):
        repro_steps.append(
            f"[Step {entry.get('step')}] {entry.get('action')}: {entry.get('args', {})}"
        )

    actual_parts = []
    for f in failures:
        if "oracle" in f:
            actual_parts.append(f"Oracle: {f['oracle']}")
        if "error" in f:
            actual_parts.append(f"Error: {f.get('error', '')}")

    return generate_ticket(
        session=session,
        target=target,
        title=f"Random test failure (seed={seed}, step={first.get('step', '?')})",
        summary=f"Random exploratory test with seed={seed} detected {len(failures)} failure(s).",
        repro_steps=repro_steps,
        actual_result="\n".join(actual_parts),
        expected_result="Application should remain stable during exploratory testing.",
        failure_step=first.get("step"),
        root_cause_hypothesis=_guess_root_cause(failures),
        seed=seed,
        profile_name=profile_name,
    )


def generate_ticket_from_explore(
    session: Session,
    target: ResolvedTarget | None,
    failures: list[dict[str, Any]],
    goal: str = "",
    profile_name: str = "",
) -> pathlib.Path:
    """Generate a ticket from AI-guided explore test failures."""
    first = failures[0] if failures else {}

    repro_steps = [f"Run AI-guided explore test"]
    if goal:
        repro_steps.append(f"Goal: {goal}")
    from wpf_agent.runner.logging import StepLogger
    logger = StepLogger(session)
    for entry in logger.read_last_n(30):
        repro_steps.append(
            f"[Step {entry.get('step')}] {entry.get('action')}: {entry.get('args', {})}"
        )

    actual_parts = []
    for f in failures:
        if "oracle" in f:
            actual_parts.append(f"Oracle: {f['oracle']}")
        if "error" in f:
            actual_parts.append(f"Error: {f.get('error', '')}")

    return generate_ticket(
        session=session,
        target=target,
        title=f"AI explore test failure (step={first.get('step', '?')})",
        summary=f"AI-guided exploratory test detected {len(failures)} failure(s).",
        repro_steps=repro_steps,
        actual_result="\n".join(actual_parts),
        expected_result="Application should remain stable during AI-guided exploratory testing.",
        failure_step=first.get("step"),
        root_cause_hypothesis=_guess_root_cause(failures),
        profile_name=profile_name,
    )


def _guess_root_cause(failures: list[dict[str, Any]]) -> str:
    """Best-effort root cause hypothesis based on failure data."""
    if not failures:
        return ""
    reasons = []
    for f in failures:
        if "oracle" in f and "terminated" in f["oracle"].lower():
            reasons.append("Process crash detected — likely unhandled exception or access violation.")
        elif "oracle" in f and "freeze" in f["oracle"].lower():
            reasons.append("UI freeze — possible deadlock or long-running UI thread operation.")
        elif "oracle" in f and "error dialog" in f["oracle"].lower():
            reasons.append(
                f"Error dialog appeared: {f.get('details', {}).get('control', {}).get('name', 'unknown')}"
            )
        elif "assertion" in f:
            reasons.append(
                f"Assertion '{f['assertion']}' mismatch — UI state differs from expected. "
                f"Expected: {f.get('expected')}, Got: {f.get('actual')}"
            )
        elif "error" in f:
            reasons.append(f"Operation error: {f.get('error', '')}")
    return " | ".join(reasons) if reasons else "Unable to determine root cause."
