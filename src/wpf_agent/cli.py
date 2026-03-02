"""CLI entry point — click-based commands."""

from __future__ import annotations

import json
import pathlib
import sys
import time

import click

from wpf_agent import __version__


@click.group()
@click.version_option(__version__)
def main():
    """WPF UI Debug Automation Agent."""
    pass


# ── init ──────────────────────────────────────────────────────────

@main.command()
def init():
    """Initialize project: create profiles.json template and directories."""
    from wpf_agent.config import PersonaStore, ProfileStore
    from wpf_agent.constants import SESSION_DIR, TICKET_DIR

    store = ProfileStore()
    store.ensure_default()
    click.echo(f"Created {store.path}")

    persona_store = PersonaStore()
    persona_store.ensure_default()
    click.echo(f"Created {persona_store.path}")

    for d in [SESSION_DIR, TICKET_DIR]:
        pathlib.Path(d).mkdir(parents=True, exist_ok=True)
        click.echo(f"Created {d}/")

    click.echo("\nInitialization complete. Edit profiles.json to add your target apps.")
    click.echo("Then register the MCP server and install skills:")
    click.echo('  claude mcp add wpf-agent -- python -m wpf_agent mcp-serve')
    click.echo('  wpf-agent install-skills')


# ── install-skills ────────────────────────────────────────────────

