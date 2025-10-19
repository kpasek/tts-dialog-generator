# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_submodules

# Główne źródło aplikacji (np. main.py)
script_file = 'gui.py'

# Ikona — tylko Windows obsługuje ikony .ico
icon_file = None
if sys.platform.startswith("win"):
    icon_file = os.path.join("assets", "icon512.ico")  # zamień PNG na ICO dla Windows
else:
    icon_file = None  # Linux nie wymaga pliku ikony w specyfikacji

# Pliki dodatkowe (np. zasoby)
datas = [
    ('assets', 'assets')
]

name = "SubtitleCleaner"

excluded_modules = [
    'torch',
    'numpy',
    'scipy',
    'matplotlib'
]

# Zależności ukryte (opcjonalnie)
hiddenimports = collect_submodules('tkinter')

a = Analysis(
    [script_file],
    pathex=[os.getcwd()],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # True jeśli chcesz mieć konsolę obok GUI
    icon=icon_file,
    noconfirm=True
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=f"{name}_build"
)
