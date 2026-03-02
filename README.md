# WPF UI Debug Automation Agent

> **Windows 10/11 required** | Python 3.10+

AI-driven WPF UI testing agent integrated with Claude Code. Claude reads screenshots, understands UI state, and autonomously explores and tests your application — then fixes issues it finds.

## Key Features

- **AI-Guided Exploration** — Claude Code sees your app's screenshots, decides what to click/type, and discovers bugs autonomously (`/wpf-explore`)
- **Auto-Fix Loop** — Build, verify, find issues, fix code, rebuild — all driven by AI (`/wpf-verify`)
- **Scenario Testing** — YAML-defined test scenarios with assertions and auto-generated tickets
- **Random Testing** — Seed-reproducible random exploration with crash/anomaly detection
- **AI-Free Replay** — Re-run recorded action sequences without API calls
- **Ticket Generation** — Auto-generated bug tickets with screenshots, UIA snapshots, and repro steps
- **UI Safety Guard** — Mouse movement detection pauses automation when user intervenes

## Installation

```bash
pip install git+https://github.com/shiromac/wpfAutoTester.git
```

Or for development:

```bash
git clone https://github.com/shiromac/wpfAutoTester.git
cd wpf-agent
pip install -e .[dev]
```

## Quick Start

```bash
# Initialize config
wpf-agent init

# Install Claude Code skills (/wpf-explore, /wpf-verify, etc.)
wpf-agent install-skills

# Register MCP server for Claude Code
claude mcp add wpf-agent -- python -m wpf_agent mcp-serve
```

## Usage

### AI-Guided Exploration (Main Feature)

Claude Code directly controls and tests your app — no ANTHROPIC_API_KEY needed for the UI commands:

```
/wpf-explore test all buttons and inputs in the settings page
```

The exploration loop:
1. Takes a screenshot and reads it
2. Lists UI controls (automation IDs, names, types)
3. Decides the next action based on visual understanding
4. Executes the action (`click`, `type`, `toggle`)
5. Verifies the result with another screenshot
6. Reports discovered issues

### Build & Auto-Verify

Automatically verify your app after building:

```bash
wpf-agent verify --exe bin/Debug/net9.0-windows/MyApp.exe
```

With a spec file for detailed checks:

```bash
wpf-agent verify --exe bin/Debug/net9.0-windows/MyApp.exe --spec verify-spec.yaml
```

When verification fails, Claude Code can read the report, fix the code, rebuild, and re-verify.

### Target an App by Profile

```bash
# Edit profiles.json with your app details, then:
wpf-agent run --profile MyApp-Dev
```

### Attach / Launch

```bash
wpf-agent attach --pid 12345
wpf-agent launch --exe "C:/path/MyApp.exe" -- --dev-mode
```

### Scenario Testing

```bash
wpf-agent scenario run --file scenarios/demo_a_settings.yaml --profile MyApp
```

### Random Testing

```bash
wpf-agent random run --profile MyApp --max-steps 200 --seed 42
```

### Usability Testing (Persona-Based)

Run a think-aloud usability test with a simulated persona:

```
/wpf-usability-test --pid 12345 --goal "Set the counter to 5"
/wpf-usability-test --pid 12345 --goal "Save settings" --persona suzuki
/wpf-usability-test --exe path/to/App.exe --goal "Save settings" --persona "College student, tech-savvy, impatient"
```

`--persona` accepts a preset name (e.g., `tanaka`, `suzuki`, `sato`) or inline text. Defaults to `tanaka` if omitted.

Claude assumes the persona and narrates thoughts while trying to achieve the goal. Generates a usability report with issues, severity ratings, and improvement suggestions.

### Replay (AI-free)

```bash
wpf-agent replay --file artifacts/sessions/<id>/actions.json --profile MyApp
```

### Tickets

