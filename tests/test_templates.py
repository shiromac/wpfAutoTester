"""Tests for ticket templates."""

from wpf_agent.tickets.templates import default_environment, render_ticket_md


def test_render_ticket_md():
    md = render_ticket_md(
        title="Test Bug",
        summary="Something went wrong",
        repro_steps=["Step 1", "Step 2"],
        actual_result="Crashed",
        expected_result="Should not crash",
        environment={"OS": "Windows 11"},
        evidence_files=["screens/step-0001.png"],
        root_cause_hypothesis="Null reference",
    )
    assert "# Test Bug" in md
    assert "1. Step 1" in md
    assert "2. Step 2" in md
    assert "Crashed" in md
    assert "Should not crash" in md
    assert "Null reference" in md
    assert "screens/step-0001.png" in md


def test_default_environment():
    env = default_environment()
    assert "OS" in env
    assert "Python" in env
