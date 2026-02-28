"""Evidence collection for ticket generation."""

from __future__ import annotations

import json
import pathlib
import shutil
from typing import Any

from wpf_agent.core.session import Session
from wpf_agent.core.target import ResolvedTarget
from wpf_agent.runner.logging import StepLogger
from wpf_agent.uia.screenshot import capture_screenshot
from wpf_agent.uia.snapshot import capture_snapshot, diff_snapshots, load_snapshot, save_snapshot


def collect_evidence(
    session: Session,
    target: ResolvedTarget | None,
    failure_step: int | None = None,
    log_tail: int = 20,
) -> dict[str, Any]:
    """Gather all evidence around a failure for ticket generation."""
    evidence: dict[str, Any] = {
        "session_id": session.session_id,
        "screenshots": [],
        "uia_snapshots": [],
        "uia_diff": None,
        "recent_logs": [],
    }

    # Collect screenshots
    for png in sorted(session.screens_dir.glob("*.png")):
        evidence["screenshots"].append(str(png))

    # Capture current screenshot if target available
    if target and target.is_alive:
        try:
            step = failure_step or session.step_count
            path = capture_screenshot(
                target=target, save_path=session.screenshot_path(step + 1000)
            )
            evidence["screenshots"].append(str(path))
        except Exception:
            pass

    # Collect UIA snapshots
    for snap_file in sorted(session.uia_dir.glob("*.json")):
        evidence["uia_snapshots"].append(str(snap_file))

    # Capture current UIA snapshot and compute diff
    if target and target.is_alive:
        try:
            current_snap = capture_snapshot(target)
            current_path = session.uia_dir / "failure-current.json"
            save_snapshot(current_snap, current_path)
            evidence["uia_snapshots"].append(str(current_path))

            # Find previous snapshot for diff
            snap_files = sorted(session.uia_dir.glob("step-*.json"))
            if snap_files:
                prev_snap = load_snapshot(snap_files[-1])
                evidence["uia_diff"] = diff_snapshots(prev_snap, current_snap)
        except Exception:
            pass

    # Recent logs
    logger = StepLogger(session)
    evidence["recent_logs"] = logger.read_last_n(log_tail)

    return evidence


def package_evidence(
    evidence: dict[str, Any],
    ticket_dir: pathlib.Path,
) -> None:
    """Copy evidence files into the ticket directory structure."""
    screens_dir = ticket_dir / "screens"
    uia_dir = ticket_dir / "uia"
    screens_dir.mkdir(parents=True, exist_ok=True)
    uia_dir.mkdir(parents=True, exist_ok=True)

    for ss in evidence.get("screenshots", []):
        src = pathlib.Path(ss)
        if src.exists():
            shutil.copy2(src, screens_dir / src.name)

    for snap in evidence.get("uia_snapshots", []):
        src = pathlib.Path(snap)
        if src.exists():
            shutil.copy2(src, uia_dir / src.name)

    # Save runner log
    if evidence.get("recent_logs"):
        log_path = ticket_dir / "runner.log"
        log_path.write_text(
            json.dumps(evidence["recent_logs"], indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    # Save UIA diff
    if evidence.get("uia_diff"):
        diff_path = uia_dir / "diff.json"
        diff_path.write_text(
            json.dumps(evidence["uia_diff"], indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
