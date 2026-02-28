"""Safety checks for destructive operations."""

from __future__ import annotations

import re
from typing import Any

from wpf_agent.config import SafetyConfig
from wpf_agent.core.errors import SafetyViolationError


def check_safety(
    action: str,
    selector_desc: str,
    config: SafetyConfig,
    confirmed: bool = False,
) -> None:
    """Raise SafetyViolationError if the action looks destructive and is not allowed."""
    if config.allow_destructive:
        return
    combined = f"{action} {selector_desc}".lower()
    for pattern in config.destructive_patterns:
        if re.search(pattern, combined):
            raise SafetyViolationError(
                f"Destructive operation blocked: action={action!r}, "
                f"selector={selector_desc!r} matched pattern={pattern!r}. "
                f"Set allow_destructive=true in profile to permit."
            )


def is_destructive(action: str, args: dict[str, Any], config: SafetyConfig) -> bool:
    """Check if an action appears destructive without raising."""
    combined = f"{action} {args}".lower()
    for pattern in config.destructive_patterns:
        if re.search(pattern, combined):
            return True
    return False
