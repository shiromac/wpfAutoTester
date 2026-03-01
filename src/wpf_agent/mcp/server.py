"""FastMCP server exposing 13 UIA tools."""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any

from mcp.server.fastmcp import FastMCP

from wpf_agent.core.errors import WpfAgentError
from wpf_agent.core.target import ResolvedTarget, TargetRegistry
from wpf_agent.uia.engine import UIAEngine
from wpf_agent.uia.screenshot import capture_screenshot
from wpf_agent.uia.selector import Selector

mcp = FastMCP("wpf-agent")


# ── Helpers ───────────────────────────────────────────────────────

def _resolve_target(
    window_query: str | None = None, target_id: str | None = None
) -> ResolvedTarget:
    """Resolve target from window_query or target_id.

    Accepts shorthand target_id formats that auto-resolve without a
    prior ``resolve_target`` call:
      - ``pid:<N>``          — resolve by PID
      - ``process:<name>``   — resolve by process name
      - ``title_re:<regex>`` — resolve by window title regex
    """
    registry = TargetRegistry.get_instance()
    if target_id:
        # Auto-resolve shorthand formats so callers can skip resolve_target
        if target_id.startswith("pid:"):
            pid = int(target_id.split(":", 1)[1])
            _, t = registry.resolve({"pid": pid})
            return t
        if target_id.startswith("process:"):
            name = target_id.split(":", 1)[1]
            _, t = registry.resolve({"process": name})
            return t
        if target_id.startswith("title_re:"):
            pattern = target_id.split(":", 1)[1]
            _, t = registry.resolve({"title_re": pattern})
            return t
        return registry.get(target_id)
    if window_query:
        _, t = registry.resolve({"title_re": window_query})
        return t
    raise WpfAgentError("Provide window_query or target_id")


def _to_selector(s: dict[str, Any] | None) -> Selector:
    if s is None:
        return Selector()
    return Selector(**{k: v for k, v in s.items() if v is not None})


def _ok(data: Any) -> str:
    return json.dumps({"success": True, "data": data}, ensure_ascii=False, default=str)


def _err(msg: str) -> str:
    return json.dumps({"success": False, "error": msg}, ensure_ascii=False)


# ── MCP Tools (13) ────────────────────────────────────────────────

@mcp.tool()
def list_windows() -> str:
    """List currently visible top-level windows."""
    try:
        data = UIAEngine.list_windows()
        return _ok(data)
    except Exception as exc:
        return _err(str(exc))


@mcp.tool()
def resolve_target(target_spec: dict) -> str:
    """Resolve a target application from a target_spec and return a target_id.

    target_spec examples:
      {"pid": 12345}
      {"process": "MyApp.exe"}
      {"exe": "C:/path/MyApp.exe", "args": ["--dev"]}
      {"title_re": ".*MyApp.*"}
    """
    try:
        registry = TargetRegistry.get_instance()
        tid, t = registry.resolve(target_spec)
        return _ok({"target_id": tid, "pid": t.pid, "process": t.process_name})
    except Exception as exc:
        return _err(str(exc))


@mcp.tool()
def focus_window(window_query: str = "", target_id: str = "") -> str:
    """Bring target window to front."""
    try:
        t = _resolve_target(window_query or None, target_id or None)
        data = UIAEngine.focus_window(t)
        return _ok(data)
    except Exception as exc:
        return _err(str(exc))


@mcp.tool()
def wait_window(
    window_query: str = "", target_id: str = "", timeout_ms: int = 10000
) -> str:
    """Wait for a window to appear."""
    try:
        t = _resolve_target(window_query or None, target_id or None)
        data = UIAEngine.wait_window(t, timeout_ms)
        return _ok(data)
    except Exception as exc:
        return _err(str(exc))


@mcp.tool()
def list_controls(
    window_query: str = "",
    target_id: str = "",
    depth: int = 4,
    filter: str = "",
) -> str:
    """Enumerate UIA controls in the target window.

    Returns automation_id, name, control_type, enabled, visible, rect, value.
    """
    try:
        t = _resolve_target(window_query or None, target_id or None)
        data = UIAEngine.list_controls(t, depth=depth, filter_type=filter or None)
        return _ok(data)
    except Exception as exc:
        return _err(str(exc))