@main.command("install-skills")
@click.option("--target", default=None, help="Target directory (default: current directory)")
@click.option("--github", is_flag=True, default=False, help="Also install into .github/skills/ for GitHub Copilot Coding Agent")
@click.option("--no-claude-md", is_flag=True, default=False, help="Skip updating CLAUDE.md")
@click.option("-y", "--yes", is_flag=True, default=False, help="Skip confirmation prompt for CLAUDE.md update")
def install_skills(target, github, no_claude_md, yes):
    """Install Claude Code slash-command skills into .claude/skills/.

    Copies bundled skill files (/wpf-explore, /wpf-verify, etc.) so that
    Claude Code auto-detects them when launched from this directory.

    Also appends a wpf-agent guide section to CLAUDE.md (with confirmation).
    Use --no-claude-md to skip the CLAUDE.md update.

    With --github, also copies skills into .github/skills/ for GitHub
    Copilot Coding Agent (repository-level).
    """
    import importlib.resources

    dest_root = pathlib.Path(target) if target else pathlib.Path.cwd()

    # Locate bundled skills: try wheel-bundled _skills/ first,
    # then fall back to .claude/skills/ in the source repo (editable install).
    pkg_skills = importlib.resources.files("wpf_agent") / "_skills"
    if not pkg_skills.is_dir():
        # editable install: package is at src/wpf_agent/, repo root is ../../
        repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
        pkg_skills = repo_root / ".claude" / "skills"

    if not pkg_skills.is_dir():
        click.echo("Bundled skills not found in package.", err=True)
        sys.exit(1)

    # Build list of destination directories
    dest_dirs = [dest_root / ".claude" / "skills"]
    if github:
        dest_dirs.append(dest_root / ".github" / "skills")

    for dest_skills in dest_dirs:
        installed = []
        for skill_dir in sorted(pkg_skills.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_name = skill_dir.name
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                continue

            out_dir = dest_skills / skill_name
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / "SKILL.md"

            # Read from package resource and write
            out_file.write_text(skill_md.read_text(encoding="utf-8"), encoding="utf-8")
            installed.append(skill_name)

        if installed:
            click.echo(f"Installed {len(installed)} skills into {dest_skills}/:")
            for name in installed:
                click.echo(f"  /{name}")
        else:
            click.echo("No skills found to install.", err=True)
            sys.exit(1)

    # ── Update CLAUDE.md with wpf-agent guide ──
    if not no_claude_md:
        _update_claude_md(dest_root, yes)


_MARKER_START = "<!-- wpf-agent:start -->"
_MARKER_END = "<!-- wpf-agent:end -->"


def _load_snippet() -> str:
    """Load the CLAUDE.md snippet from package resources or source tree."""
    import importlib.resources

    # Try wheel-bundled file first
    pkg_file = importlib.resources.files("wpf_agent") / "_claude_md_snippet.md"
    try:
        return pkg_file.read_text(encoding="utf-8")
    except (FileNotFoundError, TypeError):
        pass

    # Editable install: source tree
    src_path = pathlib.Path(__file__).resolve().parent / "_claude_md_snippet.md"
    if src_path.is_file():
        return src_path.read_text(encoding="utf-8")

    raise FileNotFoundError("wpf-agent CLAUDE.md snippet not found in package.")


def _update_claude_md(dest_root: pathlib.Path, skip_confirm: bool) -> None:
    """Append or update the wpf-agent section in CLAUDE.md."""
    snippet = _load_snippet()
    claude_md = dest_root / "CLAUDE.md"

    if claude_md.is_file():
        content = claude_md.read_text(encoding="utf-8")
        start_idx = content.find(_MARKER_START)
        end_idx = content.find(_MARKER_END)

        if start_idx != -1 and end_idx != -1:
            # Marker found — replace between markers (inclusive)
            end_idx += len(_MARKER_END)
            # Preserve trailing newline after end marker
            if end_idx < len(content) and content[end_idx] == "\n":
                end_idx += 1
            new_content = content[:start_idx] + snippet.rstrip("\n") + "\n" + content[end_idx:]
            action = "update"
        else:
            # No markers — append to end
            new_content = content.rstrip("\n") + "\n\n" + snippet.rstrip("\n") + "\n"
            action = "append"
    else:
        new_content = snippet.rstrip("\n") + "\n"
        action = "create"

    # Confirm with user before writing
    if not skip_confirm:
        action_msg = {
            "create": f"Create {claude_md} with wpf-agent guide?",
            "append": f"Append wpf-agent guide to {claude_md}?",
            "update": f"Update wpf-agent guide in {claude_md}?",
        }
        try:
            if not click.confirm(action_msg[action], default=True):
                click.echo("Skipped CLAUDE.md update.")
                return
        except click.Abort:
            # Non-interactive (no TTY) — accept by default
            click.echo(f"(non-interactive) Auto-accepting: {action_msg[action]}")
            pass

    claude_md.write_text(new_content, encoding="utf-8")
    action_past = {"create": "Created", "append": "Appended to", "update": "Updated"}
    click.echo(f"{action_past[action]} {claude_md} with wpf-agent guide.")


# ── mcp-serve ─────────────────────────────────────────────────────

@main.command("mcp-serve")
def mcp_serve():
    """Start the MCP server (stdio transport for Claude Code)."""
    from wpf_agent.mcp.server import run_server
    run_server()


# ── profiles ──────────────────────────────────────────────────────

@main.group()
def profiles():
    """Manage target app profiles."""
    pass


@profiles.command("list")
def profiles_list():
    """List all profiles."""
    from wpf_agent.config import ProfileStore
    store = ProfileStore()
    for p in store.list():
        click.echo(f"  {p.name}")
        if p.match:
            click.echo(f"    match: {p.match.model_dump(exclude_none=True)}")
        if p.launch:
            click.echo(f"    launch: {p.launch.exe} {p.launch.args}")


@profiles.command("add")
@click.option("--name", required=True, help="Profile name")
@click.option("--process", default=None, help="Process name (e.g. MyApp.exe)")
@click.option("--title-re", default=None, help="Window title regex")
@click.option("--exe", default=None, help="EXE path for launch mode")
@click.option("--pid", default=None, type=int, help="Process ID")
def profiles_add(name, process, title_re, exe, pid):
    """Add a new profile."""
    from wpf_agent.config import Profile, ProfileLaunch, ProfileMatch, ProfileStore

    match = ProfileMatch(pid=pid, process=process, title_re=title_re, exe=exe if not exe else None)
    launch = ProfileLaunch(exe=exe) if exe else None
    # If exe provided as match target (no launch), set it in match
    if exe and not launch:
        match.exe = exe

    profile = Profile(name=name, match=match, launch=launch)
    store = ProfileStore()
    store.add(profile)
    click.echo(f"Added profile '{name}'")


@profiles.command("remove")
@click.argument("name")
def profiles_remove(name):
    """Remove a profile."""
    from wpf_agent.config import ProfileStore
    store = ProfileStore()
    if store.remove(name):
        click.echo(f"Removed profile '{name}'")
    else:
        click.echo(f"Profile '{name}' not found", err=True)


@profiles.command("edit")
@click.argument("name")
@click.option("--process", default=None)
@click.option("--title-re", default=None)
@click.option("--exe", default=None)
@click.option("--pid", default=None, type=int)
def profiles_edit(name, process, title_re, exe, pid):
    """Edit an existing profile's match settings."""
    from wpf_agent.config import ProfileMatch, ProfileStore

    store = ProfileStore()
    profile = store.get(name)
    if profile is None:
        click.echo(f"Profile '{name}' not found", err=True)
        return
    if profile.match is None:
        profile.match = ProfileMatch()
    if process is not None:
        profile.match.process = process
    if title_re is not None:
        profile.match.title_re = title_re
    if exe is not None:
        profile.match.exe = exe
    if pid is not None:
        profile.match.pid = pid
    store.update(profile)
    click.echo(f"Updated profile '{name}'")


# ── personas ──────────────────────────────────────────────────────

@main.group()
def personas():
    """Manage usability-test persona presets."""
    pass


@personas.command("list")
def personas_list():
    """List all persona presets."""
    from wpf_agent.config import PersonaStore
    store = PersonaStore()
    for p in store.list():
        click.echo(f"  {p.name}: {p.description}")


@personas.command("add")
@click.option("--name", required=True, help="Persona preset name")
@click.option("--description", required=True, help="Persona description text")
def personas_add(name, description):
    """Add a new persona preset."""
    from wpf_agent.config import Persona, PersonaStore
    store = PersonaStore()
    store.add(Persona(name=name, description=description))
    click.echo(f"Added persona '{name}'")


@personas.command("remove")
@click.argument("name")
def personas_remove(name):
    """Remove a persona preset."""
    from wpf_agent.config import PersonaStore
    store = PersonaStore()
    if store.remove(name):
        click.echo(f"Removed persona '{name}'")
    else:
        click.echo(f"Persona '{name}' not found", err=True)


@personas.command("edit")
@click.argument("name")
@click.option("--description", required=True, help="New persona description text")
def personas_edit(name, description):
    """Edit an existing persona preset's description."""
    from wpf_agent.config import PersonaStore
    store = PersonaStore()
    persona = store.get(name)
    if persona is None:
        click.echo(f"Persona '{name}' not found", err=True)
        return
    persona.description = description
    store.update(persona)
    click.echo(f"Updated persona '{name}'")


# ── run / attach / launch ────────────────────────────────────────

@main.command()
@click.option("--profile", required=True, help="Profile name from profiles.json")
def run(profile):
    """Run the agent loop with a profile (interactive mode)."""
    from wpf_agent.config import ProfileStore
    from wpf_agent.core.session import Session
    from wpf_agent.core.target import TargetRegistry

    store = ProfileStore()
    prof = store.get(profile)
    if prof is None:
        click.echo(f"Profile '{profile}' not found", err=True)
        sys.exit(1)

    registry = TargetRegistry.get_instance()
    tid, target = registry.resolve_profile(prof)
    click.echo(f"Resolved: {target} (target_id={tid})")

    session = Session()
    session.start()
    click.echo(f"Session: {session.session_id}")
    click.echo("Target is connected. Use MCP tools via Claude Code or run scenarios.")


@main.command()
@click.option("--pid", required=True, type=int, help="Process ID to attach to")
def attach(pid):
    """Attach to a running process by PID."""
    from wpf_agent.core.target import TargetRegistry

    registry = TargetRegistry.get_instance()
    tid, target = registry.resolve({"pid": pid})
    click.echo(f"Attached: {target} (target_id={tid})")


@main.command()
@click.option("--exe", required=True, help="Path to executable")
@click.argument("args", nargs=-1)
def launch(exe, args):
    """Launch an application and connect."""
    from wpf_agent.core.target import TargetRegistry

    registry = TargetRegistry.get_instance()
    tid, target = registry.resolve({"exe": exe, "args": list(args)})
    click.echo(f"Launched: {target} (target_id={tid})")


# ── ui ────────────────────────────────────────────────────────────


def _resolve_ui_target(pid, title_re):
    """Resolve a target from --pid or --title-re CLI options."""
    from wpf_agent.core.target import TargetRegistry

    if not pid and not title_re:
        click.echo("Specify --pid or --title-re", err=True)
        sys.exit(1)

    registry = TargetRegistry.get_instance()
    spec = {}
    if pid:
        spec["pid"] = pid
    elif title_re:
        spec["title_re"] = title_re
    _, target = registry.resolve(spec)
    return target


def _build_selector(aid, name, control_type):
    """Build a Selector from --aid, --name, --control-type CLI options."""
    from wpf_agent.uia.selector import Selector

    if not aid and not name and not control_type:
        click.echo("Specify at least --aid, --name, or --control-type", err=True)
        sys.exit(1)

    return Selector(automation_id=aid, name=name, control_type=control_type)


@main.group("ui")
@click.option("--no-guard", is_flag=True, default=False, help="Skip mouse-movement guard check")
@click.pass_context
def ui_cmd(ctx, no_guard):
    """Direct UI operations (for Claude Code to drive the UI loop)."""
    ctx.ensure_object(dict)
    ctx.obj["no_guard"] = no_guard


def _run_guard(ctx, command_name: str) -> None:
    """Run guard check; on interrupt, print JSON and exit with code 2."""
    if ctx.obj.get("no_guard"):
        return
    from wpf_agent.core.errors import UserInterruptError
    from wpf_agent.ui_guard import check_guard

    try:
        check_guard(command_name)
    except UserInterruptError as exc:
        result = {
            "interrupted": True,
            "reason": exc.reason,
            "detail": exc.detail,
            "command": command_name,
            "action": "Run 'wpf-agent ui resume' to continue.",
        }
        click.echo(json.dumps(result, ensure_ascii=False))
        sys.exit(2)


@ui_cmd.command("screenshot")
@click.option("--pid", default=None, type=int, help="Target process ID")
@click.option("--title-re", default=None, help="Window title regex")
@click.option("--save", "save_path", default=None, help="Save path for screenshot PNG")
def ui_screenshot(pid, title_re, save_path):
    """Capture a screenshot of the target window."""
    from wpf_agent.uia.screenshot import capture_screenshot

    target = _resolve_ui_target(pid, title_re)
    dest = pathlib.Path(save_path) if save_path else None
    result_path = capture_screenshot(target=target, save_path=dest)
    click.echo(str(result_path))


@ui_cmd.command("controls")
@click.option("--pid", default=None, type=int, help="Target process ID")
@click.option("--title-re", default=None, help="Window title regex")
@click.option("--depth", default=4, type=int, help="Traversal depth")
@click.option("--type-filter", default=None, help="Filter by control_type (comma-separated, e.g. Button,Edit,ComboBox)")
@click.option("--name-filter", default=None, help="Filter by name (substring match, case-insensitive)")
@click.option("--has-name", is_flag=True, default=False, help="Only show controls with non-empty name")
@click.option("--has-aid", is_flag=True, default=False, help="Only show controls with non-empty automation_id")
@click.option("--brief", is_flag=True, default=False, help="Compact table output instead of JSON")
def ui_controls(pid, title_re, depth, type_filter, name_filter, has_name, has_aid, brief):
    """List UI controls as JSON (or brief table with --brief)."""
    import re

    from wpf_agent.uia.engine import UIAEngine

    target = _resolve_ui_target(pid, title_re)
    controls = UIAEngine.list_controls(target, depth=depth)

    # Apply filters
    if type_filter:
        allowed_types = {t.strip() for t in type_filter.split(",")}
        controls = [c for c in controls if c.get("control_type", "") in allowed_types]

    if name_filter:
        pattern = re.compile(re.escape(name_filter), re.IGNORECASE)
        controls = [c for c in controls if pattern.search(c.get("name", ""))]

    if has_name:
        controls = [c for c in controls if c.get("name", "").strip()]

    if has_aid:
        controls = [c for c in controls if c.get("automation_id", "").strip()]

    if brief:
        for c in controls:
            ct = c.get("control_type", "")
            aid = c.get("automation_id", "")
            name = c.get("name", "")
            r = c.get("rect", {})
            rect_str = f"({r.get('left', 0)},{r.get('top', 0)},{r.get('right', 0)},{r.get('bottom', 0)})"
            click.echo(f"{ct:20s} aid={aid:25s} name={name:35s} rect={rect_str}")
    else:
        click.echo(json.dumps(controls, ensure_ascii=False, indent=2))


@ui_cmd.command("focus")
@click.option("--pid", default=None, type=int, help="Target process ID")
@click.option("--title-re", default=None, help="Window title regex")
@click.pass_context
def ui_focus(ctx, pid, title_re):
    """Focus the target window."""
    _run_guard(ctx, "focus")
    from wpf_agent.uia.engine import UIAEngine

    target = _resolve_ui_target(pid, title_re)
    result = UIAEngine.focus_window(target)
    click.echo(json.dumps(result, ensure_ascii=False))


@ui_cmd.command("click")
@click.option("--pid", default=None, type=int, help="Target process ID")
@click.option("--title-re", default=None, help="Window title regex")
@click.option("--aid", default=None, help="Automation ID")
@click.option("--name", default=None, help="Element name")
@click.option("--control-type", default=None, help="Control type")
@click.pass_context
def ui_click(ctx, pid, title_re, aid, name, control_type):
    """Click a UI element."""
    _run_guard(ctx, "click")
    from wpf_agent.uia.engine import UIAEngine

    target = _resolve_ui_target(pid, title_re)
    selector = _build_selector(aid, name, control_type)
    result = UIAEngine.click(target, selector)
    click.echo(json.dumps(result, ensure_ascii=False))


@ui_cmd.command("type")
@click.option("--pid", default=None, type=int, help="Target process ID")
@click.option("--title-re", default=None, help="Window title regex")
@click.option("--aid", default=None, help="Automation ID")
@click.option("--name", default=None, help="Element name")
@click.option("--control-type", default=None, help="Control type")
@click.option("--text", required=True, help="Text to type")
@click.option("--clear/--no-clear", default=True, help="Clear field before typing")
@click.pass_context
def ui_type(ctx, pid, title_re, aid, name, control_type, text, clear):
    """Type text into a UI element."""
    _run_guard(ctx, "type")
    from wpf_agent.uia.engine import UIAEngine

    target = _resolve_ui_target(pid, title_re)
    selector = _build_selector(aid, name, control_type)
    result = UIAEngine.type_text(target, selector, text, clear=clear)
    click.echo(json.dumps(result, ensure_ascii=False))


@ui_cmd.command("toggle")
@click.option("--pid", default=None, type=int, help="Target process ID")
@click.option("--title-re", default=None, help="Window title regex")
@click.option("--aid", default=None, help="Automation ID")
@click.option("--name", default=None, help="Element name")
@click.option("--control-type", default=None, help="Control type")
@click.option("--state", default=None, type=bool, help="Target state (true/false)")
@click.pass_context
def ui_toggle(ctx, pid, title_re, aid, name, control_type, state):
    """Toggle a checkbox or toggle button."""
    _run_guard(ctx, "toggle")
    from wpf_agent.uia.engine import UIAEngine

    target = _resolve_ui_target(pid, title_re)
    selector = _build_selector(aid, name, control_type)
    result = UIAEngine.toggle(target, selector, state=state)
    click.echo(json.dumps(result, ensure_ascii=False))


@ui_cmd.command("select-combo")
@click.option("--pid", default=None, type=int, help="Target process ID")
@click.option("--title-re", default=None, help="Window title regex")
@click.option("--aid", default=None, help="Automation ID")
@click.option("--name", default=None, help="Element name")
@click.option("--control-type", default=None, help="Control type")
@click.option("--item", required=True, help="Item text to select")
@click.pass_context
def ui_select_combo(ctx, pid, title_re, aid, name, control_type, item):
    """Select an item from a ComboBox."""
    _run_guard(ctx, "select-combo")
    from wpf_agent.uia.engine import UIAEngine

    target = _resolve_ui_target(pid, title_re)
    selector = _build_selector(aid, name, control_type)
    result = UIAEngine.select_combo(target, selector, item)
    click.echo(json.dumps(result, ensure_ascii=False))


@ui_cmd.command("read")
@click.option("--pid", default=None, type=int, help="Target process ID")
@click.option("--title-re", default=None, help="Window title regex")
@click.option("--aid", default=None, help="Automation ID")
@click.option("--name", default=None, help="Element name")
@click.option("--control-type", default=None, help="Control type")
def ui_read(pid, title_re, aid, name, control_type):
    """Read text from a UI element."""
    from wpf_agent.uia.engine import UIAEngine

    target = _resolve_ui_target(pid, title_re)
    selector = _build_selector(aid, name, control_type)
    result = UIAEngine.read_text(target, selector)
    click.echo(json.dumps(result, ensure_ascii=False))


@ui_cmd.command("state")
@click.option("--pid", default=None, type=int, help="Target process ID")
@click.option("--title-re", default=None, help="Window title regex")
@click.option("--aid", default=None, help="Automation ID")
@click.option("--name", default=None, help="Element name")
@click.option("--control-type", default=None, help="Control type")
def ui_state(pid, title_re, aid, name, control_type):
    """Get state of a UI element (enabled, visible, value, etc.)."""
    from wpf_agent.uia.engine import UIAEngine

    target = _resolve_ui_target(pid, title_re)
    selector = _build_selector(aid, name, control_type)
    result = UIAEngine.get_state(target, selector)
    click.echo(json.dumps(result, ensure_ascii=False))


@ui_cmd.command("resume")
def ui_resume():
    """Clear the pause state so UI commands can run again."""
    from wpf_agent.ui_guard import clear_pause, get_pause_info

    info = get_pause_info()
    existed = clear_pause()
    result = {"resumed": existed, "previous_pause": info}
    click.echo(json.dumps(result, ensure_ascii=False))


@ui_cmd.command("status")
def ui_status():
    """Show current guard state (active or paused)."""
    from wpf_agent.ui_guard import get_pause_info, is_paused

    if is_paused():
        info = get_pause_info() or {}
        result = {"state": "paused", **info}
    else:
        result = {"state": "active"}
    click.echo(json.dumps(result, ensure_ascii=False))


@ui_cmd.command("windows")
@click.option("--brief", is_flag=True, default=False, help="Compact table output instead of JSON")
def ui_windows(brief):
    """List visible top-level windows (PID, title, handle)."""
    from wpf_agent.uia.engine import UIAEngine

    windows = UIAEngine.list_windows()
    # Filter to visible windows with a title
    windows = [w for w in windows if w.get("visible") and w.get("title", "").strip()]

    if brief:
        for w in windows:
            click.echo(f"pid={w['pid']:<8d} handle={w['handle']:<10d} title={w['title']}")
    else:
        click.echo(json.dumps(windows, ensure_ascii=False, indent=2))


@ui_cmd.command("alive")
@click.option("--pid", default=None, type=int, help="Process ID to check")
@click.option("--process", default=None, help="Process name to find (e.g. MyApp or MyApp.exe)")
@click.option("--brief", is_flag=True, default=False, help="Output PID(s) only, one per line")
def ui_alive(pid, process, brief):
    """Check if a process is running (by PID or process name).

    With --brief, outputs only PID number(s) for easy scripting.
    """
    import ctypes

    if not pid and not process:
        click.echo("Specify --pid or --process", err=True)
        sys.exit(1)

    if process:
        # Search by process name
        import subprocess

        name = process if process.lower().endswith(".exe") else process + ".exe"
        proc = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True,
        )
        matches = []
        for line in proc.stdout.strip().split("\n"):
            parts = line.strip().strip('"').split('","')
            if len(parts) >= 2 and parts[0].lower() == name.lower():
                matches.append({"pid": int(parts[1]), "process": parts[0]})

        if brief:
            for m in matches:
                click.echo(m["pid"])
        else:
            result = {"process": name, "alive": len(matches) > 0, "matches": matches}
            click.echo(json.dumps(result, ensure_ascii=False))
    else:
        # Check by PID
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            exit_code = ctypes.c_ulong()
            kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            kernel32.CloseHandle(handle)
            STILL_ACTIVE = 259
            alive = exit_code.value == STILL_ACTIVE
        else:
            alive = False

        if brief:
            if alive:
                click.echo(pid)
        else:
            result = {"pid": pid, "alive": alive}
            click.echo(json.dumps(result, ensure_ascii=False))


