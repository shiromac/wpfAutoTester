"""Pydantic models for MCP tool arguments and responses."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Target specification ──────────────────────────────────────────

class TargetSpec(BaseModel):
    pid: Optional[int] = None
    process: Optional[str] = None
    exe: Optional[str] = None
    args: list[str] = Field(default_factory=list)
    title_re: Optional[str] = None


# ── Selector ──────────────────────────────────────────────────────

class SelectorArg(BaseModel):
    automation_id: Optional[str] = None
    name: Optional[str] = None
    control_type: Optional[str] = None
    index: Optional[int] = None
    bounding_rect: Optional[dict[str, int]] = None


# ── Tool argument models ──────────────────────────────────────────

class ResolveTargetArgs(BaseModel):
    target_spec: TargetSpec


class WindowQueryArgs(BaseModel):
    window_query: Optional[str] = None
    target_id: Optional[str] = None


class WaitWindowArgs(WindowQueryArgs):
    timeout_ms: int = 10000


class ListControlsArgs(WindowQueryArgs):
    depth: int = 4
    filter: Optional[str] = None


class ClickArgs(WindowQueryArgs):
    selector: SelectorArg


class TypeTextArgs(WindowQueryArgs):
    selector: SelectorArg
    text: str
    clear: bool = True


class SelectComboArgs(WindowQueryArgs):
    selector: SelectorArg
    item_text: str


class ToggleArgs(WindowQueryArgs):
    selector: SelectorArg
    state: Optional[bool] = None


class ReadTextArgs(WindowQueryArgs):
    selector: SelectorArg


class GetStateArgs(WindowQueryArgs):
    selector: SelectorArg


class ScreenshotArgs(BaseModel):
    window_query: Optional[str] = None
    target_id: Optional[str] = None
    region: Optional[dict[str, int]] = None


class WaitForArgs(WindowQueryArgs):
    selector: SelectorArg
    condition: str = "exists"
    value: Any = True
    timeout_ms: int = 10000


# ── Response wrappers ─────────────────────────────────────────────

class ToolResult(BaseModel):
    success: bool = True
    data: Any = None
    error: Optional[str] = None
