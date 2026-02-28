"""Configuration and profile management."""

from __future__ import annotations

import json
import pathlib
from typing import Any, Optional

from pydantic import BaseModel, Field

from wpf_agent.constants import DEFAULT_TIMEOUT_MS, PROFILES_FILE


class SafetyConfig(BaseModel):
    allow_destructive: bool = False
    destructive_patterns: list[str] = Field(default_factory=lambda: [
        "delete", "remove", "drop", "exit", "quit", "close", "shutdown",
    ])
    require_double_confirm: bool = True


class TimeoutConfig(BaseModel):
    startup_ms: int = 15000
    default_ms: int = DEFAULT_TIMEOUT_MS
    screenshot_ms: int = 5000


class ProfileMatch(BaseModel):
    pid: Optional[int] = None
    process: Optional[str] = None
    title_re: Optional[str] = None
    exe: Optional[str] = None


class ProfileLaunch(BaseModel):
    exe: str
    args: list[str] = Field(default_factory=list)
    cwd: Optional[str] = None


class Profile(BaseModel):
    name: str
    match: Optional[ProfileMatch] = None
    launch: Optional[ProfileLaunch] = None
    timeouts: TimeoutConfig = Field(default_factory=TimeoutConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)


class ProfileStore:
    """Manages profiles.json read/write."""

    def __init__(self, path: str | pathlib.Path | None = None):
        self.path = pathlib.Path(path or PROFILES_FILE)

    def _load_raw(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save_raw(self, data: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def list(self) -> list[Profile]:
        return [Profile(**d) for d in self._load_raw()]

    def get(self, name: str) -> Profile | None:
        for d in self._load_raw():
            if d.get("name") == name:
                return Profile(**d)
        return None

    def add(self, profile: Profile) -> None:
        data = self._load_raw()
        if any(d.get("name") == profile.name for d in data):
            raise ValueError(f"Profile '{profile.name}' already exists")
        data.append(profile.model_dump(exclude_none=True))
        self._save_raw(data)

    def remove(self, name: str) -> bool:
        data = self._load_raw()
        new = [d for d in data if d.get("name") != name]
        if len(new) == len(data):
            return False
        self._save_raw(new)
        return True

    def update(self, profile: Profile) -> None:
        data = self._load_raw()
        for i, d in enumerate(data):
            if d.get("name") == profile.name:
                data[i] = profile.model_dump(exclude_none=True)
                self._save_raw(data)
                return
        raise ValueError(f"Profile '{profile.name}' not found")

    def ensure_default(self) -> None:
        if not self.path.exists():
            default = Profile(
                name="example",
                match=ProfileMatch(title_re=".*"),
                timeouts=TimeoutConfig(),
                safety=SafetyConfig(),
            )
            self._save_raw([default.model_dump(exclude_none=True)])
