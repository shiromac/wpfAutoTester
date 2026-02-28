# Specification: Claude Code–Integrated WPF UI Debug Automation Loop

## 1. Objective

Build an agent loop that captures WPF (Windows desktop) application UI state (for example, screenshots), then **automatically performs UI operations on Windows** based on analysis results from Claude (Claude Code / Claude API).

Primary use cases:

- Debug support
- UI regression testing
- Procedure/task execution automation
- Exploratory testing (random testing)

In this project, AI does not directly operate the OS. Instead, AI generates **structured operation commands**, and a local executor (tool layer) **strictly validates and executes UI operations**.

Additional required capabilities:

- Execute **scenario tests** (tests with predefined steps + expected results)
- Execute **random tests** (exploratory actions to detect crashes, UI corruption, invariant violations, etc.)
- **Automatically generate issue tickets** (must include repro steps / actual result / expected result)
- **Assist root-cause investigation** (estimate plausible causes and attach evidence whenever possible)

---

## 2. Assumptions and Target Environment

- OS: Windows 10/11
- Target app: WPF (assume .NET 8; dependency on .NET version should be low as long as it is WPF)
- Runner: Local PC automation runner
- AI: Claude (via Claude Code or Claude API)
- Recommended UI automation method: UI Automation (UIA)
  - Primary option in Python: `pywinauto` (`backend="uia"`)
  - Fallback: OCR + coordinate click (only when needed)

### 2.1 Arbitrary App Targeting (Required)

The system must not be hardcoded to one app and must support targeting **arbitrary desktop applications**.

#### 2.1.1 Target Resolution Methods (Priority Order)

1. **Process ID (PID)** (most reliable)
2. **Process name** (e.g., `MyApp.exe`)
3. **Launch path (EXE path)** (including app launch)
4. **Window title regex** (e.g., `.*MyApp.*`)
5. (Optional) **Window class name** or **Automation Root element** targeting

#### 2.1.2 Operation Modes

- **Attach mode**: Connect to an already running app (identify by PID/process/title)
- **Launch mode**: Launch via EXE path + args and connect (including startup wait)

### 2.2 Setup Simplicity (Required)

- Must be usable by non-developers; provide **one-command initialization** (`init`) and **profile configuration** (`profiles`).
- Additional dependencies (such as OCR) are **optional**; minimum configuration must work with UIA only.

---

## 3. Scope

### 3.1 In Scope

1. **Agent loop (control runner)**
   - Repeats: capture screen → AI analysis → operation plan → UI operation → verification → next step
2. **UI operation tools (local executor)**
   - UIA-based element enumeration, click, input, state retrieval
3. **AI integration (Claude Code / MCP or API)**
   - AI can invoke tools (MCP server format recommended)
4. **Logging / replay / failure debugging support**
   - Save screenshots, AI I/O, tool calls, and execution results
5. **Test execution foundation**
   - Run/verify scenario tests and random tests; generate tickets

### 3.2 Out of Scope

- Free-form AI-driven direct OS operation (for safety reasons)
- Fully coordinate-driven automation based only on image analysis (for stability reasons)
- Automated operations against web or external services

---

## 4. Overall Architecture

### 4.1 Separation of Responsibilities (Important)

- **AI (Claude)**: Understand screen state, decide next actions, issue structured tool calls
- **Tool layer (local executor)**: Execute UI operations (UIA/OCR/coordinates) and return results
- **Runner**: Loop control, retries, timeout handling, logging, sanitization

### 4.2 Data Flow

1. Capture screen via `screenshot()` (optionally window-scoped)
2. Provide image + objective (task) to AI
3. AI returns **tool calls** (e.g., `list_controls`, `click`, `type_text`)
4. Runner validates calls and requests execution from tool layer
5. Tool layer returns execution results (success/failure, exception, state)
6. If needed, verify again via `screenshot()` / `read_text()`
7. Stop on terminal conditions (achieved/failed/max steps)

---

## 5. Functional Requirements (Common)

### 5.1 Failure (Defect) Oracles, Minimum Baseline (Required)

At minimum, treat the following as defects:

- App crashed or process terminated
- Exception dialog, fatal error screen, or unhandled exception log detected
- Expected UI element is missing in UIA (element should exist but cannot be found)
- UI freeze (no response for a defined period)
- Scenario-defined expected results are not met

Extended oracles (optional):

