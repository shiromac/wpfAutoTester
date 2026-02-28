# WPF UI Debug Automation Agent

Claude Code integrated WPF UI automation agent. Supports scenario testing, random exploratory testing, ticket generation, and AI-free replay.

## Quick Start

```powershell
# One-command setup
powershell -ExecutionPolicy Bypass -File setup.ps1
```

Or manually:

```bash
pip install -e .[dev]
wpf-agent init
```

## Register MCP Server

```bash
claude mcp add wpf-agent -- python -m wpf_agent mcp-serve
```

## Usage

### Target an app by profile

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

### Replay (AI-free)

```bash
wpf-agent replay --file artifacts/sessions/<id>/actions.json --profile MyApp
```

### View Tickets

```bash
wpf-agent tickets open --last
```

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
```

## Building Executable

```bash
pip install pyinstaller
pyinstaller wpf_agent.spec
```
