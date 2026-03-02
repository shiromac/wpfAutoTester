"""Target application registry and resolution."""

from __future__ import annotations

import json as _json
import pathlib
import re
import subprocess
import threading
import time
from typing import Any, Optional

import psutil

from wpf_agent.config import Profile, ProfileMatch
from wpf_agent.constants import LAUNCHED_PIDS_FILE
from wpf_agent.core.errors import TargetNotFoundError


# ── Launched PID tracking ────────────────────────────────────────
# Records PIDs started by wpf-agent (launch, verify, etc.)
# so that `wpf-agent ui close` can verify it only closes processes
# that *we* started.

def record_launched_pid(pid: int, exe: str) -> None:
    """Persist a launched PID to disk."""
    entries = _load_launched_entries()
    entries.append({"pid": pid, "exe": exe, "ts": time.time()})
    LAUNCHED_PIDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAUNCHED_PIDS_FILE.write_text(
        _json.dumps(entries, indent=2), encoding="utf-8"
    )


def _load_launched_entries() -> list[dict]:
    if LAUNCHED_PIDS_FILE.is_file():
        try:
            return _json.loads(LAUNCHED_PIDS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def is_launched_pid(pid: int) -> bool:
    """Return True if *pid* was started by wpf-agent launch."""
    return any(e["pid"] == pid for e in _load_launched_entries())


def remove_launched_pid(pid: int) -> None:
    """Remove a PID from the launched list (after close)."""
    entries = [e for e in _load_launched_entries() if e["pid"] != pid]
    LAUNCHED_PIDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAUNCHED_PIDS_FILE.write_text(
        _json.dumps(entries, indent=2), encoding="utf-8"
    )


class ResolvedTarget:
    """A resolved reference to a running application."""

    def __init__(self, pid: int, process_name: str, window_handle: int | None = None):
        self.pid = pid
        self.process_name = process_name
        self.window_handle = window_handle
        self._app = None

    @property
    def app(self):
        if self._app is None:
            from pywinauto import Application
            self._app = Application(backend="uia").connect(process=self.pid)
        return self._app

    @property
    def is_alive(self) -> bool:
        return psutil.pid_exists(self.pid)

    def __repr__(self) -> str:
        return f"ResolvedTarget(pid={self.pid}, name={self.process_name!r})"


class TargetRegistry:
    """Singleton registry for resolved targets."""

    _instance: Optional[TargetRegistry] = None
    _lock = threading.Lock()

    def __init__(self):
        self._targets: dict[str, ResolvedTarget] = {}
        self._counter = 0

    @classmethod
    def get_instance(cls) -> TargetRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._instance = None

    def _next_id(self) -> str:
        self._counter += 1
        return f"target-{self._counter}"

    def resolve(self, spec: dict[str, Any]) -> tuple[str, ResolvedTarget]:
        """Resolve a target_spec dict to a ResolvedTarget."""
        if "pid" in spec:
            return self._resolve_by_pid(spec["pid"])
        if "process" in spec:
            return self._resolve_by_process(spec["process"])
        if "exe" in spec:
            return self._resolve_by_exe(
                spec["exe"], spec.get("args", []), spec.get("cwd")
            )
        if "title_re" in spec:
            return self._resolve_by_title(spec["title_re"])
        raise TargetNotFoundError(f"Invalid target_spec: {spec}")

    def resolve_profile(self, profile: Profile) -> tuple[str, ResolvedTarget]:
        """Resolve from a Profile."""
        if profile.launch:
            spec: dict[str, Any] = {
                "exe": profile.launch.exe,
                "args": profile.launch.args,
            }
            if profile.launch.cwd:
                spec["cwd"] = profile.launch.cwd
            return self.resolve(spec)
        if profile.match:
            return self._resolve_match(profile.match)
        raise TargetNotFoundError(
            f"Profile '{profile.name}' has no match or launch config"
        )

    def get(self, target_id: str) -> ResolvedTarget:
        t = self._targets.get(target_id)
        if t is None:
            raise TargetNotFoundError(f"Unknown target_id: {target_id}")
        return t

    def _register(self, target: ResolvedTarget) -> str:
        tid = self._next_id()
        self._targets[tid] = target
        return tid

    def _resolve_match(self, match: ProfileMatch) -> tuple[str, ResolvedTarget]:
        if match.pid is not None:
            return self._resolve_by_pid(match.pid)
        if match.process:
            return self._resolve_by_process(match.process)
        if match.exe:
            return self._resolve_by_exe(match.exe, [], None)
        if match.title_re:
            return self._resolve_by_title(match.title_re)
        raise TargetNotFoundError("Empty match specification")

    def _resolve_by_pid(self, pid: int) -> tuple[str, ResolvedTarget]:
        if not psutil.pid_exists(pid):
            raise TargetNotFoundError(f"PID {pid} not found")
        proc = psutil.Process(pid)
        t = ResolvedTarget(pid=pid, process_name=proc.name())
        tid = self._register(t)
        return tid, t

    def _resolve_by_process(self, name: str) -> tuple[str, ResolvedTarget]:
        name_lower = name.lower()
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == name_lower:
                    t = ResolvedTarget(
                        pid=proc.info["pid"], process_name=proc.info["name"]
                    )
                    tid = self._register(t)
                    return tid, t
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        raise TargetNotFoundError(f"Process '{name}' not found")

    def _resolve_by_exe(
        self, exe: str, args: list[str], cwd: str | None
    ) -> tuple[str, ResolvedTarget]:
        exe_path = str(pathlib.Path(exe).resolve())
        cmd = [exe_path] + args
        proc = subprocess.Popen(cmd, cwd=cwd)
        time.sleep(2)
        if proc.poll() is not None:
            raise TargetNotFoundError(f"Process exited immediately: {exe}")
        basename = exe.replace("\\", "/").rsplit("/", 1)[-1]
        record_launched_pid(proc.pid, exe)
        t = ResolvedTarget(pid=proc.pid, process_name=basename)
        tid = self._register(t)
        return tid, t

    def _resolve_by_title(self, pattern: str) -> tuple[str, ResolvedTarget]:
        from pywinauto import Desktop

        desktop = Desktop(backend="uia")
        regex = re.compile(pattern, re.IGNORECASE)
        for w in desktop.windows():
            try:
                title = w.window_text()
                if regex.search(title):
                    pid = w.process_id()
                    proc = psutil.Process(pid)
                    t = ResolvedTarget(
                        pid=pid,
                        process_name=proc.name(),
                        window_handle=w.handle,
                    )
                    tid = self._register(t)
                    return tid, t
            except Exception:
                continue
        raise TargetNotFoundError(f"No window matching '{pattern}'")
