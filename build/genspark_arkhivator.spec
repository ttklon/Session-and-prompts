# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec для Windows-сборки.
# Запуск: pyinstaller --noconfirm genspark_arkhivator.spec
from pathlib import Path
block_cipher = None

HERE = Path('.').resolve()
RES = HERE / "data" ; RES.mkdir(exist_ok=True)
CHATS = RES / "chats" ; CHATS.mkdir(exist_ok=True)

a = Analysis(
    ['gui.py'],
    pathex=[str(HERE)],
    binaries=[], datas=[],
    hiddenimports=[
        'selenium','selenium.webdriver','selenium.webdriver.chrome',
        'selenium.webdriver.chrome.options','selenium.webdriver.chrome.service',
        'selenium.webdriver.edge','selenium.webdriver.edge.options',
        'selenium.webdriver.common','selenium.webdriver.remote',
        'requests','rapidfuzz','db','extractor','summarizer','search','theme',
    ],
    hookspath=[], runtime_hooks=[], excludes=['tkinter.test'],
    win_no_prefer_redirects=False, win_private_assemblies=False,
    cipher=block_cipher, noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [],
          name='GensparkArkhivator',
          debug=False, bootloader_ignore_signals=False, strip=False,
          upx=True, upx_exclude=[], runtime_tmpdir=None,
          console=False, disable_windowed_traceback=False,
          target_arch=None, codesign_identity=None,
          entitlements_file=None, icon=None)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas,
               strip=False, upx=True, upx_exclude=[],
               name='GensparkArkhivator')
