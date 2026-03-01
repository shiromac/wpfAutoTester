"""Global constants."""

import pathlib


def _find_project_root() -> pathlib.Path:
    """Find the project root (directory containing profiles.json or .git).

    Search order:
      1. Walk up from cwd
      2. Walk up from the package source directory (editable install)
    Fallback: cwd
    """
    markers = ("profiles.json", ".git")

    def _search(start: pathlib.Path) -> pathlib.Path | None:
        for d in [start, *start.parents]:
            if any((d / m).exists() for m in markers):
                return d
        return None

    # Try cwd first (normal case)
    found = _search(pathlib.Path.cwd())
    if found:
        return found

    # Try package source location (covers editable installs from odd cwd)
    pkg_dir = pathlib.Path(__file__).resolve().parent  # src/wpf_agent/
    found = _search(pkg_dir)
    if found:
        return found

    return pathlib.Path.cwd()


PROJECT_ROOT = _find_project_root()

DEFAULT_TIMEOUT_MS = 10000
DEFAULT_DEPTH = 4
DEFAULT_LOG_TAIL = 20
SESSION_DIR = str(PROJECT_ROOT / "artifacts" / "sessions")
TICKET_DIR = str(PROJECT_ROOT / "artifacts" / "tickets")
PROFILES_FILE = str(PROJECT_ROOT / "profiles.json")
MAX_CONTROLS = 500
SCREENSHOT_FORMAT = "png"

# UI guard constants
GUARD_CHECK_DELAY_MS = 50
GUARD_MOVEMENT_THRESHOLD_PX = 2.0
GUARD_PAUSE_DIR = pathlib.Path.home() / ".wpf-agent"
LAUNCHED_PIDS_FILE = pathlib.Path.home() / ".wpf-agent" / "launched_pids.json"
