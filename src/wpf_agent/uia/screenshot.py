"""Screenshot capture utilities."""

from __future__ import annotations

import pathlib
from typing import Any, Optional

from PIL import ImageGrab

from wpf_agent.core.target import ResolvedTarget


def capture_screenshot(
    target: ResolvedTarget | None = None,
    region: dict[str, int] | None = None,
    save_path: pathlib.Path | None = None,
) -> pathlib.Path:
    """Capture a screenshot, optionally scoped to a window or region."""
    bbox = None

    if region:
        bbox = (region["left"], region["top"], region["right"], region["bottom"])
    elif target:
        try:
            from wpf_agent.uia.engine import _top_window
            win = _top_window(target)
            r = win.rectangle()
            bbox = (r.left, r.top, r.right, r.bottom)
        except Exception:
            pass  # fall back to full screen

    img = ImageGrab.grab(bbox=bbox)

    if save_path is None:
        import tempfile
        fd = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        save_path = pathlib.Path(fd.name)
        fd.close()

    save_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(save_path), "PNG")
    return save_path