@ui_cmd.command("close")
@click.option("--pid", required=True, type=int, help="PID of the process to close")
def ui_close(pid):
    """Gracefully close a process launched by wpf-agent.

    Only processes started via `wpf-agent launch` can be closed.
    Sends WM_CLOSE to the main window (does not force-kill).
    """
    import ctypes

    from wpf_agent.core.target import is_launched_pid, remove_launched_pid

    if not is_launched_pid(pid):
        click.echo(
            json.dumps({"closed": False, "error": "PID was not launched by wpf-agent"}, ensure_ascii=False)
        )
        sys.exit(1)

    # Find the main window for this PID and send WM_CLOSE
    user32 = ctypes.windll.user32
    WM_CLOSE = 0x0010
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))

    closed_hwnds = []

    def _cb(hwnd, _lparam):
        win_pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(win_pid))
        if win_pid.value == pid and user32.IsWindowVisible(hwnd):
            # Check it has a title (main window, not helper)
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
                closed_hwnds.append(hwnd)
        return True

    user32.EnumWindows(WNDENUMPROC(_cb), 0)

    if closed_hwnds:
        remove_launched_pid(pid)
        click.echo(json.dumps({"closed": True, "pid": pid, "windows": len(closed_hwnds)}, ensure_ascii=False))
    else:
        click.echo(json.dumps({"closed": False, "pid": pid, "error": "No visible window found"}, ensure_ascii=False))
        sys.exit(1)


