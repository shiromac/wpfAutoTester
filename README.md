# wpfAutoTester

AI-driven WPF UI testing agent integrated with Claude Code. Claude reads
screenshots, understands UI state, and autonomously explores and tests your
application — then fixes issues it finds.

[![CI](https://github.com/shiromac/wpfAutoTester/actions/workflows/ci.yml/badge.svg)](https://github.com/shiromac/wpfAutoTester/actions/workflows/ci.yml)

---

## Installation

```bash
pip install wpfautotester
```

For development / contribution:

```bash
git clone https://github.com/shiromac/wpfAutoTester.git
cd wpfAutoTester
pip install -e ".[dev]"
```

---

## Requirements

| Requirement | Notes |
|---|---|
| Python >= 3.9 | Required |
| Windows 10/11 | Required for live UI automation |
| .NET runtime | Optional — needed only if your WPF app requires it |
| pywinauto | Installed automatically as a dependency |

---

## Usage

### `doctor` — validate your environment

Before running tests, check that your environment is configured correctly:

```bash
wpfautotester doctor
```

Sample output:

```
wpfautotester doctor — environment check
─────────────────────────────────────────────
  [✓] Python version: Python 3.11 ✓ (>= 3.9 required)
  [✓] Tool: python: 'python' found at C:\Python311\python.exe ✓
  [✓] Optional tool: dotnet: 'dotnet' found at C:\Program Files\dotnet\dotnet.exe ✓
  [✓] Optional tool: pwsh: 'pwsh' not found (optional)
       ↳ Install 'pwsh' if you need .NET / PowerShell integration.
  [✓] .NET runtime: .NET 8.0.100 found ✓
  [✓] Artifact path: .\artifacts: '.\artifacts' is writable ✓
  [✓] Profile: No profile specified (skipped)

✅  All checks passed — environment is ready.
```

**Options:**

| Option | Description |
|---|---|
| `--artifact-path PATH` | Verify a custom artifact directory (repeatable) |
| `--profile FILE` | Validate a JSON test-profile file |

```bash
# Custom artifact directory + profile validation
wpfautotester doctor --artifact-path C:\TestArtifacts --profile profile.json
```

**Exit codes:**

| Code | Meaning |
|---|---|
| 0 | All required checks passed |
| 10 | One or more required checks failed |

---

## Error codes

wpfautotester uses structured exit codes for all UI-targeting failures:

| Code | Constant | Meaning |
|---|---|---|
| 0 | `EXIT_OK` | Success |
| 1 | `EXIT_GENERAL_ERROR` | Unclassified error |
| 2 | `EXIT_ELEMENT_NOT_FOUND` | No element matched the selector |
| 3 | `EXIT_ELEMENT_NOT_INTERACTIVE` | Element is disabled or hidden |
| 4 | `EXIT_ELEMENT_OFFSCREEN` | Element is off-screen or obscured |
| 5 | `EXIT_AMBIGUOUS_TARGET` | Multiple elements matched the selector |
| 6 | `EXIT_TIMEOUT` | Timed out waiting for the element |
| 10 | `EXIT_DOCTOR_FAILURE` | Environment check failed |

---

## Troubleshooting

### `ElementNotFoundError` — element not found

- Open **Inspect.exe** (ships with the Windows SDK) or **UISpy** and verify
  the automation ID / control type of your target element.
- Ensure the target window is in the foreground and fully loaded before
  running the automation.
- Increase the `timeout` parameter if the application is slow to render.

### `AmbiguousTargetError` — multiple elements matched

- Narrow your selector with a unique `auto_id` or add an index suffix.
- Use the `control_type` filter to restrict matches to a specific type.

### `ElementNotInteractiveError` — element is disabled or hidden

- Check that the application is in the correct state before interacting
  (e.g. a form is fully loaded, a button is enabled).

### `TargetingTimeoutError` — operation timed out

- Increase the `timeout` value passed to `find_element` / `click_element`.
- Confirm the application is running and its window is visible.

### doctor reports failures

Run `wpfautotester doctor` and follow the `↳` hints printed for each
failing check.

---

## Development

```bash
# Run tests
pytest tests/ -v

# Run linter
flake8 wpfautotester/ tests/

# Run both
flake8 wpfautotester/ tests/ && pytest tests/ -v
```

CI runs automatically on every push and pull-request via
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).
