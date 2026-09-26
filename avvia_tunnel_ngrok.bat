@echo off
title Tunnel ngrok per Webhook WhatsApp (Porta 5000)
echo ========================================================
echo   TUNNEL NGROK PER WEBHOOK TWILIO WHATSAPP
echo ========================================================
echo.

set "NGROK_BIN="
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\ngrok.exe" (
    set "NGROK_BIN=%LOCALAPPDATA%\Microsoft\WinGet\Links\ngrok.exe"
) else (
    where ngrok >nul 2>nul
    if %errorlevel% equ 0 (
        set "NGROK_BIN=ngrok"
    )
)

if "%NGROK_BIN%"=="" (
    echo ERRORE: ngrok non trovato. Installalo o verifica il percorso.
    pause
    exit /b 1
)

echo Avvio del tunnel sulla porta 5000...
echo Copia l'URL pubblico HTTPS (es. https://xxxx.ngrok-free.app) 
echo e incollalo su Twilio: https://xxxx.ngrok-free.app/incoming
echo.
"%NGROK_BIN%" http 5000
pause
