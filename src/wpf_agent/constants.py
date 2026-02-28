"""Global constants."""

import pathlib

DEFAULT_TIMEOUT_MS = 10000
DEFAULT_DEPTH = 4
DEFAULT_LOG_TAIL = 20
SESSION_DIR = "artifacts/sessions"
TICKET_DIR = "artifacts/tickets"
PROFILES_FILE = "profiles.json"
MAX_CONTROLS = 500
SCREENSHOT_FORMAT = "png"

# UI guard constants
GUARD_CHECK_DELAY_MS = 200
GUARD_MOVEMENT_THRESHOLD_PX = 5.0
GUARD_PAUSE_DIR = pathlib.Path.home() / ".wpf-agent"