```bash
# Create a ticket from CLI
wpf-agent tickets create --title "Button crash" --summary "App crashes on click" \
  --actual "Crash" --expected "No crash" --repro "Click MainButton" --pid 1234

# View latest ticket
wpf-agent tickets open --last

# List untriaged tickets
wpf-agent tickets list-pending

# Triage: classify as fix or wontfix
wpf-agent tickets triage --ticket <path> --decision fix --reason "Crash detected"
wpf-agent tickets triage --ticket <path> --decision wontfix --reason "Expected behavior"
```

Or use slash commands:

```
/wpf-ticket-create App crashed after clicking the save button
/wpf-ticket-triage auto
```

## `wpf-agent ui` — Direct UI Commands

CLI commands for Claude Code to operate UI directly via Bash. No ANTHROPIC_API_KEY required.

### Action Commands (guarded by mouse movement detection)

```bash
wpf-agent ui focus --pid <pid>                          # Focus window
wpf-agent ui click --pid <pid> --aid <id>               # Click element
wpf-agent ui type --pid <pid> --aid <id> --text "..."   # Type text
wpf-agent ui toggle --pid <pid> --aid <id>              # Toggle checkbox
wpf-agent ui close --pid <pid>                          # Graceful close (launch-started only)
```

### Read-Only Commands (always available, even when paused)

```bash
wpf-agent ui windows [--brief]                          # List top-level windows (PID, title)
wpf-agent ui alive --process MyApp [--brief]            # Find process + get PID
wpf-agent ui alive --pid <pid>                          # Check if process is running
wpf-agent ui screenshot --pid <pid> [--save <path>]     # Take screenshot (auto-composites popups)
wpf-agent ui controls --pid <pid> [--depth N]            # List all controls (JSON)
wpf-agent ui controls --pid <pid> --has-aid --brief      # Only controls with automation_id (table)
wpf-agent ui controls --pid <pid> --type-filter Button,Edit,ComboBox --brief
wpf-agent ui read --pid <pid> --aid <id>                 # Read text
wpf-agent ui state --pid <pid> --aid <id>                # Get state
```

`ui controls` filter options:

| Option | Description |
|--------|-------------|
| `--type-filter` | Filter by control_type (comma-separated) |
| `--name-filter` | Filter by name (substring, case-insensitive) |
| `--has-name` | Only controls with non-empty name |
| `--has-aid` | Only controls with non-empty automation_id |
| `--brief` | Compact table output instead of JSON |

### Guard Management

```bash
wpf-agent ui status                                     # Check guard state
wpf-agent ui resume                                     # Resume after pause
wpf-agent ui --no-guard click --pid ...                 # Skip guard
```

All commands accept `--pid <int>` or `--title-re <regex>` for targeting.
Selectors: `--aid`, `--name`, `--control-type` (`--aid` recommended).

## UI Guard (Mouse Movement Detection)

Action commands (`focus`, `click`, `type`, `toggle`) sample mouse position for 50ms before execution. If user mouse movement (>2px) is detected, the operation is aborted and a persistent pause is set.

- Interrupted: exit code 2 + JSON output with reason
- Read-only commands remain available during pause
- Resume with `wpf-agent ui resume`

## MCP Tools (13)

| Tool | Description |
|------|-------------|
| `list_windows` | List visible top-level windows |
| `resolve_target` | Resolve app by PID/process/exe/title regex |
| `focus_window` | Bring window to front |
| `wait_window` | Wait for window appearance |
| `list_controls` | Enumerate UIA controls |
| `click` | Click a UI element |
| `type_text` | Type text into element |
| `select_combo` | Select combo box item |
| `toggle` | Toggle checkbox/button |
| `read_text` | Read element text |
| `get_state` | Get element state |
| `screenshot` | Capture screenshot |
| `wait_for` | Wait for UI condition |

## VS Code Copilot Support

