"""Command-line interface for wpfautotester."""

from __future__ import annotations

import sys
from typing import Optional, Tuple

import click

from . import __version__
from .doctor import run_doctor
from .errors import EXIT_DOCTOR_FAILURE, EXIT_OK


@click.group()
@click.version_option(version=__version__, prog_name="wpfautotester")
def main() -> None:
    """wpfautotester — AI-driven WPF UI testing agent."""


@main.command()
@click.option(
    "--artifact-path",
    "artifact_paths",
    multiple=True,
    metavar="PATH",
    help="Artifact directory to verify (repeatable). Defaults to ./artifacts.",
)
@click.option(
    "--profile",
    "profile_path",
    default=None,
    metavar="FILE",
    help="Path to a JSON test-profile file to validate.",
)
def doctor(
    artifact_paths: Tuple[str, ...],
    profile_path: Optional[str],
) -> None:
    """Validate the environment setup for wpfautotester.

    Checks Python version, required tools, optional .NET availability,
    writable artifact paths, and profile file validity.

    Exits with code 0 when all required checks pass, or 10 when one or
    more required checks fail.
    """
    paths = list(artifact_paths) if artifact_paths else None
    report = run_doctor(artifact_paths=paths, profile_path=profile_path)

    _print_report(report)

    if report.passed:
        click.echo("\n✅  All checks passed — environment is ready.")
        sys.exit(EXIT_OK)
    else:
        click.echo(
            "\n❌  One or more checks failed. Fix the issues above and re-run "
            "`wpfautotester doctor`.",
            err=True,
        )
        sys.exit(EXIT_DOCTOR_FAILURE)


def _print_report(report) -> None:
    """Pretty-print the doctor report to stdout."""
    click.echo(f"wpfautotester doctor — environment check\n{'─' * 45}")
    for check in report.checks:
        icon = "✓" if check.passed else "✗"
        click.echo(f"  [{icon}] {check.name}: {check.message}")
        if check.hint:
            click.echo(f"       ↳ {check.hint}")