@ui_cmd.command("init-session")
@click.option("--prefix", default="session", help="Session directory prefix (e.g. usability, explore)")
def ui_init_session(prefix):
    """Create a timestamped session workspace under artifacts/sessions/.

    Returns the created directory path as JSON.
    Example: wpf-agent ui init-session --prefix usability
    → artifacts/sessions/usability_20260301_153045/
    """
    import pathlib as _pl

    from wpf_agent.constants import SESSION_DIR

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    session_dir = _pl.Path(SESSION_DIR) / f"{prefix}_{timestamp}"
    session_dir.mkdir(parents=True, exist_ok=True)
    click.echo(json.dumps({"path": str(session_dir)}, ensure_ascii=False))


# ── scenario ──────────────────────────────────────────────────────

@main.group()
def scenario():
    """Scenario test commands."""
    pass


@scenario.command("run")
@click.option("--file", "file_path", required=True, help="Path to scenario YAML")
@click.option("--profile", default=None, help="Override profile name")
def scenario_run(file_path, profile):
    """Run a scenario test from a YAML file."""
    from wpf_agent.core.session import Session
    from wpf_agent.testing.scenario import Scenario, run_scenario
    from wpf_agent.tickets.generator import generate_ticket_from_scenario

    scenario_obj = Scenario.from_file(pathlib.Path(file_path))
    if profile:
        scenario_obj.profile = profile

    session = Session()
    click.echo(f"Running scenario '{scenario_obj.id}'...")
    result = run_scenario(scenario_obj, session=session)

    if result.passed:
        click.echo(f"PASSED ({result.steps_run} steps)")
    else:
        click.echo(f"FAILED at step {result.steps_run}")
        for f in result.failures:
            click.echo(f"  - {f}")

        ticket_dir = generate_ticket_from_scenario(
            session=session,
            target=None,
            scenario_id=scenario_obj.id,
            failures=result.failures,
            profile_name=profile or scenario_obj.profile,
        )
        click.echo(f"Ticket generated: {ticket_dir}")


