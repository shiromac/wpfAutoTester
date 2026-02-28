"""Tests for wpfautotester CLI (doctor command)."""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from wpfautotester.cli import main
from wpfautotester.errors import EXIT_DOCTOR_FAILURE, EXIT_OK


@pytest.fixture()
def runner():
    return CliRunner()


def test_version(runner):
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "wpfautotester" in result.output.lower()


def test_doctor_help(runner):
    result = runner.invoke(main, ["doctor", "--help"])
    assert result.exit_code == 0
    assert "doctor" in result.output.lower()


def test_doctor_passes_with_valid_profile(runner, tmp_path):
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({"app": "test.exe"}))
    arts = str(tmp_path / "arts")

    result = runner.invoke(
        main,
        ["doctor", "--artifact-path", arts, "--profile", str(profile)],
    )
    assert result.exit_code == EXIT_OK
    assert "All checks passed" in result.output


def test_doctor_fails_with_invalid_profile(runner, tmp_path):
    bad_profile = tmp_path / "bad.json"
    bad_profile.write_text("{broken")

    result = runner.invoke(main, ["doctor", "--profile", str(bad_profile)])
    assert result.exit_code == EXIT_DOCTOR_FAILURE


def test_doctor_fails_with_missing_profile(runner, tmp_path):
    result = runner.invoke(
        main, ["doctor", "--profile", str(tmp_path / "nonexistent.json")]
    )
    assert result.exit_code == EXIT_DOCTOR_FAILURE


def test_doctor_output_contains_check_names(runner, tmp_path):
    result = runner.invoke(main, ["doctor", "--artifact-path", str(tmp_path)])
    assert "Python version" in result.output
    assert ".NET runtime" in result.output


def test_doctor_shows_hint_on_failure(runner, tmp_path):
    bad_profile = tmp_path / "bad.json"
    bad_profile.write_text("{bad")
    result = runner.invoke(main, ["doctor", "--profile", str(bad_profile)])
    # The hint arrow should appear in output
    assert "↳" in result.output


def test_doctor_no_args_exits_zero_or_ten(runner):
    """doctor with no args should exit with 0 or 10 — not crash."""
    result = runner.invoke(main, ["doctor"])
    assert result.exit_code in (EXIT_OK, EXIT_DOCTOR_FAILURE)
    assert result.exception is None
