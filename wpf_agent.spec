# PyInstaller spec for wpf-agent single executable
# Build: pyinstaller wpf_agent.spec

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['src/wpf_agent/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('profiles.json', '.'),
        ('scenarios', 'scenarios'),
    ],
    hiddenimports=[
        'wpf_agent',
        'wpf_agent.cli',
        'wpf_agent.config',
        'wpf_agent.constants',
        'wpf_agent.core.errors',
        'wpf_agent.core.target',
        'wpf_agent.core.session',
        'wpf_agent.core.safety',
        'wpf_agent.uia.engine',
        'wpf_agent.uia.selector',
        'wpf_agent.uia.snapshot',
        'wpf_agent.uia.screenshot',
        'wpf_agent.uia.waits',
        'wpf_agent.mcp.server',
        'wpf_agent.mcp.types',
        'wpf_agent.runner.agent_loop',
        'wpf_agent.runner.replay',
        'wpf_agent.runner.logging',
        'wpf_agent.testing.scenario',
        'wpf_agent.testing.random_tester',
        'wpf_agent.testing.assertions',
        'wpf_agent.testing.oracles',
        'wpf_agent.testing.minimizer',
        'wpf_agent.tickets.generator',
        'wpf_agent.tickets.templates',
        'wpf_agent.tickets.evidence',
        'pywinauto',
        'mcp',
        'click',
        'pydantic',
        'PIL',
        'psutil',
        'yaml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='wpf-agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