@mcp.tool()
def click(window_query: str = "", target_id: str = "", selector: dict = {}) -> str:
    """Click a UI element.

    target_id accepts registered IDs (e.g. "target-1") or shorthand formats
    that auto-resolve: "pid:12345", "process:MyApp.exe", "title_re:.*MyApp.*".
    Selector priority: automation_id > name+control_type > bounding_rect center.
    """
    try:
        t = _resolve_target(window_query or None, target_id or None)
        s = _to_selector(selector)
        data = UIAEngine.click(t, s)
        return _ok(data)
    except Exception as exc:
        return _err(str(exc))


@mcp.tool()
def type_text(
    window_query: str = "",
    target_id: str = "",
    selector: dict = {},
    text: str = "",
    clear: bool = True,
) -> str:
    """Type text into a UI element."""
    try:
        t = _resolve_target(window_query or None, target_id or None)
        s = _to_selector(selector)
        data = UIAEngine.type_text(t, s, text, clear=clear)
        return _ok(data)
    except Exception as exc:
        return _err(str(exc))


@mcp.tool()
def select_combo(
    window_query: str = "",
    target_id: str = "",
    selector: dict = {},
    item_text: str = "",
) -> str:
    """Select an item from a combo box."""
    try:
        t = _resolve_target(window_query or None, target_id or None)
        s = _to_selector(selector)
        data = UIAEngine.select_combo(t, s, item_text)
        return _ok(data)
    except Exception as exc:
        return _err(str(exc))


@mcp.tool()
def toggle(
    window_query: str = "",
    target_id: str = "",
    selector: dict = {},
    state: str = "",
) -> str:
    """Toggle a checkbox or toggle button. state: 'true', 'false', or '' for toggle."""
    try:
        t = _resolve_target(window_query or None, target_id or None)
        s = _to_selector(selector)
        st = None
        if state.lower() == "true":
            st = True
        elif state.lower() == "false":
            st = False
        data = UIAEngine.toggle(t, s, st)
        return _ok(data)
    except Exception as exc:
        return _err(str(exc))


@mcp.tool()
def read_text(
    window_query: str = "", target_id: str = "", selector: dict = {}
) -> str:
    """Read text from a UI element."""
    try:
        t = _resolve_target(window_query or None, target_id or None)
        s = _to_selector(selector)
        data = UIAEngine.read_text(t, s)
        return _ok(data)
    except Exception as exc:
        return _err(str(exc))


@mcp.tool()
def get_state(
    window_query: str = "", target_id: str = "", selector: dict = {}
) -> str:
    """Get the state of a UI element (enabled, visible, selected, value)."""
    try:
        t = _resolve_target(window_query or None, target_id or None)
        s = _to_selector(selector)
        data = UIAEngine.get_state(t, s)
        return _ok(data)
    except Exception as exc:
        return _err(str(exc))


@mcp.tool()
def screenshot(
    window_query: str = "",
    target_id: str = "",
    region: dict = {},
) -> str:
    """Capture a screenshot of the target window or full screen.

    Returns the path to the saved PNG file.
    """
    try:
        t = None
        if window_query or target_id:
            t = _resolve_target(window_query or None, target_id or None)
        r = region if region else None
        path = capture_screenshot(target=t, region=r)
        return _ok({"path": str(path)})
    except Exception as exc:
        return _err(str(exc))


@mcp.tool()
def wait_for(
    window_query: str = "",
    target_id: str = "",
    selector: dict = {},
    condition: str = "exists",
    value: str = "true",
    timeout_ms: int = 10000,
) -> str:
    """Wait until a condition is met on a UI element.

    Conditions: exists, enabled, visible, text_equals, text_contains.
    """
    try:
        t = _resolve_target(window_query or None, target_id or None)
        s = _to_selector(selector)
        # Parse value
        v: Any = value
        if value.lower() == "true":
            v = True
        elif value.lower() == "false":
            v = False
        data = UIAEngine.wait_for(t, s, condition, v, timeout_ms)
        return _ok(data)
    except Exception as exc:
        return _err(str(exc))


# ── Entry point ───────────────────────────────────────────────────

def run_server() -> None:
    """Start the MCP server on stdio."""
    mcp.run(transport="stdio")
