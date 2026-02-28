"""Doctor command — validates the runtime environment for wpfautotester."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

MIN_PYTHON = (3, 9)

# Tools that must be on PATH for full functionality
REQUIRED_TOOLS = ["python"]

# Optional tools whose absence is warned but not fatal
OPTIONAL_TOOLS = ["dotnet", "pwsh"]


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    hint: Optional[str] = None


@dataclass
class DoctorReport:
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def add(self, result: CheckResult) -> None:
        self.checks.append(result)


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_python_version() -> CheckResult:
    """Verify that the running Python meets the minimum version requirement."""
    current = sys.version_info[:2]
    ok = current >= MIN_PYTHON
    ver_str = f"{current[0]}.{current[1]}"
    min_str = f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}"
    if ok:
        return CheckResult(
            name="Python version",
            passed=True,
            message=f"Python {ver_str} ✓ (>= {min_str} required)",
        )
    return CheckResult(
        name="Python version",
        passed=False,
        message=f"Python {ver_str} is too old (need >= {min_str})",
        hint=f"Install Python {min_str}+ from https://python.org/downloads/",
    )


def check_required_tools() -> List[CheckResult]:
    """Check that every required tool is available on PATH."""
    results = []
    for tool in REQUIRED_TOOLS:
        path = shutil.which(tool)
        if path:
            results.append(
                CheckResult(
                    name=f"Tool: {tool}",
                    passed=True,
                    message=f"'{tool}' found at {path} ✓",
                )
            )
        else:
            results.append(
                CheckResult(
                    name=f"Tool: {tool}",
                    passed=False,
                    message=f"'{tool}' not found on PATH",
                    hint=f"Install '{tool}' and ensure it is added to your PATH.",
                )
            )
    return results


def check_optional_tools() -> List[CheckResult]:
    """Check optional tools and emit warnings (never fail the doctor run)."""
    results = []
    for tool in OPTIONAL_TOOLS:
        path = shutil.which(tool)
        if path:
            results.append(
                CheckResult(
                    name=f"Optional tool: {tool}",
                    passed=True,
                    message=f"'{tool}' found at {path} ✓",
                )
            )
        else:
            results.append(
                CheckResult(
                    name=f"Optional tool: {tool}",
                    passed=True,  # optional — does not fail
                    message=f"'{tool}' not found (optional)",
                    hint=(
                        f"Install '{tool}' if you need .NET / PowerShell integration."
                    ),
                )
            )
    return results


def check_dotnet() -> CheckResult:
    """Check whether the .NET runtime is available and report its version."""
    dotnet = shutil.which("dotnet")
    if dotnet is None:
        return CheckResult(
            name=".NET runtime",
            passed=True,  # optional
            message=".NET runtime not found (optional)",
            hint=(
                "Install .NET from https://dotnet.microsoft.com/download"
                " if your WPF application requires it."
            ),
        )
    try:
        result = subprocess.run(
            [dotnet, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        version = result.stdout.strip()
        return CheckResult(
            name=".NET runtime",
            passed=True,
            message=f".NET {version} found ✓",
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return CheckResult(
            name=".NET runtime",
            passed=True,  # optional — availability already indicated above
            message=f".NET found but version query failed: {exc}",
        )


def check_artifact_paths(paths: Optional[List[str]] = None) -> List[CheckResult]:
    """Verify that artifact directories exist (or can be created) and are writable."""
    if paths is None:
        paths = [os.path.join(os.getcwd(), "artifacts")]

    results = []
    for raw_path in paths:
        p = Path(raw_path)
        try:
            p.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass  # will be caught below

        if p.exists() and os.access(p, os.W_OK):
            results.append(
                CheckResult(
                    name=f"Artifact path: {p}",
                    passed=True,
                    message=f"'{p}' is writable ✓",
                )
            )
        elif not p.exists():
            results.append(
                CheckResult(
                    name=f"Artifact path: {p}",
                    passed=False,
                    message=f"'{p}' does not exist and could not be created",
                    hint=(
                        f"Create the directory manually: mkdir -p \"{p}\""
                    ),
                )
            )
        else:
            results.append(
                CheckResult(
                    name=f"Artifact path: {p}",
                    passed=False,
                    message=f"'{p}' exists but is not writable",
                    hint=f"Fix permissions: chmod u+w \"{p}\"",
                )
            )
    return results


def check_profile(profile_path: Optional[str] = None) -> CheckResult:
    """Validate that the test profile file (if given) exists and is non-empty JSON."""
    if profile_path is None:
        return CheckResult(
            name="Profile",
            passed=True,
            message="No profile specified (skipped)",
        )

    p = Path(profile_path)
    if not p.exists():
        return CheckResult(
            name="Profile",
            passed=False,
            message=f"Profile file not found: '{p}'",
            hint="Create the profile file or pass the correct path with --profile.",
        )
    if p.stat().st_size == 0:
        return CheckResult(
            name="Profile",
            passed=False,
            message=f"Profile file is empty: '{p}'",
            hint="Populate the profile with valid JSON before running tests.",
        )

    import json  # noqa: PLC0415

    try:
        with p.open() as fh:
            json.load(fh)
    except json.JSONDecodeError as exc:
        return CheckResult(
            name="Profile",
            passed=False,
            message=f"Profile file contains invalid JSON: {exc}",
            hint="Fix the JSON syntax in your profile file.",
        )

    return CheckResult(
        name="Profile",
        passed=True,
        message=f"Profile '{p}' is valid JSON ✓",
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_doctor(
    artifact_paths: Optional[List[str]] = None,
    profile_path: Optional[str] = None,
) -> DoctorReport:
    """Run all environment checks and return a :class:`DoctorReport`."""
    report = DoctorReport()

    report.add(check_python_version())
    for result in check_required_tools():
        report.add(result)
    for result in check_optional_tools():
        report.add(result)
    report.add(check_dotnet())
    for result in check_artifact_paths(artifact_paths):
        report.add(result)
    report.add(check_profile(profile_path))

    return report
