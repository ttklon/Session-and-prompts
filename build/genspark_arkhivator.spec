# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec для Genspark Arkhivator.
Собирает один EXE: python gui.py — окно без консоли.
Включает selectors.json и reference_screenshot.png как ресурсы.
"""
import os

block_cipher = None
ROOT = os.path.abspath(os.path.join(os.path.dirname(SPEC), ".."))  # noqa: F821

a = Analysis(
    [os.path.join(ROOT, "gui.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, "selectors.json"), "."),
        (os.path.join(ROOT, "reference_screenshot.png"), "."),
    ],
    hiddenimports=[
        "db", "extractor", "summarizer", "theme", "widgets",
        "search", "semantic_search", "duplicates", "prompts",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["playwright"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="genspark_arkhivator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