# ── random ────────────────────────────────────────────────────────

@main.group("random")
def random_cmd():
    """Random (exploratory) test commands."""
    pass


@random_cmd.command("run")
@click.option("--profile", default=None, help="Profile name")
@click.option("--config", "config_file", default=None, help="Path to random test config YAML")
@click.option("--max-steps", default=None, type=int, help="Maximum exploration steps (overrides config)")
@click.option("--seed", default=None, type=int, help="Random seed (overrides config)")
def random_run(profile, config_file, max_steps, seed):
    """Run random exploratory testing.

    Configuration can be provided via --config YAML file, CLI options, or both.
    CLI options override values from the config file.
    """
    from wpf_agent.config import ProfileStore
    from wpf_agent.core.session import Session
    from wpf_agent.core.target import TargetRegistry
    from wpf_agent.testing.random_tester import RandomConfig, run_random_test
    from wpf_agent.tickets.generator import generate_ticket_from_random

    # Load config from YAML or use defaults
    if config_file:
        config = RandomConfig.from_file(pathlib.Path(config_file))
    else:
        config = RandomConfig()

    # CLI overrides
    if max_steps is not None:
        config.max_steps = max_steps
    if seed is not None:
        config.seed = seed

    # Resolve profile: CLI > config file > error
    profile_name = profile or config.profile
    if not profile_name:
        click.echo("Specify --profile or set profile in config YAML", err=True)
        sys.exit(1)

    store = ProfileStore()
    prof = store.get(profile_name)
    if prof is None:
        click.echo(f"Profile '{profile_name}' not found", err=True)
        sys.exit(1)

    # Use profile safety if config file didn't override
    if not config_file:
        config.safety = prof.safety

    registry = TargetRegistry.get_instance()
    _, target = registry.resolve_profile(prof)
    session = Session()
    click.echo(f"Starting random test (seed will be logged)...")
    result = run_random_test(target, config, session=session)

    click.echo(f"Completed: {result.steps_run} steps, seed={result.seed}")
    if result.passed:
        click.echo("PASSED — no failures detected")
    else:
        click.echo(f"FAILED — {len(result.failures)} failure(s)")
        for f in result.failures:
            click.echo(f"  - Step {f.get('step')}: {f.get('oracle', f.get('error', ''))}")

        ticket_dir = generate_ticket_from_random(
            session=session,
            target=target,
            seed=result.seed,
            failures=result.failures,
            profile_name=profile,
        )
        click.echo(f"Ticket generated: {ticket_dir}")


