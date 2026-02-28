"""UIA tree snapshot for logging and diff analysis."""

from __future__ import annotations

import json
import pathlib
from typing import Any

from wpf_agent.constants import DEFAULT_DEPTH, MAX_CONTROLS
from wpf_agent.core.target import ResolvedTarget


def capture_snapshot(
    target: ResolvedTarget,
    depth: int = DEFAULT_DEPTH,
) -> list[dict[str, Any]]:
    """Capture a serializable snapshot of the UIA tree."""
    from wpf_agent.uia.engine import UIAEngine
    return UIAEngine.list_controls(target, depth=depth)


def save_snapshot(snapshot: list[dict[str, Any]], path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")


def load_snapshot(path: pathlib.Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def diff_snapshots(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare two snapshots and return differences."""

    def _key(item: dict[str, Any]) -> str:
        return f"{item.get('automation_id', '')}|{item.get('name', '')}|{item.get('control_type', '')}"

    before_map = {_key(i): i for i in before}
    after_map = {_key(i): i for i in after}

    added = [v for k, v in after_map.items() if k not in before_map]
    removed = [v for k, v in before_map.items() if k not in after_map]

    changed = []
    for k in before_map:
        if k in after_map:
            b, a = before_map[k], after_map[k]
            diffs = {}
            for field in ("enabled", "visible", "value"):
                if b.get(field) != a.get(field):
                    diffs[field] = {"before": b.get(field), "after": a.get(field)}
            if diffs:
                changed.append({"element": k, "changes": diffs})

    return {"added": added, "removed": removed, "changed": changed}
