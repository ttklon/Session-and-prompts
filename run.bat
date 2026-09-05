@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Genspark Arkhivator

where python >nul 2>nul
if errorlevel 1 (
    echo [ОШИБКА] Python не найден.
    echo Установите Python 3.10+ с https://www.python.org/downloads/
    echo и при установке ОБЯЗАТЕЛЬНО поставьте галочку "Add Python to PATH".
    pause
    exit /b 1
)

python -c "import selenium, requests, rapidfuzz" >nul 2>nul
if errorlevel 1 (
    echo Первый запуск: устанавливаю библиотеки ^(один раз^)...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
)

python gui.py %*
pause