# ── explore ───────────────────────────────────────────────────────

@main.group("explore")
def explore_cmd():
    """AI-guided exploratory test commands."""
    pass


@explore_cmd.command("run")
@click.option("--profile", default=None, help="Profile name")
@click.option("--goal", default="", help="Exploration goal (e.g. '全画面を探索してクラッシュを探す')")
@click.option("--config", "config_file", default=None, help="Path to explore config YAML")
@click.option("--max-steps", default=None, type=int, help="Maximum exploration steps (overrides config)")
@click.option("--model", default=None, help="Claude model to use (overrides config)")
def explore_run(profile, goal, config_file, max_steps, model):
    """Run AI-guided exploratory testing.

    Uses Claude Vision to analyze screenshots and decide actions.
    Requires ANTHROPIC_API_KEY environment variable.
    """
    from wpf_agent.config import ProfileStore
    from wpf_agent.core.session import Session
    from wpf_agent.core.target import TargetRegistry
    from wpf_agent.testing.explorer import ExploreConfig, run_explore_test
    from wpf_agent.tickets.generator import generate_ticket_from_explore

    # Load config from YAML or use defaults
    if config_file:
        config = ExploreConfig.from_file(pathlib.Path(config_file))
    else:
        config = ExploreConfig()

    # CLI overrides
    if max_steps is not None:
        config.max_steps = max_steps
    if goal:
        config.goal = goal
    if model:
        config.model = model

    # Resolve profile: CLI > config file > error
    profile_name = profile or config.profile
    if not profile_name:
        click.echo("Specify --profile or set profile in config YAML", err=True)
        sys.exit(1)

    store = ProfileStore()
    prof = store.get(profile_name)
    if prof is None:
        click.echo(f"Profile '{profile_name}' not found", err=True)
        sys.exit(1)

    # Use profile safety if config file didn't override
    if not config_file:
        config.safety = prof.safety

    registry = TargetRegistry.get_instance()
    _, target = registry.resolve_profile(prof)
    session = Session()
    click.echo(f"Starting AI-guided exploration (model={config.model}, max_steps={config.max_steps})...")
    if config.goal:
        click.echo(f"Goal: {config.goal}")

    result = run_explore_test(target, config, session=session)

    click.echo(f"Completed: {result.steps_run} steps")
    if result.passed:
        click.echo("PASSED — no failures detected")
    else:
        click.echo(f"FAILED — {len(result.failures)} failure(s)")
        for f in result.failures:
            click.echo(f"  - Step {f.get('step')}: {f.get('oracle', f.get('error', ''))}")

        ticket_dir = generate_ticket_from_explore(
            session=session,
            target=target,
            failures=result.failures,
            goal=config.goal,
            profile_name=profile_name,
        )
        click.echo(f"Ticket generated: {ticket_dir}")


