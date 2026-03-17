"""Tests for config and profile management."""

import json
import pathlib
import tempfile

from wpf_agent.config import (
    Persona,
    PersonaStore,
    Profile,
    ProfileMatch,
    ProfileStore,
    SafetyConfig,
)


def test_profile_store_lifecycle(tmp_path):
    path = tmp_path / "profiles.json"
    store = ProfileStore(path)

    # Empty initially
    assert store.list() == []

    # Add
    p = Profile(name="test", match=ProfileMatch(process="test.exe"))
    store.add(p)
    assert len(store.list()) == 1
    assert store.get("test").name == "test"

    # Duplicate raises
    try:
        store.add(p)
        assert False, "Should have raised"
    except ValueError:
        pass

    # Update
    p.match.process = "test2.exe"
    store.update(p)
    updated = store.get("test")
    assert updated.match.process == "test2.exe"

    # Remove
    assert store.remove("test") is True
    assert store.remove("nonexistent") is False
    assert len(store.list()) == 0


def test_ensure_default(tmp_path):
    path = tmp_path / "profiles.json"
    store = ProfileStore(path)
    store.ensure_default()
    assert path.exists()
    profiles = store.list()
    assert len(profiles) == 1
    assert profiles[0].name == "example"


def test_profile_store_legacy_fallback(tmp_path, monkeypatch):
    """When .wpf-agent/profiles.json doesn't exist but root profiles.json does, fall back."""
    legacy = tmp_path / "profiles.json"
    legacy.write_text(
        json.dumps([{"name": "legacy", "match": {"process": "x.exe"}}]),
        encoding="utf-8",
    )
    new_path = tmp_path / ".wpf-agent" / "profiles.json"
    monkeypatch.setattr("wpf_agent.config.PROFILES_FILE", str(new_path))
    monkeypatch.setattr("wpf_agent.config.PROJECT_ROOT", tmp_path)

    store = ProfileStore()  # no explicit path
    assert store.path == legacy
    profiles = store.list()
    assert len(profiles) == 1
    assert profiles[0].name == "legacy"


def test_persona_store_legacy_fallback(tmp_path, monkeypatch):
    """When .wpf-agent/personas.json doesn't exist but root personas.json does, fall back."""
    legacy = tmp_path / "personas.json"
    legacy.write_text(
        json.dumps([{"name": "test", "description": "test persona"}]),
        encoding="utf-8",
    )
    new_path = tmp_path / ".wpf-agent" / "personas.json"
    monkeypatch.setattr("wpf_agent.config.PERSONAS_FILE", str(new_path))
    monkeypatch.setattr("wpf_agent.config.PROJECT_ROOT", tmp_path)

    store = PersonaStore()
    assert store.path == legacy
    personas = store.list()
    assert len(personas) == 1
    assert personas[0].name == "test"


def test_profile_store_prefers_new_path(tmp_path, monkeypatch):
    """When both legacy and new paths exist, prefer the new .wpf-agent/ path."""
    legacy = tmp_path / "profiles.json"
    legacy.write_text(json.dumps([{"name": "old"}]), encoding="utf-8")
    new_dir = tmp_path / ".wpf-agent"
    new_dir.mkdir()
    new_path = new_dir / "profiles.json"
    new_path.write_text(
        json.dumps([{"name": "new", "match": {"process": "y.exe"}}]),
        encoding="utf-8",
    )
    monkeypatch.setattr("wpf_agent.config.PROFILES_FILE", str(new_path))
    monkeypatch.setattr("wpf_agent.config.PROJECT_ROOT", tmp_path)

    store = ProfileStore()
    assert store.path == new_path
    assert store.get("new") is not None


def test_safety_config_defaults():
    s = SafetyConfig()
    assert s.allow_destructive is False
    assert "delete" in s.destructive_patterns
    assert s.require_double_confirm is True
