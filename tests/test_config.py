"""Tests for config and profile management."""

import json
import pathlib
import tempfile

from wpf_agent.config import Profile, ProfileMatch, ProfileStore, SafetyConfig


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


def test_safety_config_defaults():
    s = SafetyConfig()
    assert s.allow_destructive is False
    assert "delete" in s.destructive_patterns
    assert s.require_double_confirm is True
