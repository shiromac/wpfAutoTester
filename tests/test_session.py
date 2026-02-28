"""Tests for session management."""

from wpf_agent.core.session import Session


def test_session_creates_dirs(tmp_path):
    s = Session()
    # Override base_dir for testing
    s.base_dir = tmp_path / "test_session"
    s.screens_dir = s.base_dir / "screens"
    s.uia_dir = s.base_dir / "uia"
    s.start()
    assert s.base_dir.exists()
    assert s.screens_dir.exists()
    assert s.uia_dir.exists()


def test_session_step_counter():
    s = Session()
    assert s.step_count == 0
    assert s.next_step() == 1
    assert s.next_step() == 2
    assert s.step_count == 2


def test_session_paths():
    s = Session()
    s.step_count = 5
    assert "step-0005" in str(s.screenshot_path(5))
    assert "step-0005" in str(s.uia_snapshot_path(5))
    assert "runner.log" in str(s.log_path())
    assert "actions.json" in str(s.actions_path())
