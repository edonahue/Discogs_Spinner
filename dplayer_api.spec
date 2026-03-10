# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for the dplayer-api FastAPI sidecar.
#
# Usage:
#   pyinstaller dplayer_api.spec
#
# Or via the build script which handles platform naming:
#   ./scripts/build_sidecar.sh
#
# Output binary is placed in desktop_shell/src-tauri/binaries/ with the
# Tauri sidecar naming convention: dplayer-api-{target-triple}[.exe]

import sys
from pathlib import Path

ROOT = Path(SPECPATH)  # repo root (spec lives at repo root)
SRC = ROOT / "src"

# ---------------------------------------------------------------------------
# Hidden imports required by uvicorn + FastAPI at runtime
# ---------------------------------------------------------------------------
hidden = [
    # uvicorn internals
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.asyncio",
    "uvicorn.loops.uvloop",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.off",
    "uvicorn.lifespan.on",
    # fastapi / starlette
    "fastapi",
    "starlette",
    "starlette.routing",
    "starlette.middleware",
    "starlette.middleware.cors",
    "anyio",
    "anyio.from_thread",
    # discogs_player packages
    "discogs_player",
    "discogs_player_api",
    "discogs_player.core",
    "discogs_player.data",
    "discogs_player.services",
    "discogs_player.use_cases",
    "discogs_player.integrations",
    # platformdirs — lazy imports missed by PyInstaller
    "platformdirs",
    "platformdirs.windows",
    "platformdirs.macos",
    "platformdirs.unix",
    # stdlib extras sometimes missed
    "email.mime.text",
    "email.mime.multipart",
]

# ---------------------------------------------------------------------------
# Data files: DB migration scripts and any bundled assets
# ---------------------------------------------------------------------------
datas = [
    # Include Alembic / raw SQL migration files if any exist under data/
    (str(SRC / "discogs_player" / "data"), "discogs_player/data"),
]

a = Analysis(
    [str(SRC / "discogs_player" / "api_main.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["gi", "gtk", "tkinter", "PyQt5", "PyQt6", "wx"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    # Name is set by build_sidecar.sh via --name flag; default here for direct runs.
    name="dplayer-api",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # keep console for sidecar logging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
