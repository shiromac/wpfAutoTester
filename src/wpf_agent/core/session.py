"""Session lifecycle management."""

from __future__ import annotations

import pathlib
import time
import uuid
from dataclasses import dataclass, field

from wpf_agent.constants import SESSION_DIR


@dataclass
class Session:
    """One test/automation run = one session."""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: float = field(default_factory=time.time)
    base_dir: pathlib.Path = field(init=False)
    screens_dir: pathlib.Path = field(init=False)
    uia_dir: pathlib.Path = field(init=False)
    step_count: int = 0

    def __post_init__(self):
        self.base_dir = pathlib.Path(SESSION_DIR) / self.session_id
        self.screens_dir = self.base_dir / "screens"
        self.uia_dir = self.base_dir / "uia"

    def start(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.screens_dir.mkdir(exist_ok=True)
        self.uia_dir.mkdir(exist_ok=True)

    def next_step(self) -> int:
        self.step_count += 1
        return self.step_count

    def screenshot_path(self, step: int | None = None) -> pathlib.Path:
        s = step if step is not None else self.step_count
        return self.screens_dir / f"step-{s:04d}.png"

    def uia_snapshot_path(self, step: int | None = None) -> pathlib.Path:
        s = step if step is not None else self.step_count
        return self.uia_dir / f"step-{s:04d}.json"

    def log_path(self) -> pathlib.Path:
        return self.base_dir / "runner.log"

    def actions_path(self) -> pathlib.Path:
        return self.base_dir / "actions.json"

    @property
    def elapsed_s(self) -> float:
        return time.time() - self.started_at
