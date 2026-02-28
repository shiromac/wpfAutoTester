"""Tests for runner logging."""

import json

from wpf_agent.core.session import Session
from wpf_agent.runner.logging import ActionRecorder, StepLogger


def test_step_logger(tmp_path):
    session = Session()
    session.base_dir = tmp_path / "test"
    session.screens_dir = session.base_dir / "screens"
    session.uia_dir = session.base_dir / "uia"
    session.start()

    logger = StepLogger(session)
    logger.open()
    logger.log_step(1, "click", {"selector": "btn"}, result={"ok": True})
    logger.log_step(2, "type_text", {"text": "hi"}, error="not found")
    logger.close()

    entries = logger.read_last_n(10)
    assert len(entries) == 2
    assert entries[0]["action"] == "click"
    assert entries[1]["error"] == "not found"


def test_action_recorder(tmp_path):
    session = Session()
    session.base_dir = tmp_path / "test"
    session.screens_dir = session.base_dir / "screens"
    session.uia_dir = session.base_dir / "uia"
    session.start()

    recorder = ActionRecorder(session)
    recorder.record("click", {"selector": "btn1"})
    recorder.record("type_text", {"text": "hello"})
    path = recorder.save()

    assert path.exists()
    data = json.loads(path.read_text())
    assert len(data) == 2
    assert data[0]["action"] == "click"
    assert data[1]["action"] == "type_text"
