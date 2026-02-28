"""CLI entry point — click-based commands."""

from __future__ import annotations

import json
import pathlib
import sys

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
    from wpf_agent.config import ProfileStore
    from wpf_agent.constants import SESSION_DIR, TICKET_DIR

    store = ProfileStore()
    store.ensure_default()
    click.echo(f"Created {store.path}")

    for d in [SESSION_DIR, TICKET_DIR]:
        pathlib.Path(d).mkdir(parents=True, exist_ok=True)
        click.echo(f"Created {d}/")

    click.echo("\nInitialization complete. Edit profiles.json to add your target apps.")
    click.echo("Then register the MCP server in Claude Code:")
    click.echo('  claude mcp add wpf-agent -- python -m wpf_agent mcp-serve')


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
