@echo off
title Assistente WhatsApp Euronics Comiso (Gemini Backend)
echo ========================================================
echo   ASSISTENTE WHATSAPP EURONICS COMISO - BACKEND GEMINI
echo ========================================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    echo Utilizzo ambiente virtuale .venv...
    set "PYTHON_CMD=.venv\Scripts\python.exe"
) else (
    echo Utilizzo Python di sistema...
    set "PYTHON_CMD=python"
)

echo Avvio server Flask su porta 5000...
echo.
"%PYTHON_CMD%" app.py
pause
