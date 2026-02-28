"""Markdown templates for ticket generation."""

from __future__ import annotations

import os
import platform
from typing import Any


def render_ticket_md(
    title: str,
    summary: str,
    repro_steps: list[str],
    actual_result: str,
    expected_result: str,
    environment: dict[str, Any],
    evidence_files: list[str],
    root_cause_hypothesis: str = "",
    uia_diff: dict[str, Any] | None = None,
) -> str:
    """Render a ticket.md from structured data."""
    lines = [
        f"# {title}",
        "",
        "## Summary",
        summary,
        "",
        "## Repro Steps",
    ]
    for i, step in enumerate(repro_steps, 1):
        lines.append(f"{i}. {step}")
    lines.append("")

    lines.extend([
        "## Actual Result",
        actual_result,
        "",
        "## Expected Result",
        expected_result,
        "",
        "## Environment",
    ])
    for k, v in environment.items():
        lines.append(f"- **{k}**: {v}")
    lines.append("")

    lines.append("## Evidence")
    for f in evidence_files:
        lines.append(f"- `{f}`")
    lines.append("")

    if root_cause_hypothesis:
        lines.extend([
            "## Root Cause Hypothesis",
            root_cause_hypothesis,
            "",
        ])

    if uia_diff:
        lines.append("## UIA Diff (before/after failure)")
        if uia_diff.get("removed"):
            lines.append("### Elements Removed")
            for elem in uia_diff["removed"][:10]:
                lines.append(f"- {elem.get('name', '')} ({elem.get('control_type', '')})")
        if uia_diff.get("added"):
            lines.append("### Elements Added")
            for elem in uia_diff["added"][:10]:
                lines.append(f"- {elem.get('name', '')} ({elem.get('control_type', '')})")
        if uia_diff.get("changed"):
            lines.append("### Elements Changed")
            for change in uia_diff["changed"][:10]:
                lines.append(f"- {change['element']}: {change['changes']}")
        lines.append("")

    return "\n".join(lines)


def default_environment() -> dict[str, Any]:
    """Gather default environment info."""
    return {
        "OS": f"{platform.system()} {platform.version()}",
        "Machine": platform.machine(),
        "Python": platform.python_version(),
    }
