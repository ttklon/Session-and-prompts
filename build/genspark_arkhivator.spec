# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec для Genspark Arkhivator.

КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ (ошибка «No module named 'selenium.webdriver.chrome.options'»):
Selenium импортирует подмодули драйверов лениво, поэтому статический анализ
PyInstaller их не видит. Забираем ВСЕ подмодули selenium.webdriver явно через
collect_submodules, плюс данные certifi (HTTPS для Gemini).
"""
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None
ROOT = os.path.abspath(os.path.join(os.path.dirname(SPEC), ".."))  # noqa: F821

selenium_hidden = collect_submodules("selenium.webdriver")
certifi_datas = collect_data_files("certifi")

a = Analysis(
    [os.path.join(ROOT, "gui.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, "selectors.json"), "."),
        (os.path.join(ROOT, "reference_screenshot.png"), "."),
        (os.path.join(ROOT, "icon.ico"), "."),
    ] + certifi_datas,
    hiddenimports=[
        "db", "extractor", "summarizer", "theme", "widgets",
        "search", "semantic_search", "duplicates", "prompts",
        "compressor", "patterns",
    ] + selenium_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["playwright", "llmlingua", "torch", "transformers"],
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
    upx=False,  # UPX замедляет распаковку при каждом старте и злит антивирусы
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, "icon.ico"),
)
