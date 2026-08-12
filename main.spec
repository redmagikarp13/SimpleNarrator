# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

# Coletar assets do CustomTkinter e dependências C++/ONNX do Piper
datas = collect_data_files('customtkinter')
binaries = []

for pkg in ['piper', 'piper_phonemize', 'onnxruntime']:
    try:
        datas.extend(collect_data_files(pkg))
    except Exception:
        pass
    try:
        binaries.extend(collect_dynamic_libs(pkg))
    except Exception:
        pass

hidden_imports = [
    'ui',
    'ui.app',
    'engines',
    'engines.base_engine',
    'engines.native_engine',
    'engines.piper_engine',
    'file_io',
    'file_io.reader',
    'file_io.exporter',
    'audio',
    'audio.chunker',
    'models',
    'models.downloader',
    'customtkinter',
    'fitz',
    'piper',
    'piper.voice',
    'piper.config',
    'piper_phonemize',
    'onnxruntime',
    'requests',
    'pyttsx3',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
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
    name='SimpleNarrator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