- Error text displayed on screen (OCR/text detection)
- Invariant violations (e.g., “Saved” indicator must appear after save)

### 5.2 Safety (Especially for Random Testing)

- **Destructive operations (delete/exit/external send, etc.) are disallowed by default**.
- If destructive operations are enabled, they must be explicitly configured in profile and require a double-confirmation step.

### 5.3 Window Management

- `list_windows()`
  - Returns currently visible top-level windows
- `focus_window(window_query | target_id)`
  - Brings target window to front via regex/partial match, etc.
- `wait_window(window_query | target_id, timeout_ms)`
  - Waits for window appearance
- `resolve_target(target_spec)`
  - Uniquely resolves target app (window/process) from `target_spec` and returns `target_id`

`target_spec` examples:

- `{ "pid": 12345 }`
- `{ "process": "MyApp.exe" }`
- `{ "exe": "C:/path/MyApp.exe", "args": ["--dev"] }`
- `{ "title_re": ".*MyApp.*" }`

### 5.4 UIA Element Enumeration

- `list_controls(window_query | target_id, depth?, filter?)`
  - Enumerates UIA tree and returns:
    - `automation_id`, `name`, `control_type`, `enabled`, `visible`, `bounding_rect` (if available), `value` (if available)
  - Must support filtering by `control_type`, etc.

### 5.5 UI Operations

- `click(window_query | target_id, selector)`
  - Selector matching priority:
    1. `automation_id`
    2. `name` + `control_type`
    3. Center click in `bounding_rect` (last resort)
- `type_text(window_query | target_id, selector, text)`
- `select_combo(window_query | target_id, selector, item_text)`
- `toggle(window_query | target_id, selector, state?)`

### 5.6 State Retrieval and Verification

- `read_text(window_query | target_id, selector)`
- `get_state(window_query | target_id, selector)`
  - Retrieves `enabled/visible/selected/value`, etc.
- `screenshot(window_query | target_id?, region?)`
  - Saves PNG and returns path/ID

### 5.7 OCR Fallback (Optional)

- `ocr_find(text, screenshot_id)`
- `click_xy(x, y)`

Note: OCR and coordinate clicks are optional fallback for custom-rendered UIs not discoverable via UIA.

---

## 6. Test Execution Modes (Additional Requirement, Required)

Using the same UI operation toolset, the system must provide two modes:

- **Scenario mode**
- **Random (exploratory) mode**

For both modes, when failures are detected, **issue tickets must be generated**, and repro steps should be minimized when possible.

### 6.1 Scenario Testing

#### 6.1.1 Definition Format

- Scenarios are file-defined and executable from CLI
- Format is YAML or JSON (implementation must standardize to one)

#### 6.1.2 Minimal Scenario Structure

- Metadata: `id`, `title`, `tags`, `owner`, `created_at`
- Target: `profile` or `target_spec`
- Step list:
  - `action` (`click`/`type_text`/`select_combo`/`toggle`/`wait_for`, etc.)
  - `selector` (`automation_id`/`name`/`control_type`)
  - `args`
  - `expected`
- Termination conditions:
  - Success condition (expectations met)
  - Failure condition (timeout, expectation mismatch, crash, etc.)

#### 6.1.3 Minimal Expected Assertions (Required)

- `exists`
- `text_equals`
- `enabled`
- `selected`

Recommended extensions:

- `text_contains`, `value_equals`, `regex`, `count_greater_equal`, `screenshot_diff` (simple)

#### 6.1.4 Failure Behavior (Required)

- Generate issue ticket immediately when expected conditions are unmet
- Collect the following around failure point:
  - Screenshot
  - UIA snapshot
  - Last N operation logs (N configurable, default 20)

### 6.2 Random (Exploratory) Testing

#### 6.2.1 Input (Exploration Profile)

- `target` (`profile`/`target_spec`)
- `seed` (if omitted, generate and always record)
- `max_steps`
- `action_space` (weights/preconditions/destructive flag)
- `invariants` (optional but recommended)
- `safety` (destructive operation policy and double confirmation)

#### 6.2.2 Exploration Strategy (Required Minimum)

- Uniform random + weighted selection

Optional extensions:

- Coverage-based selection (prioritize new screens/new elements)
- State save (snapshot) and restore/reset

#### 6.2.3 Seed/Replay (Required)

