# setup.ps1 — WPF UI Debug Automation Agent setup helper
# Run: powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== WPF UI Debug Automation Agent Setup ===" -ForegroundColor Cyan

# 1. Check prerequisites
Write-Host "`n[1/5] Checking prerequisites..." -ForegroundColor Yellow

# Windows check
if ($env:OS -ne "Windows_NT") {
    Write-Host "ERROR: This tool requires Windows." -ForegroundColor Red
    exit 1
}
Write-Host "  OS: Windows OK"

# Python check
try {
    $pyVer = python --version 2>&1
    Write-Host "  Python: $pyVer"
    $verMatch = [regex]::Match($pyVer, '(\d+)\.(\d+)')
    $major = [int]$verMatch.Groups[1].Value
    $minor = [int]$verMatch.Groups[2].Value
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
        Write-Host "ERROR: Python 3.10+ required." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "ERROR: Python not found. Install Python 3.10+." -ForegroundColor Red
    exit 1
}

# 2. Install package
Write-Host "`n[2/5] Installing wpf-agent..." -ForegroundColor Yellow
python -m pip install -e ".[dev]" --quiet
Write-Host "  Installed successfully"

# 3. Initialize project
Write-Host "`n[3/5] Initializing project..." -ForegroundColor Yellow
python -m wpf_agent init

# 4. Claude Code MCP registration guidance
Write-Host "`n[4/5] MCP Server Registration" -ForegroundColor Yellow
Write-Host "  To register with Claude Code, run:"
Write-Host ""
Write-Host "    claude mcp add wpf-agent -- python -m wpf_agent mcp-serve" -ForegroundColor Green
Write-Host ""
Write-Host "  Or add to your Claude Code MCP config:" -ForegroundColor Gray
Write-Host '    {' -ForegroundColor Gray
Write-Host '      "mcpServers": {' -ForegroundColor Gray
Write-Host '        "wpf-agent": {' -ForegroundColor Gray
Write-Host '          "command": "python",' -ForegroundColor Gray
Write-Host '          "args": ["-m", "wpf_agent", "mcp-serve"]' -ForegroundColor Gray
Write-Host '        }' -ForegroundColor Gray
Write-Host '      }' -ForegroundColor Gray
Write-Host '    }' -ForegroundColor Gray

# 5. Smoke test
Write-Host "`n[5/5] Running smoke test..." -ForegroundColor Yellow
try {
    python -c "from wpf_agent.mcp.server import mcp; print('  MCP server import: OK')"
    python -c "from wpf_agent.cli import main; print('  CLI import: OK')"
    python -c "from wpf_agent.uia.engine import UIAEngine; print('  UIA engine import: OK')"
    python -c "from wpf_agent.testing.scenario import Scenario; print('  Scenario runner import: OK')"
    Write-Host "  Smoke test passed!" -ForegroundColor Green
} catch {
    Write-Host "  Smoke test failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "Next steps:"
Write-Host "  1. Edit profiles.json to add your target WPF apps"
Write-Host "  2. Register MCP server with Claude Code (see above)"
Write-Host "  3. Run: wpf-agent scenario run --file scenarios/demo_a_settings.yaml --profile <name>"
Write-Host ""
