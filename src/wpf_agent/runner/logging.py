"""Structured per-step logging for sessions."""

from __future__ import annotations

import json
import pathlib
import sys
import time
from typing import Any

from wpf_agent.core.session import Session


class StepLogger:
    """Append-only structured log for a session."""

    def __init__(self, session: Session):
        self.session = session
        self._log_path = session.log_path()
        self._fh = None

    def open(self) -> None:
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self._log_path, "a", encoding="utf-8")

    def close(self) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None

    def log_step(
        self,
        step: int,
        action: str,
        args: dict[str, Any],
        result: dict[str, Any] | None = None,
        error: str | None = None,
        screenshot_path: str | None = None,
        uia_snapshot_path: str | None = None,
    ) -> None:
        entry = {
            "step": step,
            "timestamp": time.time(),
            "action": action,
            "args": args,
            "result": result,
            "error": error,
            "screenshot": screenshot_path,
            "uia_snapshot": uia_snapshot_path,
        }
        line = json.dumps(entry, ensure_ascii=False, default=str)
        if self._fh:
            self._fh.write(line + "\n")
            self._fh.flush()
        # In MCP mode, log to stderr
        print(line, file=sys.stderr)

    def read_last_n(self, n: int = 20) -> list[dict[str, Any]]:
        if not self._log_path.exists():
            return []
        lines = self._log_path.read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(l) for l in lines[-n:]]


class ActionRecorder:
    """Record actions for replay."""

    def __init__(self, session: Session):
        self.session = session
        self._actions: list[dict[str, Any]] = []

    def record(self, action: str, args: dict[str, Any]) -> None:
        self._actions.append({
            "step": len(self._actions) + 1,
            "action": action,
            "args": args,
            "timestamp": time.time(),
        })

    def save(self) -> pathlib.Path:
        path = self.session.actions_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._actions, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return path

    @property
    def actions(self) -> list[dict[str, Any]]:
        return list(self._actions)