- Record random seed and support re-execution with same seed
- Support **AI-free replay** from recorded action sequence

#### 6.2.4 Minimization (Recommended)

- Shorten failing repro steps where possible
- Minimum support:
  - Extract last N operations
  - Simple delta reduction by testing first-half/second-half deletions

---

## 7. Issue Ticket Requirements (Required)

### 7.1 Storage Format

- Output path: `artifacts/tickets/<session_id>/TICKET-<timestamp>-<shortid>/`
- Required files:
  - `ticket.md`
  - `repro.actions.json`
  - `screens/`
  - `uia/`
  - `runner.log`
- Optional files:
  - `ticket.json`
  - `app.log` / `crash.dmp` / `eventlog.txt`

### 7.2 Required `ticket.md` Fields

- **Repro Steps** (numbered)
- **Actual Result**
- **Expected Result**
- **Title**
- **Summary**
- **Environment** (OS, target method, profile name, seed, build type, etc.)
- **Evidence** (attachments list)
- **Root Cause Hypothesis** (evidence-based, non-conclusive)

### 7.3 Root-Cause Assistance (Best Effort)

- Last operated selector and point-in-time UIA state (`enabled`/`visible`/`bounding`)
- UIA diff before/after failure (element disappearance/disablement, etc.)
- Error UI text (OCR/text)
- If available: app logs, unhandled exception stacks, Windows event logs

---

## 8. AI Output Specification (Structured)

AI output must be **tool calls** (or strict JSON action array), not free-form natural language.

### 8.1 Action JSON Example

```json
[
  {"tool":"focus_window","args":{"window_query": ".*MyApp.*"}},
  {"tool":"list_controls","args":{"window_query": ".*MyApp.*"}},
  {"tool":"click","args":{"window_query": ".*MyApp.*","selector":{"automation_id":"SettingsButton"}}},
  {"tool":"type_text","args":{"window_query": ".*MyApp.*","selector":{"automation_id":"ServerUrlTextBox"},"text":"http://localhost:1234"}},
  {"tool":"click","args":{"window_query": ".*MyApp.*","selector":{"automation_id":"SaveButton"}}},
  {"tool":"screenshot","args":{"window_query": ".*MyApp.*"}}
]
```

### 8.2 AI Safety Constraints

- Coordinate clicks are disallowed by default (allowed only when UIA selectors are unavailable)
- No repeated blind clicking (must reacquire state before repeated operation)
- Destructive operations allowed only with explicit permission

---

## 9. Non-Functional Requirements

### 9.1 Stability

- Insert wait/verification (`wait_for` / `get_state`) for each operation
- Timeout settings:
  - Default: 10 seconds
  - Overridable per tool

### 9.2 Logging / Audit

Store the following for each step:

- Screenshot (PNG)
- UIA snapshot (JSON)
- AI input prompt
- AI output (tool calls/JSON)
- Executed tool call and result (success/exception/log)

Use one session directory per run (`1 run = 1 session ID`).

### 9.3 Replay

- Re-execute collected action JSON
- Replay must be possible without AI

### 9.4 Security

- Implement only allowlisted tool operations
- File operations/network sends/process launches are disallowed by default (add only if explicitly required)

### 9.5 Performance

- UIA enumeration can be heavy; support depth/filter options
- Screenshot capture should be on demand; provide mode that does not force capture every step

---

## 10. Implementation Approach (Recommended)

### 10.1 Claude Code + MCP (Primary Deliverable)

- Implement local MCP server (stdio)
- Register tools callable from Claude Code
- Invoke `pywinauto` (UIA) inside MCP server

### 10.2 Alternative (Direct API)

- Send image + instruction to Claude API
- Runner executes returned action JSON

### 10.3 Setup UX (Highest Priority)

#### 10.3.1 Distribution Format (Recommended)

- ZIP distribution (recommended): `wpf-ui-agent/`
  - `wpf-agent.exe` (single executable bundling runner + MCP server)
  - `setup.ps1` (initialization + Claude Code registration helper)
  - `profiles.json` (target app definitions)
  - `README.md`

If implemented in Python, single-exe packaging via PyInstaller (or equivalent) is strongly preferred.

#### 10.3.2 One-Command Initialization

Running `setup.ps1` must perform:

1. Prerequisite checks (Windows/permissions/required components)
2. `profiles.json` template generation
3. MCP registration guidance for Claude Code (including command examples)
4. Smoke test (run demo scenario A in dry-run)

