"""Tests for snapshot diff."""

from wpf_agent.uia.snapshot import diff_snapshots


def test_diff_empty():
    d = diff_snapshots([], [])
    assert d["added"] == []
    assert d["removed"] == []
    assert d["changed"] == []


def test_diff_added():
    before = []
    after = [{"automation_id": "btn1", "name": "OK", "control_type": "Button"}]
    d = diff_snapshots(before, after)
    assert len(d["added"]) == 1
    assert d["added"][0]["name"] == "OK"


def test_diff_removed():
    before = [{"automation_id": "btn1", "name": "OK", "control_type": "Button"}]
    after = []
    d = diff_snapshots(before, after)
    assert len(d["removed"]) == 1


def test_diff_changed():
    before = [{"automation_id": "btn1", "name": "OK", "control_type": "Button", "enabled": True}]
    after = [{"automation_id": "btn1", "name": "OK", "control_type": "Button", "enabled": False}]
    d = diff_snapshots(before, after)
    assert len(d["changed"]) == 1
    assert d["changed"][0]["changes"]["enabled"]["before"] is True
    assert d["changed"][0]["changes"]["enabled"]["after"] is False
