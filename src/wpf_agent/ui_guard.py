"""Mouse-movement guard for UI operations.

Detects user mouse movement before destructive UI commands and pauses
the automation loop until explicitly resumed with ``wpf-agent ui resume``.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from wpf_agent.constants import (
    GUARD_CHECK_DELAY_MS,
    GUARD_MOVEMENT_THRESHOLD_PX,
    GUARD_PAUSE_DIR,
)
from wpf_agent.core.errors import UserInterruptError

# ── Cursor position ──────────────────────────────────────────────


@dataclass
class CursorPos:
    x: int
    y: int


def _get_cursor_pos() -> CursorPos:
    """Return the current cursor position using Win32 API."""
    pt = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return CursorPos(x=pt.x, y=pt.y)


# ── Pause file management ────────────────────────────────────────

_PAUSE_FILE = GUARD_PAUSE_DIR / "pause"
_PAUSE_INFO_FILE = GUARD_PAUSE_DIR / "pause_info.json"


def is_paused() -> bool:
    """Return True if the pause file exists."""
    return _PAUSE_FILE.exists()


def set_paused(reason: str, command: str, detail: str = "") -> None:
    """Create the pause file and write pause info JSON."""
    GUARD_PAUSE_DIR.mkdir(parents=True, exist_ok=True)
    _PAUSE_FILE.write_text("paused\n", encoding="utf-8")
    info = {
        "reason": reason,
        "command": command,
        "detail": detail,
        "paused_at": datetime.now(timezone.utc).isoformat(),
    }
    _PAUSE_INFO_FILE.write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def clear_pause() -> bool:
    """Remove the pause file.  Returns True if it existed."""
    existed = _PAUSE_FILE.exists()
    if _PAUSE_FILE.exists():
        _PAUSE_FILE.unlink()
    if _PAUSE_INFO_FILE.exists():
        _PAUSE_INFO_FILE.unlink()
    return existed


def get_pause_info() -> dict | None:
    """Read the pause info JSON, or None if not paused."""
    if not _PAUSE_INFO_FILE.exists():
        return None
    try:
        return json.loads(_PAUSE_INFO_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# ── Main guard check ─────────────────────────────────────────────


def check_guard(command_name: str) -> None:
    """Run the mouse-movement guard before a UI command.

    Raises ``UserInterruptError`` if:
    1. The pause file already exists (previously interrupted), or
    2. The mouse moved more than *GUARD_MOVEMENT_THRESHOLD_PX* pixels
       during a short sampling window.
    """
    # 1. Already paused?
    if is_paused():
        info = get_pause_info() or {}
        raise UserInterruptError(
            reason="paused",
            detail=(
                f"Previously paused ({info.get('reason', 'unknown')}). "
                "Run 'wpf-agent ui resume' to continue."
            ),
        )

    # 2. Sample mouse position
    pos1 = _get_cursor_pos()
    time.sleep(GUARD_CHECK_DELAY_MS / 1000.0)
    pos2 = _get_cursor_pos()

    distance = math.hypot(pos2.x - pos1.x, pos2.y - pos1.y)
    if distance > GUARD_MOVEMENT_THRESHOLD_PX:
        detail = (
            f"Mouse moved {distance:.1f}px "
            f"({pos1.x},{pos1.y})->({pos2.x},{pos2.y}) "
            f"during {GUARD_CHECK_DELAY_MS}ms pre-check."
        )
        set_paused(reason="mouse_movement", command=command_name, detail=detail)
        raise UserInterruptError(reason="mouse_movement", detail=detail)
