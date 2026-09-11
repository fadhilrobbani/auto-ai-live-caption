# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None
spec_dir = SPECPATH if "SPECPATH" in globals() else os.path.dirname(os.path.abspath(sys.argv[0]))
project_root = os.path.abspath(os.path.join(spec_dir, "../.."))

datas = []
# Collect package data
datas += collect_data_files("faster_whisper")
datas += collect_data_files("ctranslate2")
assets_dir = os.path.join(project_root, "packaging", "assets")
if os.path.exists(assets_dir):
    datas.append((assets_dir, "packaging/assets"))

# Dynamic libraries (ctranslate2, onnxruntime shared objects)
binaries = []
binaries += collect_dynamic_libs("ctranslate2")
binaries += collect_dynamic_libs("onnxruntime")

hidden_imports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "core",
    "core.audio",
    "core.audio.device_manager",
    "core.audio.streamer",
    "core.vad",
    "core.vad.processor",
    "core.models",
    "core.models.base",
    "core.models.catalog",
    "core.models.downloader",
    "core.models.faster_whisper",
    "core.models.groq_api",
    "core.models.openai_api",
    "core.models.registry",
    "core.stabilizer",
    "core.stabilizer.text_stabilizer",
    "core.transcript",
    "core.transcript.recorder",
    "core.config",
    "core.config.manager",
    "ui",
    "ui.overlay",
    "ui.controls",
    "ui.settings_dialog",
    "ui.download_dialog",
    "ui.history_dialog",
    "ui.tray",
    "ui.worker",
    "ctranslate2",
    "faster_whisper",
    "onnxruntime",
    "soundfile",
    "scipy.signal",
    "httpx",
]

a = Analysis(
    [os.path.join(project_root, "main.py")],
    pathex=[project_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "test", "unittest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="auto-ai-live-caption",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="auto-ai-live-caption",
)
