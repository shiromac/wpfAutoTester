"""Tests for wpfautotester.doctor module."""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch

import pytest

from wpfautotester.doctor import (
    CheckResult,
    DoctorReport,
    check_artifact_paths,
    check_dotnet,
    check_optional_tools,
    check_profile,
    check_python_version,
    check_required_tools,
    run_doctor,
)


# ---------------------------------------------------------------------------
# CheckResult / DoctorReport helpers
# ---------------------------------------------------------------------------


def test_doctor_report_passed_when_all_checks_pass():
    report = DoctorReport()
    report.add(CheckResult("a", True, "ok"))
    report.add(CheckResult("b", True, "ok"))
    assert report.passed is True


def test_doctor_report_fails_when_any_check_fails():
    report = DoctorReport()
    report.add(CheckResult("a", True, "ok"))
    report.add(CheckResult("b", False, "bad"))
    assert report.passed is False


# ---------------------------------------------------------------------------
# check_python_version
# ---------------------------------------------------------------------------


def test_check_python_version_passes_for_current():
    result = check_python_version()
    assert result.passed is True
    assert "✓" in result.message


def test_check_python_version_fails_for_old_version():
    with patch.object(sys, "version_info", (3, 7, 0, "final", 0)):
        result = check_python_version()
    assert result.passed is False
    assert result.hint is not None
    assert "3.9" in result.hint


# ---------------------------------------------------------------------------
# check_required_tools
# ---------------------------------------------------------------------------


def test_check_required_tools_finds_python():
    """'python' must be available since we're running Python right now."""
    results = check_required_tools()
    python_result = next((r for r in results if "python" in r.name.lower()), None)
    assert python_result is not None
    assert python_result.passed is True


def test_check_required_tools_fails_for_missing_tool():
    with patch("shutil.which", return_value=None):
        results = check_required_tools()
    for result in results:
        assert result.passed is False
        assert result.hint is not None


# ---------------------------------------------------------------------------
# check_optional_tools
# ---------------------------------------------------------------------------


def test_check_optional_tools_always_passes():
    """Optional tools never cause a failure, regardless of presence."""
    with patch("shutil.which", return_value=None):
        results = check_optional_tools()
    for result in results:
        assert result.passed is True


def test_check_optional_tools_provides_hint_when_missing():
    with patch("shutil.which", return_value=None):
        results = check_optional_tools()
    for result in results:
        assert result.hint is not None


# ---------------------------------------------------------------------------
# check_dotnet
# ---------------------------------------------------------------------------


def test_check_dotnet_passes_when_not_found():
    """dotnet is optional — absence should still be a passing check."""
    with patch("shutil.which", return_value=None):
        result = check_dotnet()
    assert result.passed is True
    assert "optional" in result.message


def test_check_dotnet_passes_and_reports_version(tmp_path):
    fake_dotnet = str(tmp_path / "dotnet")
    with (
        patch("shutil.which", return_value=fake_dotnet),
        patch(
            "subprocess.run",
            return_value=type("R", (), {"stdout": "8.0.100\n", "returncode": 0})(),
        ),
    ):
        result = check_dotnet()
    assert result.passed is True
    assert "8.0.100" in result.message


# ---------------------------------------------------------------------------
# check_artifact_paths
# ---------------------------------------------------------------------------


def test_check_artifact_paths_creates_missing_dir(tmp_path):
    new_dir = str(tmp_path / "artifacts" / "sub")
    results = check_artifact_paths([new_dir])
    assert len(results) == 1
    assert results[0].passed is True


def test_check_artifact_paths_fails_for_non_writable(tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o444)

    if os.access(locked, os.W_OK):
        pytest.skip("Running as root — permission test not meaningful")

    results = check_artifact_paths([str(locked)])
    assert results[0].passed is False
    assert results[0].hint is not None


# ---------------------------------------------------------------------------
# check_profile
# ---------------------------------------------------------------------------


def test_check_profile_skipped_when_none():
    result = check_profile(None)
    assert result.passed is True
    assert "skipped" in result.message.lower()


def test_check_profile_fails_for_missing_file(tmp_path):
    result = check_profile(str(tmp_path / "no_such.json"))
    assert result.passed is False
    assert result.hint is not None


def test_check_profile_fails_for_empty_file(tmp_path):
    empty = tmp_path / "empty.json"
    empty.write_text("")
    result = check_profile(str(empty))
    assert result.passed is False
    assert "empty" in result.message.lower()


def test_check_profile_fails_for_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json")
    result = check_profile(str(bad))
    assert result.passed is False
    assert "invalid" in result.message.lower()


def test_check_profile_passes_for_valid_json(tmp_path):
    good = tmp_path / "profile.json"
    good.write_text(json.dumps({"app": "MyApp.exe", "timeout": 30}))
    result = check_profile(str(good))
    assert result.passed is True
    assert "✓" in result.message


# ---------------------------------------------------------------------------
# run_doctor integration
# ---------------------------------------------------------------------------


def test_run_doctor_returns_report(tmp_path):
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({"app": "test.exe"}))

    report = run_doctor(
        artifact_paths=[str(tmp_path / "arts")],
        profile_path=str(profile),
    )

    assert isinstance(report, DoctorReport)
    assert len(report.checks) > 0


def test_run_doctor_with_no_args_does_not_raise():
    """run_doctor() with defaults must not raise any exception."""
    report = run_doctor()
    assert isinstance(report, DoctorReport)