The skills in `.claude/skills/` are compatible with the [Agent Skills](https://agentskills.io) open standard.
VS Code Copilot (Insiders / agent mode) auto-detects them — no extra configuration needed.

To also install skills for GitHub Copilot Coding Agent (repository-level):

```bash
wpf-agent install-skills --github
```

## Claude Code Slash Commands

| Command | Description |
|---------|-------------|
| `/wpf-setup` | Setup and register MCP server |
| `/wpf-inspect` | Inspect UI (windows + controls + screenshot) |
| `/wpf-explore` | AI-guided exploration testing |
| `/wpf-usability-test` | Persona-based usability testing (think-aloud + goal-oriented) |
| `/wpf-verify` | Build & auto-verify (launch, smoke test, UI check, report) |
| `/wpf-click` | Click element + verify |
| `/wpf-type` | Type text + verify |
| `/wpf-scenario` | Run scenario test / create YAML |
| `/wpf-random` | Random exploration testing |
| `/wpf-replay` | AI-free replay |
| `/wpf-ticket` | View/analyze tickets |
| `/wpf-ticket-create` | Create issue ticket with evidence |
| `/wpf-ticket-triage` | Triage tickets (classify as fix/wontfix) |

## Profile Configuration

Edit `profiles.json`:

```json
[
  {
    "name": "MyApp-Dev",
    "match": { "process": "MyApp.exe" },
    "launch": { "exe": "C:/path/MyApp.exe", "args": ["--dev"] },
    "timeouts": { "startup_ms": 15000, "default_ms": 10000 },
    "safety": { "allow_destructive": false }
  }
]
```

## Persona Presets

`personas.json` defines reusable persona presets for usability testing:

```json
[
  {
    "name": "tanaka",
    "description": "Tanaka Misaki (35), office worker, moderate IT literacy, cautious, reads instructions carefully"
  },
  {
    "name": "suzuki",
    "description": "Suzuki Kenichi (62), retiree, low IT literacy, prefers large text, operates slowly"
  },
  {
    "name": "sato",
    "description": "Sato Shota (22), junior engineer, high IT literacy, impatient, clicks without reading"
  }
]
```

Manage presets via CLI:

```bash
wpf-agent personas list
wpf-agent personas add --name yamada --description "Yamada (45), manager, moderate IT skills"
wpf-agent personas edit yamada --description "Yamada (45), senior manager, high IT skills"
wpf-agent personas remove yamada
```

## Project Structure

```
src/wpf_agent/
  core/       # target registry, session, safety, errors
  uia/        # UIA engine, selector, snapshot, screenshot, waits
  mcp/        # FastMCP server (13 tools), Pydantic types
  runner/     # agent loop, replay, logging
  testing/    # scenario, random tester, assertions, oracles, minimizer
  tickets/    # generator, templates, evidence
scenarios/    # YAML scenario definitions
artifacts/    # sessions and tickets (generated)
tests/        # unit tests
testApp/      # Sample WPF app (.NET 9) for testing
profiles.json # target app definitions
personas.json # persona presets for usability testing
```

## Building Executable

```bash
pip install pyinstaller
pyinstaller wpf_agent.spec
```

## Claude Code Permission Settings

To auto-approve `wpf-agent` commands, add the following to `.claude/settings.local.json` (project-local, gitignored):

```jsonc
{
  "permissions": {
    "allow": [
      "Bash(wpf-agent *)",   // Full command string including pipes
      "Bash(wpf-agent:*)",   // Command name prefix (simple commands)
      "Bash(python:*)"
    ]
  }
}
```

| Pattern | Matches | Use for |
|---------|---------|---------|
| `Bash(wpf-agent:*)` | Command **name** prefix | Simple: `wpf-agent tickets create ...` |
| `Bash(wpf-agent *)` | Full command **string** | Piped: `wpf-agent ui controls ... \| head` |

Both patterns are recommended. The `*` glob does not match newlines, so always write Bash commands on a single line.

Use `/permissions` in Claude Code to inspect active rules.

## License

MIT License. See [LICENSE](LICENSE).
