"""UIA element selector resolution."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class Selector(BaseModel):
    """Identifies a UI element via UIA properties.

    Priority order:
    1. automation_id (most reliable)
    2. name + control_type
    3. bounding_rect center click (last resort)
    """
    automation_id: Optional[str] = None
    name: Optional[str] = None
    control_type: Optional[str] = None
    index: Optional[int] = None
    bounding_rect: Optional[dict[str, int]] = None

    def describe(self) -> str:
        parts = []
        if self.automation_id:
            parts.append(f"aid={self.automation_id}")
        if self.name:
            parts.append(f"name={self.name!r}")
        if self.control_type:
            parts.append(f"type={self.control_type}")
        if self.index is not None:
            parts.append(f"idx={self.index}")
        return ", ".join(parts) or "(empty selector)"

    def to_find_kwargs(self) -> dict[str, Any]:
        """Convert to pywinauto find_element kwargs."""
        kw: dict[str, Any] = {}
        if self.automation_id:
            kw["auto_id"] = self.automation_id
        if self.name:
            kw["title"] = self.name
        if self.control_type:
            kw["control_type"] = self.control_type
        return kw
