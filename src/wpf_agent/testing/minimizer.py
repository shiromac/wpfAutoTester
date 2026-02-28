"""Repro step minimization — reduce failing action sequences."""

from __future__ import annotations

import copy
from typing import Any, Callable

from wpf_agent.core.session import Session
from wpf_agent.core.target import ResolvedTarget
from wpf_agent.runner.replay import replay_actions
from wpf_agent.testing.oracles import run_all_oracles


def minimize_actions(
    actions: list[dict[str, Any]],
    target: ResolvedTarget,
    check_failure: Callable[[ResolvedTarget], bool] | None = None,
    max_attempts: int = 20,
) -> list[dict[str, Any]]:
    """Try to reduce the action list while still reproducing the failure.

    Uses a simple bisection strategy:
    1. Try last N actions
    2. Try first-half / second-half deletion

    Returns the shortest reproducing sequence found.
    """
    if check_failure is None:
        check_failure = _default_failure_check

    # Start with the full sequence
    best = list(actions)

    # Strategy 1: Try last-N slices
    for n in [5, 10, 20]:
        if n >= len(best):
            continue
        candidate = best[-n:]
        if _reproduces(candidate, target, check_failure):
            best = candidate

    # Strategy 2: Bisection — try removing halves
    for attempt in range(max_attempts):
        if len(best) <= 2:
            break
        mid = len(best) // 2

        # Try second half only
        candidate = best[mid:]
        if _reproduces(candidate, target, check_failure):
            best = candidate
            continue

        # Try first half only
        candidate = best[:mid]
        if _reproduces(candidate, target, check_failure):
            best = candidate
            continue

        # Try removing individual steps from the middle
        improved = False
        for i in range(len(best) - 1, 0, -1):
            candidate = best[:i] + best[i + 1:]
            if _reproduces(candidate, target, check_failure):
                best = candidate
                improved = True
                break

        if not improved:
            break

    return best


def _reproduces(
    actions: list[dict[str, Any]],
    target: ResolvedTarget,
    check_failure: Callable[[ResolvedTarget], bool],
) -> bool:
    """Check if an action sequence reproduces the failure."""
    try:
        session = Session()
        replay_actions(actions, target, session=session, step_delay_ms=200)
        return check_failure(target)
    except Exception:
        return True  # exception during replay counts as failure reproduction


def _default_failure_check(target: ResolvedTarget) -> bool:
    """Default failure oracle check."""
    verdicts = run_all_oracles(target)
    return any(v.failed for v in verdicts)