# ── verify ────────────────────────────────────────────────────────

@main.command()
@click.option("--exe", required=True, help="Path to app executable")
@click.option("--args", "app_args", default="", help="App arguments (space-separated)")
@click.option("--title-re", default=None, help="Window title regex for detection")
@click.option("--spec", default=None, help="Path to verification spec YAML")
@click.option("--timeout", default=5000, type=int, help="Startup wait ms")
@click.option("--no-close", is_flag=True, help="Don't close app after verification")
def verify(exe, app_args, title_re, spec, timeout, no_close):
    """Verify a built app: launch, smoke-test, check elements, and report."""
    from wpf_agent.core.session import Session
    from wpf_agent.testing.verifier import VerifyConfig, run_verify

    if spec:
        config = VerifyConfig.from_file(pathlib.Path(spec))
        # CLI overrides
        if exe:
            config.exe = exe
        if title_re:
            config.title_re = title_re
    else:
        config = VerifyConfig(exe=exe, title_re=title_re or "")

    if app_args:
        config.args = app_args.split()
    config.startup_wait_ms = timeout
    if no_close:
        config.auto_close = False

    session = Session()
    click.echo(f"Verifying: {config.exe}")
    click.echo(f"Session: {session.session_id}")

    result = run_verify(config, session=session)

    # Display results
    for c in result.checks:
        status = click.style("PASS", fg="green") if c.passed else click.style("FAIL", fg="red")
        click.echo(f"  [{status}] {c.name}: {c.message}")

    click.echo()
    if result.passed:
        click.echo(click.style("VERIFICATION PASSED", fg="green", bold=True))
    else:
        click.echo(click.style("VERIFICATION FAILED", fg="red", bold=True))
        failed = [c for c in result.checks if not c.passed]
        click.echo(f"  {len(failed)} check(s) failed")

    click.echo(f"\nSession: {result.session_id}")
    click.echo(f"Controls found: {result.controls_found}")
    if result.screenshot_path:
        click.echo(f"Screenshot: {result.screenshot_path}")


# ── replay ────────────────────────────────────────────────────────

@main.command()
@click.option("--file", "file_path", required=True, help="Path to actions JSON")
@click.option("--profile", default=None, help="Profile name")
@click.option("--pid", default=None, type=int, help="Target PID")
@click.option("--title-re", default=None, help="Window title regex")
def replay(file_path, profile, pid, title_re):
    """Replay a recorded action sequence (AI-free)."""
    from wpf_agent.config import ProfileStore
    from wpf_agent.core.session import Session
    from wpf_agent.core.target import TargetRegistry
    from wpf_agent.runner.replay import load_actions, replay_actions

    registry = TargetRegistry.get_instance()
    if profile:
        store = ProfileStore()
        prof = store.get(profile)
        if prof is None:
            click.echo(f"Profile '{profile}' not found", err=True)
            sys.exit(1)
        _, target = registry.resolve_profile(prof)
    elif pid:
        _, target = registry.resolve({"pid": pid})
    elif title_re:
        _, target = registry.resolve({"title_re": title_re})
    else:
        click.echo("Specify --profile, --pid, or --title-re", err=True)
        sys.exit(1)

    actions = load_actions(pathlib.Path(file_path))
    session = Session()
    click.echo(f"Replaying {len(actions)} actions...")
    results = replay_actions(actions, target, session=session)

    errors = [r for r in results if "error" in r]
    click.echo(f"Done: {len(results)} steps, {len(errors)} errors")
    for e in errors:
        click.echo(f"  - Step {e['step']}: {e['error']}")


# ── tickets ───────────────────────────────────────────────────────

@main.group()
def tickets():
    """Ticket management commands."""
    pass


@tickets.command("open")
@click.option("--last", is_flag=True, help="Open the most recent ticket")
@click.option("--session", "session_id", default=None, help="Session ID")
def tickets_open(last, session_id):
    """Open a generated ticket."""
    from wpf_agent.constants import TICKET_DIR

    ticket_base = pathlib.Path(TICKET_DIR)
    if not ticket_base.exists():
        click.echo("No tickets found", err=True)
        return

    if last:
        # Find the most recent ticket
        all_tickets = sorted(ticket_base.rglob("ticket.md"))
        if not all_tickets:
            click.echo("No tickets found", err=True)
            return
        ticket_path = all_tickets[-1]
    elif session_id:
        session_dir = ticket_base / session_id
        tickets_in_session = sorted(session_dir.rglob("ticket.md"))
        if not tickets_in_session:
            click.echo(f"No tickets found for session {session_id}", err=True)
            return
        ticket_path = tickets_in_session[-1]
    else:
        # List all tickets
        for md in sorted(ticket_base.rglob("ticket.md")):
            click.echo(f"  {md.parent.name}: {md}")
        return

    click.echo(ticket_path.read_text(encoding="utf-8"))


