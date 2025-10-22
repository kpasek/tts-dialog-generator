# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import get_package_paths, collect_submodules, collect_data_files

torch_path = get_package_paths('torch')[0]
torch_layers = os.path.join(torch_path, 'nn')
torch_jit = os.path.join(torch_path, 'jit')


datas = [('assets', 'assets')]
datas += collect_data_files('TTS', include_py_files=False)
datas += collect_data_files('trainer', include_py_files=False)
datas += collect_data_files('torch', include_py_files=True)

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas= datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SubtitleStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\icon512.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SubtitleStudio',
)
