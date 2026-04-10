# PyInstaller spec for bundling the FastAPI backend as a standalone executable.
# Run: pyinstaller pyinstaller.spec

import sys
from pathlib import Path

block_cipher = None

src_dir = str(Path("src").resolve())

a = Analysis(
    ["src/api/server.py"],
    pathex=[src_dir],
    binaries=[],
    datas=[],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "scout",
        "scout.parser",
        "scout.scorer",
        "scout.report",
        "scout.rules",
        "scout.rules.schema_design",
        "scout.rules.metadata",
        "scout.rules.relationships",
        "scout.rules.measures",
        "scout.rules.ai_prep",
        "scout.rules.data_types",
        "scout.rules.data_consistency",
        "enforcer",
        "enforcer.planner",
        "enforcer.file_applier",
        "historian",
        "historian.logger",
        "shared",
        "shared.model",
        "shared.config",
        "shared.llm",
        "api",
        "api.routes",
        "api.routes.scout",
        "api.routes.enforcer",
        "api.routes.historian",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="api-server",
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
