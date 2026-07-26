# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: freeze the app into one self-contained executable per OS.

Build:  pyinstaller youtube_downloader.spec   ->   dist/Youtube-Downloader[.exe]

Bundles the read-only resources the app loads at runtime (metadata.json and the
gui/web assets) under the same repo-relative layout that youtube_downloader/paths.py
expects, and collects the yt-dlp extractors, the imageio-ffmpeg static binary, and
certifi's CA bundle (yt-dlp needs it for HTTPS).
"""

import sys

from PyInstaller.utils.hooks import collect_all

# Read-only resources, kept at their repo-relative paths so resource_path() finds
# them under sys._MEIPASS at runtime.
datas = [
    ('metadata.json', '.'),
    ('youtube-dl.ico', '.'),  # served as the web UI favicon (see gui/server.py)
    ('youtube_downloader/gui/web', 'youtube_downloader/gui/web'),
]
binaries = []
hiddenimports = []

# yt_dlp: lazily-imported extractors. imageio_ffmpeg: the bundled ffmpeg binary.
# certifi: CA bundle for yt-dlp's HTTPS requests.
for _pkg in ('yt_dlp', 'imageio_ffmpeg', 'certifi'):
    _d, _b, _h = collect_all(_pkg)
    datas += _d
    binaries += _b
    hiddenimports += _h

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Youtube-Downloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # GUI app: opens in the browser; logs via the in-app panel + log file
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Only a Windows .ico exists; a macOS .icns can be added later.
    icon='youtube-dl.ico' if sys.platform == 'win32' else None,
)