#### 10.3.3 CLI Requirements

- `wpf-agent init`
- `wpf-agent profiles list/add/edit/remove`
- `wpf-agent run --profile <name>`
- `wpf-agent attach --pid <pid>`
- `wpf-agent launch --exe <path> -- <args...>`
- (Recommended) `wpf-agent scenario run --file <scenario.yaml> --profile <name>`
- (Recommended) `wpf-agent random run --profile <name> --max-steps 200 --seed 12345`
- (Recommended) `wpf-agent replay --file repro.actions.json`
- (Recommended) `wpf-agent tickets open --last`

#### 10.3.4 Profile Format (Arbitrary App Targeting)

`profiles.json` must support multiple app profiles:

- `name`: e.g., `MyApp-Dev`
- `match`: `pid` / `process` / `title_re` / `exe`
- `launch`: launch path + args (optional)
- `timeouts`: startup wait etc.
- `safety`: destructive operation allow/deny

---

## 11. Deliverables

1. Full source code
   - `runner/` (loop control, logs, replay)
   - `mcp_server/` (tool implementations)
   - `schemas/` (action JSON / tool argument schemas)
2. Setup guide
   - Windows environment setup, dependencies, MCP registration for Claude Code
3. Specification/design document (lightweight acceptable)
   - Tool list, arguments, error codes, log format
4. Demo scenarios (minimum 2)
   - (A) Open settings screen, input text, save
   - (B) Operation involving navigation (including dialog)
5. Tests
   - Unit tests for tool layer (as feasible)
   - Sample demo run logs (session directory)
6. Distribution artifacts (required)
   - `wpf-agent.exe` (single executable) or equivalent easy distribution artifact
   - `setup.ps1`
   - `profiles.json` template
   - `README.md` (one-page quick-start)

---

## 12. Acceptance Criteria

- Tools are callable from Claude Code (via MCP)
- Target app can be specified arbitrarily using **all 4 methods** (PID/process/EXE/title regex)
- Multiple apps can be registered in `profiles.json` and switched via `--profile`
- Target app window can be identified and focused
- UIA control list can be retrieved
- Click/input by AutomationId succeeds
- Post-operation verification is possible (screenshot or UIA value)
- Scenario tests generate issue tickets when expectations mismatch
- Random tests can run for specified steps and generate issue tickets on failures
- Tickets always include repro steps / actual result / expected result
- Tickets include screenshot, UIA snapshot, and recent logs
- Reproduction is possible without AI via seed and action sequence
- Full per-session logs are saved in a session folder
- Smoke test completes within **10 minutes from `setup.ps1` or `wpf-agent init`** (target)

---

## 13. Risks and Mitigations

- **UIA cannot see elements** (custom-rendered / custom controls)
  - Mitigation: assign `AutomationProperties.AutomationId`; implement AutomationPeer if needed
  - Alternative: OCR + coordinate click (limited use)
- **AI performs wrong actions**
  - Mitigation: tool allowlist, destructive action prohibition, double confirmation
- **Window title is dynamic**
  - Mitigation: combine PID/process/regex/class-based identification

---

## 14. Implementation Milestones (Recommended)

1. Minimal PoC
   - `list_windows` / `resolve_target` / `focus_window` / `list_controls` / `click` / `type_text` / `screenshot`
   - Achieve demo (A) using arbitrary app targeting (PID/title)
2. Distribution and setup hardening
   - `wpf-agent init` / `profiles.json` / `setup.ps1`
   - MCP registration path for Claude Code
   - Smoke test
3. Stabilization
   - `wait_for`, `get_state`, error handling, retries
   - Logging and replay
4. Fallback introduction (if needed)
   - OCR/coordinate click
   - Achieve demo (B)

### 14.1 Recommended App-Side Changes in WPF

- Assign `AutomationProperties.AutomationId` to major controls
- Provide stable Name/AutomationId for dynamic labels/content
- Implement AutomationPeer for custom controls as needed

### 14.2 Operation Modes

- Safe mode: UIA only, no coordinate clicks
- Extended mode: UIA + OCR (coordinate clicks allowed)

### 14.3 Pre-Engagement Questions (Optional)

- Target WPF app window title (or identification method)
- First concrete scenario to automate (navigation steps)
- Degree of UIA invisibility (presence of custom rendering)

---

End of document.