@tickets.command("create")
@click.option("--title", required=True, help="Ticket title")
@click.option("--summary", required=True, help="Summary (1-2 sentences)")
@click.option("--actual", "--actual-result", required=True, help="Actual result")
@click.option("--expected", "--expected-result", required=True, help="Expected result")
@click.option("--repro", "--repro-steps", multiple=True, help="Repro step (repeat for multiple)")
@click.option("--evidence", multiple=True, help="Evidence file path (repeat for multiple)")
@click.option("--hypothesis", "--root-cause", default="", help="Root cause hypothesis")
@click.option("--pid", default=None, type=int, help="Target PID (added to environment)")
@click.option("--process", default=None, help="Target process name (added to environment)")
@click.option("--profile", default=None, help="Profile name (added to environment)")
def tickets_create(title, summary, actual, expected, repro, evidence, hypothesis, pid, process, profile):
    """Create a ticket directory with ticket.md and ticket.json."""
    import shutil
    import time

    from wpf_agent.constants import TICKET_DIR
    from wpf_agent.tickets.templates import default_environment, render_ticket_md

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    ticket_dir = pathlib.Path(TICKET_DIR) / f"TICKET-{timestamp}"
    ticket_dir.mkdir(parents=True, exist_ok=True)

    env = default_environment()
    if pid:
        env["Target PID"] = str(pid)
    if process:
        env["Target Process"] = process
    if profile:
        env["Profile"] = profile

    repro_steps = list(repro) if repro else []
    evidence_files = list(evidence) if evidence else []

    # Copy evidence files into ticket dir
    screens_dir = ticket_dir / "screens"
    for ef in evidence_files:
        src = pathlib.Path(ef)
        if src.exists():
            screens_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(screens_dir / src.name))

    # Rebuild evidence list relative to ticket dir
    packaged_evidence = []
    if screens_dir.exists():
        for p in sorted(screens_dir.iterdir()):
            packaged_evidence.append(f"screens/{p.name}")

    md = render_ticket_md(
        title=title,
        summary=summary,
        repro_steps=repro_steps,
        actual_result=actual,
        expected_result=expected,
        environment=env,
        evidence_files=packaged_evidence,
        root_cause_hypothesis=hypothesis,
    )
    (ticket_dir / "ticket.md").write_text(md, encoding="utf-8")

    ticket_data = {
        "title": title,
        "summary": summary,
        "repro_steps": repro_steps,
        "actual_result": actual,
        "expected_result": expected,
        "environment": env,
        "evidence_files": packaged_evidence,
        "root_cause_hypothesis": hypothesis,
        "timestamp": timestamp,
    }
    (ticket_dir / "ticket.json").write_text(
        json.dumps(ticket_data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    result = {
        "ticket_dir": str(ticket_dir),
        "ticket_md": str(ticket_dir / "ticket.md"),
        "ticket_json": str(ticket_dir / "ticket.json"),
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


@tickets.command("list-pending")
def tickets_list_pending():
    """List untriaged tickets (not yet in fix/ or wontfix/)."""
    from wpf_agent.constants import TICKET_DIR

    ticket_base = pathlib.Path(TICKET_DIR)
    if not ticket_base.exists():
        click.echo(json.dumps([], ensure_ascii=False))
        return

    # Directories that contain triaged tickets
    triaged_roots = {ticket_base / "fix", ticket_base / "wontfix"}

    pending = []
    for ticket_json in sorted(ticket_base.rglob("ticket.json")):
        # Skip tickets already under fix/ or wontfix/
        if any(ticket_json.is_relative_to(r) for r in triaged_roots if r.exists()):
            continue

        # Skip tickets that already have a triage decision in their JSON
        try:
            data = json.loads(ticket_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        if data.get("triage"):
            continue

        pending.append({
            "path": str(ticket_json.parent),
            "title": data.get("title", ""),
            "summary": data.get("summary", ""),
            "timestamp": data.get("timestamp", ""),
        })

    click.echo(json.dumps(pending, ensure_ascii=False, indent=2))


@tickets.command("triage")
@click.option("--ticket", required=True, help="Path to ticket directory")
@click.option(
    "--decision",
    required=True,
    type=click.Choice(["fix", "wontfix"], case_sensitive=False),
    help="Triage decision",
)
@click.option("--reason", default="", help="Reason for the decision")
def tickets_triage(ticket, decision, reason):
    """Triage a ticket: add decision and move to fix/ or wontfix/."""
    import shutil
    import time

    from wpf_agent.constants import TICKET_DIR

    ticket_dir = pathlib.Path(ticket)
    ticket_json_path = ticket_dir / "ticket.json"

    if not ticket_json_path.exists():
        click.echo(f"ticket.json not found in {ticket_dir}", err=True)
        sys.exit(1)

    # Update ticket.json with triage info
    try:
        data = json.loads(ticket_json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        click.echo(f"Failed to read ticket.json: {exc}", err=True)
        sys.exit(1)

    data["triage"] = {
        "decision": decision,
        "reason": reason,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    ticket_json_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    # Move ticket directory to fix/ or wontfix/
    dest_parent = pathlib.Path(TICKET_DIR) / decision
    dest_parent.mkdir(parents=True, exist_ok=True)
    dest = dest_parent / ticket_dir.name

    try:
        shutil.move(str(ticket_dir), str(dest))
    except (OSError, shutil.Error) as exc:
        click.echo(f"Failed to move ticket: {exc}", err=True)
        sys.exit(1)

    result = {
        "ticket": ticket_dir.name,
        "decision": decision,
        "reason": reason,
        "moved_to": str(dest),
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))
